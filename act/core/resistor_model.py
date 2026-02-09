# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import yaml
from .carbon import Carbon, SourceType
from .common import ACT_ROOT
from .logger import log
from .units import kg, units
from enum import Enum

DEFAULT_RESISTOR_MODEL_FILE = f"{ACT_ROOT}/models/passives/resistor.yaml"


class ResistorType(Enum):
    """Resistor package types"""
    PKG_0201 = "0201"
    PKG_0402 = "0402"
    PKG_0603 = "0603"
    PKG_0805 = "0805"
    GENERIC = "generic"


class ResistorModel:
    """
    Resistor carbon emissions model based on package type.
    
    Formula: carbon = emission_factor_per_package × quantity
    """

    def __init__(self, model_file: str = DEFAULT_RESISTOR_MODEL_FILE):
        """
        Initializes the ResistorModel instance with a model file.
        
        Args:
            model_file (str): The path to the model file. Defaults to DEFAULT_RESISTOR_MODEL_FILE.
        """
        with open(model_file) as handle:
            model_data = yaml.load(handle, Loader=yaml.FullLoader)
        
        # Load emission factors by package type
        self.emission_factors = {}
        for package_type, factor in model_data.items():
            try:
                self.emission_factors[ResistorType(package_type)] = units(factor)
            except ValueError:
                log.warn(f"Unknown resistor package type '{package_type}' in model file, skipping.")
        
        # Ensure we have at least one package type
        if not self.emission_factors:
            log.error("No resistor emission factors found in model file.")
            exit(-1)
        
        # Set generic default
        if ResistorType.PKG_0805 in self.emission_factors and ResistorType.GENERIC not in self.emission_factors:
            self.emission_factors[ResistorType.GENERIC] = self.emission_factors[ResistorType.PKG_0805]

    def get_carbon(
        self,
        n_resistors: int = 1,
        resistor_type: ResistorType = ResistorType.PKG_0805
    ) -> Carbon:
        """
        Calculates the carbon emissions for resistors based on package type.
        
        Args:
            n_resistors: Number of resistors
            resistor_type: Resistor package type (0201, 0402, 0603, 0805)
        
        Returns:
            Carbon: The total carbon emissions for the resistors
        """
        # Get emission factor for this package type
        if resistor_type not in self.emission_factors:
            log.warn(
                f"Resistor package type {resistor_type} not found. Using 0805 as default."
            )
            emission_factor = self.emission_factors.get(
                ResistorType.PKG_0805,
                list(self.emission_factors.values())[0]
            )
        else:
            emission_factor = self.emission_factors[resistor_type]
        
        total_carbon = emission_factor * n_resistors
        
        log.debug(
            f"Resistor carbon (package-based): {emission_factor} * {n_resistors} = {total_carbon}"
        )
        
        return Carbon(total_carbon, SourceType.FABRICATION)