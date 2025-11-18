"""PyATS/Genie parser integration for structured output from network devices."""

import logging
from typing import Optional, Any
from collections import namedtuple

logger = logging.getLogger(__name__)

# Device OS type mapping (CML node definition -> PyATS device type)
DEVICE_TYPE_MAPPING = {
    "iosv": "ios",
    "iosvl2": "ios",
    "csr1000v": "iosxe",
    "iosxe": "iosxe",
    "nxosv": "nxos",
    "nxosv9000": "nxos",
    "asav": "asa",
    "iosxrv": "iosxr",
    "iosxrv9000": "iosxr",
}

# Create a simple Device object for parsers that need it
Device = namedtuple('Device', ['name', 'os'])


class PyATSHelper:
    """Helper class for applying PyATS/Genie parsers to command output."""

    @staticmethod
    def get_device_os(node_definition: str) -> Optional[str]:
        """
        Map CML node definition to PyATS device OS type.
        
        Args:
            node_definition: CML node definition (e.g., "iosv", "csr1000v")
            
        Returns:
            PyATS OS type (e.g., "ios", "iosxe") or None if not Cisco
        """
        # Extract base definition (handle versioned definitions like "iosv-15.9")
        base_def = node_definition.split("-")[0].lower()
        return DEVICE_TYPE_MAPPING.get(base_def)

    @staticmethod
    def is_cisco_device(node_definition: str) -> bool:
        """Check if device type supports PyATS parsing."""
        return PyATSHelper.get_device_os(node_definition) is not None

    @staticmethod
    def parse_output(
        command: str,
        output: str,
        device_os: str,
        device_name: str = "device"
    ) -> dict[str, Any]:
        """
        Attempt to parse command output using Genie parser.
        
        Args:
            command: The command that was executed
            output: Raw text output from the device
            device_os: PyATS device OS type (ios, iosxe, nxos, etc.)
            device_name: Device name for parser context
            
        Returns:
            Dictionary with 'parsed' (bool), 'data' (parsed or raw), and 'parser_used' (str or None)
        """
        if not output.strip():
            return {
                "parsed": False,
                "data": output,
                "parser_used": None,
                "note": "Empty output received"
            }

        try:
            # Import Genie lookup
            from genie.libs.parser.utils import get_parser
            
            # Create a simple device object
            device = Device(name=device_name, os=device_os)
            
            # Try to find and use a parser
            try:
                parser_class = get_parser(command, device)
                if parser_class:
                    parser = parser_class(device=device_name)
                    parsed_data = parser.parse(output=output)
                    
                    return {
                        "parsed": True,
                        "data": parsed_data,
                        "parser_used": parser_class.__name__,
                        "command": command
                    }
            except Exception as parse_error:
                logger.debug(f"Parser execution failed for '{command}': {parse_error}")
                # Fall through to return raw output
                
        except ImportError as e:
            logger.warning(f"Genie parser import failed: {e}")
        except Exception as e:
            logger.debug(f"Parser lookup failed for '{command}': {e}")

        # Return raw output if parsing failed or no parser available
        return {
            "parsed": False,
            "data": output,
            "parser_used": None,
            "note": f"No parser available for '{command}' on {device_os}"
        }

    @staticmethod
    def get_available_parsers(device_os: str) -> list[str]:
        """
        Get list of available parser commands for a device OS.
        
        Args:
            device_os: PyATS device OS type
            
        Returns:
            List of command strings that have parsers
        """
        try:
            from genie import parsergen
            from genie.libs import parser
            
            # This is a simplified approach - in reality, Genie has hundreds of parsers
            # Common commands that typically have parsers:
            common_parsers = [
                "show version",
                "show ip interface brief",
                "show interfaces",
                "show ip route",
                "show ip ospf neighbor",
                "show ip bgp summary",
                "show ip eigrp neighbors",
                "show spanning-tree",
                "show vlan",
                "show cdp neighbors",
                "show lldp neighbors",
                "show inventory",
                "show running-config",
            ]
            
            return common_parsers
            
        except Exception as e:
            logger.warning(f"Could not retrieve parser list: {e}")
            return []

    @staticmethod
    def normalize_command(command: str) -> str:
        """
        Normalize command for parser matching.
        
        Some parsers are sensitive to exact command format.
        
        Args:
            command: Raw command string
            
        Returns:
            Normalized command string
        """
        # Remove extra whitespace
        cmd = " ".join(command.split())
        
        # Remove trailing pipe commands (| include, | begin, etc.)
        if "|" in cmd:
            cmd = cmd.split("|")[0].strip()
            
        return cmd

    @staticmethod
    def format_parsed_output(parsed_data: dict, indent: int = 2) -> str:
        """
        Format parsed data as readable string.
        
        Args:
            parsed_data: Parsed output dictionary
            indent: Indentation spaces
            
        Returns:
            Formatted string representation
        """
        import json
        try:
            return json.dumps(parsed_data, indent=indent, default=str)
        except:
            return str(parsed_data)
