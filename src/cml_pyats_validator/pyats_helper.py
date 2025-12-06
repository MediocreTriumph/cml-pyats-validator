"""
PyATS Helper

Handles PyATS/Genie parser integration for command output parsing.
"""

from genie.conf.base import Device
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

# Map CML device definitions to Genie OS types
DEVICE_TYPE_MAPPING = {
    'iosv': 'iosxe',
    'csr1000v': 'iosxe',
    'iosvl2': 'iosxe',
    'nxosv': 'nxos',
    'nxosv9000': 'nxos',
    'iosxrv': 'iosxr',
    'iosxrv9000': 'iosxr',
    'asav': 'asa',
}


def get_genie_os(cml_device_type: str) -> Optional[str]:
    """Map CML device type to Genie OS type
    
    Args:
        cml_device_type: CML node definition (e.g., 'iosv', 'csr1000v')
    
    Returns:
        Genie OS type or None if not a Cisco device
    """
    return DEVICE_TYPE_MAPPING.get(cml_device_type)


def is_cisco_device(cml_device_type: str) -> bool:
    """Check if device is a Cisco device with parser support"""
    return cml_device_type in DEVICE_TYPE_MAPPING


def parse_output(command: str, output: str, os_type: str) -> Dict[str, Any]:
    """Parse command output using PyATS/Genie parsers
    
    Args:
        command: Command that was executed
        output: Raw command output
        os_type: Genie OS type (e.g., 'iosxe', 'nxos')
    
    Returns:
        Parsed output as dictionary
    
    Raises:
        Exception if parsing fails
    """
    try:
        # Create temporary device for parsing
        device = Device("temp", os=os_type)
        device.custom.abstraction = {'order': ['os']}
        
        # Parse the output
        parsed = device.parse(command, output=output)
        
        logger.info(f"Successfully parsed '{command}' output using {os_type} parser")
        return parsed
        
    except Exception as e:
        logger.warning(f"Failed to parse '{command}' output: {e}")
        raise


def has_parser(command: str, os_type: str) -> bool:
    """Check if a parser exists for the command
    
    Args:
        command: Command to check
        os_type: Genie OS type
    
    Returns:
        True if parser exists, False otherwise
    """
    try:
        device = Device("temp", os=os_type)
        device.custom.abstraction = {'order': ['os']}
        # Try to get parser
        device.parse(command, output="")
        return True
    except:
        return False
