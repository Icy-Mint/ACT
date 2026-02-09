# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import yaml
from .carbon import Carbon, SourceType
from .common import ACT_ROOT
from .logger import log
from .units import kg, units
from enum import Enum

DEFAULT_DIODE_MODEL_FILE = f"{ACT_ROOT}/models/passives/diode.yaml"


class DiodeType(Enum):
    """Enumeration of diode types based on Ecoinvent 3.11 data"""
    GLASS_SMD = "glass_smd"  # Glass diode for surface mounting
    LED = "led"  # Light emitting diode
    TRANSISTOR = "transistor"  # Transistor, surface-mounted
    GENERIC = "generic"  # Generic diode (default)


class DiodeModel:
    """
    Diode carbon emissions model based on weight and material type.
    
    This class calculates carbon emissions for diodes using emission factors
    from Ecoinvent 3.11 database.
    
    Formula: carbon = weight (kg) * emission_factor (kg CO2e/kg) * quantity
    """

    def __init__(self, model_file: str = DEFAULT_DIODE_MODEL_FILE):
        """
        Initializes the DiodeModel instance with a model file.
        
        Args:
            model_file (str): The path to the model file. Defaults to DEFAULT_DIODE_MODEL_FILE.
        """
        with open(model_file) as handle:
            model_data = yaml.load(handle, Loader=yaml.FullLoader)
        
        # Load emission factors for diode types
        self.emission_factors = {}
        for diode_type, factor in model_data.items():
            try:
                self.emission_factors[DiodeType(diode_type)] = units(factor)
            except ValueError:
                log.warn(f"Unknown diode type '{diode_type}' in model file, skipping.")
        
        # Ensure we have at least a generic factor
        if DiodeType.GENERIC not in self.emission_factors:
            if DiodeType.GLASS_SMD in self.emission_factors:
                self.emission_factors[DiodeType.GENERIC] = self.emission_factors[DiodeType.GLASS_SMD]
            else:
                log.error("No diode emission factors found in model file.")
                exit(-1)
    
    def get_carbon(
        self,
        weight: units,
        diode_type: DiodeType = DiodeType.GENERIC,
        n_diodes: int = 1
    ) -> Carbon:
        """
        Calculates the carbon emissions for diodes based on weight and type.
        
        Args:
            weight: The weight of a single diode
            diode_type: The type of diode. Defaults to DiodeType.GENERIC
            n_diodes: The number of diodes. Defaults to 1
        
        Returns:
            Carbon: The total carbon emissions for the diodes
        
        Raises:
            AssertionError: If the weight is not in units of mass
        """
        assert weight.check(kg), f"Expected weight units for diode model but got {weight}"
        
        # Get the emission factor for this diode type
        if diode_type not in self.emission_factors:
            log.warn(
                f"Diode type {diode_type} not found in model. Using generic emission factor."
            )
            emission_factor = self.emission_factors[DiodeType.GENERIC]
        else:
            emission_factor = self.emission_factors[diode_type]
        
        # Calculate carbon: weight × emission_factor × number of diodes
        total_carbon = weight * emission_factor * n_diodes
        
        log.debug(
            f"Diode carbon calculation: {weight} * {emission_factor} * {n_diodes} = {total_carbon}"
        )
        
        return Carbon(total_carbon, SourceType.FABRICATION)