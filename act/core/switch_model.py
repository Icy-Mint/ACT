# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import yaml
from .carbon import Carbon, SourceType
from .common import ACT_ROOT
from .logger import log
from .units import kg, units
from enum import Enum

DEFAULT_SWITCH_MODEL_FILE = f"{ACT_ROOT}/models/passives/switch.yaml"


class SwitchType(Enum):
    """Enumeration of switch types"""
    GENERIC = "generic"  # Generic switch (default)
    # Add more specific types as needed


class SwitchModel:
    """
    Switch carbon emissions model based on weight and material type.
    
    This class calculates carbon emissions for switches using emission factors.
    
    Formula: carbon = weight (kg) × emission_factor (kg CO2e/kg) × quantity
    """

    def __init__(self, model_file: str = DEFAULT_SWITCH_MODEL_FILE):
        """
        Initializes the SwitchModel instance with a model file.
        
        Args:
            model_file (str): The path to the model file. Defaults to DEFAULT_SWITCH_MODEL_FILE.
        """
        with open(model_file) as handle:
            model_data = yaml.load(handle, Loader=yaml.FullLoader)
        
        # Load emission factors for switch types
        self.emission_factors = {}
        for switch_type, factor in model_data.items():
            try:
                self.emission_factors[SwitchType(switch_type)] = units(factor)
            except ValueError:
                log.warn(f"Unknown switch type '{switch_type}' in model file, skipping.")
        
        # Ensure we have at least a generic factor
        if SwitchType.GENERIC not in self.emission_factors:
            log.error("No switch emission factors found in model file.")
            exit(-1)
    
    def get_carbon(
        self,
        weight: units,
        switch_type: SwitchType = SwitchType.GENERIC,
        n_switches: int = 1
    ) -> Carbon:
        """
        Calculates the carbon emissions for switches based on weight and type.
        
        Args:
            weight: The weight of a single switch
            switch_type: The type of switch. Defaults to SwitchType.GENERIC
            n_switches: The number of switches. Defaults to 1
        
        Returns:
            Carbon: The total carbon emissions for the switches
        
        Raises:
            AssertionError: If the weight is not in units of mass
        """
        assert weight.check(kg), f"Expected weight units for switch model but got {weight}"
        
        # Get the emission factor for this switch type
        if switch_type not in self.emission_factors:
            log.warn(
                f"Switch type {switch_type} not found in model. Using generic emission factor."
            )
            emission_factor = self.emission_factors[SwitchType.GENERIC]
        else:
            emission_factor = self.emission_factors[switch_type]
        
        # Calculate carbon: weight × emission_factor × number of switches
        total_carbon = weight * emission_factor * n_switches
        
        log.debug(
            f"Switch carbon calculation: {weight} * {emission_factor} * {n_switches} = {total_carbon}"
        )
        
        return Carbon(total_carbon, SourceType.SWITCH)