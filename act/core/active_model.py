# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import yaml
from .carbon import Carbon, SourceType
from .common import ACT_ROOT
from .logger import log
from .units import kg, units
from enum import Enum

DEFAULT_ACTIVE_MODEL_FILE = f"{ACT_ROOT}/models/passives/active.yaml"


class ActiveType(Enum):
    """Enumeration of active semiconductor component types based on Ecoinvent 3.11 data"""
    TRANSISTOR_BJT = "transistor_bjt"      # BJT transistor (NPN/PNP), surface-mounted
    TRANSISTOR_MOSFET = "transistor_mosfet"  # MOSFET transistor, surface-mounted
    ACTIVE_GENERIC = "active_generic"      # Generic active semiconductor (unspecified)
    GENERIC = "generic"                    # Generic (defaults to active_generic)


class ActiveModel:
    """
    Active semiconductor component carbon emissions model based on weight and type.

    This class calculates carbon emissions for active semiconductors (transistors,
    MOSFETs, etc.) using emission factors from Ecoinvent 3.11 database.

    Formula: carbon = weight (kg) * emission_factor (kg CO2e/kg) * quantity
    """

    def __init__(self, model_file: str = DEFAULT_ACTIVE_MODEL_FILE):
        """
        Initializes the ActiveModel instance with a model file.

        Args:
            model_file (str): The path to the model file. Defaults to DEFAULT_ACTIVE_MODEL_FILE.
        """
        with open(model_file) as handle:
            model_data = yaml.load(handle, Loader=yaml.FullLoader)

        # Load emission factors for active component types
        self.emission_factors = {}
        for active_type, factor in model_data.items():
            try:
                self.emission_factors[ActiveType(active_type)] = units(factor)
            except ValueError:
                log.warn(f"Unknown active component type '{active_type}' in model file, skipping.")

        # Ensure we have at least a generic factor
        if ActiveType.GENERIC not in self.emission_factors:
            if ActiveType.ACTIVE_GENERIC in self.emission_factors:
                self.emission_factors[ActiveType.GENERIC] = self.emission_factors[ActiveType.ACTIVE_GENERIC]
            else:
                log.error("No active component emission factors found in model file.")
                exit(-1)

    def get_carbon(
        self,
        weight: units,
        active_type: ActiveType = ActiveType.GENERIC,
        n_components: int = 1
    ) -> Carbon:
        """
        Calculates the carbon emissions for active semiconductor components.

        Args:
            weight: The weight of a single component
            active_type: The type of active component. Defaults to ActiveType.GENERIC
            n_components: The number of components. Defaults to 1

        Returns:
            Carbon: The total carbon emissions for the components

        Raises:
            AssertionError: If the weight is not in units of mass
        """
        assert weight.check(kg), f"Expected weight units for active model but got {weight}"

        # Get the emission factor for this active component type
        if active_type not in self.emission_factors:
            log.warn(
                f"Active component type {active_type} not found in model. Using generic emission factor."
            )
            emission_factor = self.emission_factors[ActiveType.GENERIC]
        else:
            emission_factor = self.emission_factors[active_type]

        # Calculate carbon: weight × emission_factor × number of components
        total_carbon = weight * emission_factor * n_components

        log.debug(
            f"Active component carbon calculation: {weight} * {emission_factor} * {n_components} = {total_carbon}"
        )

        return Carbon(total_carbon, SourceType.ACTIVE)
