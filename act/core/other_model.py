# Copyright (c) Meta Platforms, Inc. and affiliates.
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import yaml
from .carbon import Carbon, SourceType
from .common import ACT_ROOT
from .logger import log
from .units import kg, units
from enum import Enum

DEFAULT_OTHER_MODEL_FILE = f"{ACT_ROOT}/models/passives/other.yaml"


class OtherType(Enum):
    """Enumeration of other passive component types"""
    PASSIVE_GENERIC = "passive_generic"  # Generic passive component
    ACTIVE_GENERIC = "active_generic"    # Generic active component
    GENERIC = "generic"  # Generic (defaults to passive)


class OtherModel:
    """
    Other passive components carbon emissions model based on weight.
    
    This class calculates carbon emissions for unspecified passive components
    using emission factors from Ecoinvent 3.11 database.
    
    Formula: carbon = weight (kg) * emission_factor (kg CO2e/kg) * quantity
    """

    def __init__(self, model_file: str = DEFAULT_OTHER_MODEL_FILE):
        """
        Initializes the OtherModel instance with a model file.
        
        Args:
            model_file (str): The path to the model file. Defaults to DEFAULT_OTHER_MODEL_FILE.
        """
        with open(model_file) as handle:
            model_data = yaml.load(handle, Loader=yaml.FullLoader)
        
        # Load emission factors
        self.emission_factors = {}
        for component_type, factor in model_data.items():
            try:
                self.emission_factors[OtherType(component_type)] = units(factor)
            except ValueError:
                log.warn(f"Unknown other component type '{component_type}' in model file, skipping.")
        
        # Ensure we have at least a generic factor
        if OtherType.GENERIC not in self.emission_factors:
            log.error("No generic emission factor found in other model.")
            exit(-1)
    
    def get_carbon(
        self,
        weight: units,
        component_type: OtherType = OtherType.GENERIC,
        n_components: int = 1
    ) -> Carbon:
        """
        Calculates the carbon emissions for other passive components based on weight.
        
        Args:
            weight: The weight of a single component
            component_type: The type of component. Defaults to OtherType.GENERIC
            n_components: The number of components. Defaults to 1
        
        Returns:
            Carbon: The total carbon emissions for the components
        
        Raises:
            AssertionError: If the weight is not in units of mass
        """
        assert weight.check(kg), f"Expected weight units for other model but got {weight}"
        
        # Get the emission factor
        if component_type not in self.emission_factors:
            log.warn(
                f"Other component type {component_type} not found. Using generic emission factor."
            )
            emission_factor = self.emission_factors[OtherType.GENERIC]
        else:
            emission_factor = self.emission_factors[component_type]
        
        # Calculate carbon: weight × emission_factor × number of components
        total_carbon = weight * emission_factor * n_components
        
        log.debug(
            f"Other component carbon calculation: {weight} × {emission_factor} × {n_components} = {total_carbon}"
        )
        
        return Carbon(total_carbon, SourceType.OTHER)