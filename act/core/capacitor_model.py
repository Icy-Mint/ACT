# Copyright (c) Meta Platforms, Inc. and affiliates.

# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from enum import Enum

import yaml
from .units import *

from .carbon import Carbon, SourceType
from .common import ACT_ROOT, EnergyLocation
from .utils import load_ci_model


class CapacitorType(Enum):
    """
    Enum representing different types of capacitors.

    Attributes:
        Energy-based types: 
            MLCC (str): Multilayer Ceramic Capacitor
            TEC (str): Tantalum Electrolytic Capacitor
            GENERIC (str): Generic Capacitor

        Package-based types (IoT components):
            PKG_0201 (str): 0201 package (package-based)
            PKG_0402 (str): 0402 package (package-based)
            PKG_0603 (str): 0603 package (package-based)
            PKG_0805 (str): 0805 package (package-based)
    """

    # Energy-based types 
    MLCC = "mlcc"
    TEC = "tec"
    GENERIC = "generic"
    
    # Package-based types (IoT components)
    PKG_0201 = "0201"
    PKG_0402 = "0402"
    PKG_0603 = "0603"
    PKG_0805 = "0805"


"""Default weight of a capacitor in grams."""
DEFAULT_CAPACITOR_WEIGHT = 0.03 * g

"""Default carbon emissions per capacitor in grams."""
DEFAULT_CARBON_PER_CAPACITOR = 300 * g

"""Default configuration file for capacitor models."""
DEFAULT_CP_CONFIG = f"{ACT_ROOT}/models/passives/capacitors.yaml"


class CapacitorModel:
    """
    A model for estimating carbon emissions from capacitors.

    Supports two calculation methods:
    1. Energy-based (legacy): For MLCC, TEC, GENERIC types with weight
       Formula: energy_per_kg * carbon_intensity * weight * quantity
    2. Package-based (new): For 0201, 0402, 0603, 0805 types
       Formula: emission_factor_per_package * quantity

    Attributes:
        capacitor_model (dict): A dictionary mapping CapacitorType to units of carbon per weight.
        ci_model (dict): A dictionary mapping EnergyLocation to carbon intensity values.
        package_model (dict): Package-based model (kg CO2e per capacitor)
    """

    def __init__(self, model_file=DEFAULT_CP_CONFIG) -> None:
        """
        Initializes a new instance of the CapacitorModel class.
        Loads the capacitor model and carbon intensity model from YAML files.

        Args:
            model_file (str, optional): Capacitor model file to load. Defaults to DEFAULT_CP_CONFIG.
        """
        with open(model_file) as f:
            model_data = yaml.load(f, Loader=yaml.FullLoader)
        
        # Separate energy-based and package-based models
        self.capacitor_model: dict[CapacitorType, pint.Quantity] = {}
        self.package_model: dict[CapacitorType, pint.Quantity] = {}
        
        for key, value in model_data.items():
            try:
                cap_type = CapacitorType(key)
                
                # Energy-based types (MJ/kg)
                if cap_type in [CapacitorType.MLCC, CapacitorType.TEC, CapacitorType.GENERIC]:
                    self.capacitor_model[cap_type] = units(value)
                # Package-based types (kg CO2e)
                else:
                    self.package_model[cap_type] = units(value)
            except ValueError:
                # Skip unknown types
                pass
        self.ci_model = load_ci_model()

    def get_carbon(
        self,
        ci: EnergyLocation = EnergyLocation.JAPAN,
        ctype: CapacitorType = CapacitorType.GENERIC,
        weight: pint.Quantity = DEFAULT_CAPACITOR_WEIGHT,
        n_caps: int = 1,
    ) -> Carbon:
        """
        Get the carbon emissions cost based on the capacitor type and weight of the capacitor.

        Automatically selects calculation method:
        - Package-based: If ctype is 0201/0402/0603/0805 (uses package emission factors)
        - Energy-based: If ctype is mlcc/tec/generic (uses weight * energy * carbon intensity)

        Args:
            ci (EnergyLocation, optional): Carbon intensity per manufacturing energy. Defaults to EnergyLocation.JAPAN.
            ctype (CapacitorType, optional): The capacitor type. Defaults to CapacitorType.GENERIC.
            weight (pint.Quantity, optional): Weight of the capacitor. Defaults to DEFAULT_CAPACITOR_WEIGHT.
            n_caps (int, optional): Number of capacitors. Defaults to 1.

        Returns:
            Carbon: A carbon object that encodes the emissions cost of manufacturing.
        """
        # Method 1: Package-based calculation (for IoT components)
        if ctype in self.package_model:
            emission_per_cap = self.package_model[ctype]
            total_carbon = emission_per_cap * n_caps
            return Carbon(total_carbon, SourceType.PASSIVES)
        
        # Method 2: Energy-based calculation (legacy)
        elif ctype in self.capacitor_model:
            energy_per_kg = self.capacitor_model[ctype]
            carbon_intensity = self.ci_model[ci]
            total_carbon = energy_per_kg * weight * n_caps * carbon_intensity
            return Carbon(total_carbon, SourceType.PASSIVES)
        
        # Fallback: Use default
        else:
            return Carbon(DEFAULT_CARBON_PER_CAPACITOR * n_caps, SourceType.PASSIVES)
