# Copyright (c) Meta Platforms, Inc. and affiliates.
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import yaml
from .carbon import Carbon, SourceType
from .common import ACT_ROOT
from .logger import log
from .units import kg, units
from enum import Enum

DEFAULT_INDUCTOR_MODEL_FILE = f"{ACT_ROOT}/models/passives/inductor.yaml"


class InductorType(Enum):
    """Inductor types"""
    # Weight-based type
    WEIGHT_BASED = "weight_based"
    
    # Package-based types
    PKG_0201 = "0201"
    PKG_0402 = "0402"
    PKG_0603 = "0603"
    PKG_0805 = "0805"
    
    GENERIC = "generic"


class InductorModel:
    """
    Inductor carbon emissions model.
    
    Supports two calculation methods:
    1. Weight-based: weight * emission_factor_per_kg * quantity
    2. Package-based: emission_factor_per_package * quantity
    """

    def __init__(self, model_file: str = DEFAULT_INDUCTOR_MODEL_FILE):
        """
        Initializes the InductorModel instance with a model file.
        
        Args:
            model_file (str): The path to the model file. Defaults to DEFAULT_INDUCTOR_MODEL_FILE.
        """
        with open(model_file) as handle:
            model_data = yaml.load(handle, Loader=yaml.FullLoader)
        
        # Separate weight-based and package-based models
        self.weight_based_factor = None
        self.package_emission_factors = {}
        
        for key, value in model_data.items():
            if key == "weight_based":
                self.weight_based_factor = units(value)
            else:
                try:
                    inductor_type = InductorType(key)
                    self.package_emission_factors[inductor_type] = units(value)
                except ValueError:
                    log.warn(f"Unknown inductor type '{key}' in model file, skipping.")
        
        # Set generic default to 0805 if available
        if InductorType.PKG_0805 in self.package_emission_factors:
            self.package_emission_factors[InductorType.GENERIC] = (
                self.package_emission_factors[InductorType.PKG_0805]
            )

    def get_carbon(
        self,
        n_inductors: int = 1,
        inductor_type: InductorType = InductorType.GENERIC,
        weight=None
    ) -> Carbon:
        """
        Calculates the carbon emissions for inductors.
        
        Method selection:
        - If weight is provided: Use weight-based calculation
        - If inductor_type is a package type: Use package-based calculation
        
        Args:
            n_inductors: Number of inductors
            inductor_type: Inductor type (weight_based, 0201, 0402, 0603, 0805)
            weight: Optional weight for weight-based calculation
        
        Returns:
            Carbon: The total carbon emissions for the inductors
        """
        # Determine calculation method
        is_package_type = inductor_type in [
            InductorType.PKG_0201,
            InductorType.PKG_0402,
            InductorType.PKG_0603,
            InductorType.PKG_0805,
            InductorType.GENERIC
        ]
        
        # Method 1: Package-based calculation
        if is_package_type and weight is None:
            if inductor_type not in self.package_emission_factors:
                log.warn(
                    f"Inductor package type {inductor_type} not found. Using 0805 as default."
                )
                emission_factor = self.package_emission_factors.get(
                    InductorType.PKG_0805,
                    list(self.package_emission_factors.values())[0]
                )
            else:
                emission_factor = self.package_emission_factors[inductor_type]
            
            total_carbon = emission_factor * n_inductors
            
            log.debug(
                f"Inductor carbon (package-based): {emission_factor} × {n_inductors} = {total_carbon}"
            )
            
            return Carbon(total_carbon, SourceType.INDUCTOR)
        
        # Method 2: Weight-based calculation
        else:
            if weight is None:
                log.warn("Weight not provided for inductor weight-based calculation. Skipping.")
                return Carbon(units("0 kg"), SourceType.INDUCTOR)
            
            assert weight.check(kg), f"Expected weight units for inductor model but got {weight}"
            
            if self.weight_based_factor is None:
                log.error("Weight-based emission factor not found in inductor model.")
                return Carbon(units("0 kg"), SourceType.INDUCTOR)
            
            total_carbon = weight * self.weight_based_factor * n_inductors
            
            log.debug(
                f"Inductor carbon (weight-based): {weight} * {self.weight_based_factor} * {n_inductors} = {total_carbon}"
            )
            
            return Carbon(total_carbon, SourceType.INDUCTOR)