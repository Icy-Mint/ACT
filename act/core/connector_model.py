# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import yaml
from .carbon import Carbon, SourceType
from .common import ACT_ROOT
from .logger import log
from .units import kg, units
from enum import Enum

DEFAULT_CONNECTOR_MODEL_FILE = f"{ACT_ROOT}/models/passives/connector.yaml"


class ConnectorType(Enum):
    """Enumeration of connector types based on Ecoinvent 3.11 data"""
    PCI = "pci"  # Peripheral Component Interconnect bus
    PERIPHERAL = "peripheral"  # Peripheral type bus (default for most connectors)


class ConnectorModel:
    """
    Connector carbon emissions model based on weight and material type.
    
    This class calculates carbon emissions for connectors using emission factors
    from Ecoinvent 3.11 database:
    - PCI bus connector: 112 kg CO2e/kg
    - Peripheral type bus connector: 9.38 kg CO2e/kg
    
    Formula: carbon = weight * emission_factor * number_of_connectors
    """

    def __init__(self, model_file: str = DEFAULT_CONNECTOR_MODEL_FILE):
        """
        Initializes the ConnectorModel instance with a model file.
        
        Args:
            model_file (str): The path to the model file. Defaults to DEFAULT_CONNECTOR_MODEL_FILE.
        """
        with open(model_file) as handle:
            model_data = yaml.load(handle, Loader=yaml.FullLoader)
        
        # Load emission factors for connector types
        self.emission_factors = {}
        for connector_type, factor in model_data.items():
            try:
                self.emission_factors[ConnectorType(connector_type)] = units(factor)
            except ValueError:
                log.warn(f"Unknown connector type '{connector_type}' in model file, skipping.")
        
        # Ensure we have the required factors
        if ConnectorType.PERIPHERAL not in self.emission_factors:
            log.error("Peripheral connector emission factor missing from model.")
            exit(-1)
        if ConnectorType.PCI not in self.emission_factors:
            log.error("PCI connector emission factor missing from model.")
            exit(-1)
    
    def get_carbon(
        self,
        weight: units,
        connector_type: ConnectorType = ConnectorType.PERIPHERAL,
        n_connectors: int = 1
    ) -> Carbon:
        """
        Calculates the carbon emissions for connectors based on weight and type.
        
        Args:
            weight: The weight of a single connector
            connector_type: The type of connector. Defaults to ConnectorType.PERIPHERAL
            n_connectors: The number of connectors. Defaults to 1
        
        Returns:
            Carbon: The total carbon emissions for the connectors
        
        Raises:
            AssertionError: If the weight is not in units of mass
        """
        assert weight.check(kg), f"Expected weight units for connector model but got {weight}"
        
        # Get the emission factor for this connector type
        if connector_type not in self.emission_factors:
            log.warn(
                f"Connector type {connector_type} not found in model. Using peripheral type emission factor."
            )
            emission_factor = self.emission_factors[ConnectorType.PERIPHERAL]
        else:
            emission_factor = self.emission_factors[connector_type]
        
        # Calculate carbon: weight × emission_factor × number of connectors
        carbon_per_connector = weight * emission_factor
        total_carbon = carbon_per_connector * n_connectors
        
        log.debug(
            f"Connector carbon calculation: {weight} * {emission_factor} * {n_connectors} = {total_carbon}"
        )
        
        return Carbon(total_carbon, SourceType.CONNECTOR)