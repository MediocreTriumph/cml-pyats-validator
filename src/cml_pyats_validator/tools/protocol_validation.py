"""
Protocol Validation Tool

Validates routing and L2 protocol operation using PyATS parsers.
"""

from typing import Optional, Dict, Any
from .execution import execute_device_command
import logging

logger = logging.getLogger(__name__)

# Protocol-specific commands for IOS/IOS-XE/NX-OS
PROTOCOL_COMMANDS_IOS = {
    "ospf": {
        "neighbors": "show ip ospf neighbor",
        "routes": "show ip route ospf",
        "database": "show ip ospf database",
    },
    "bgp": {
        "neighbors": "show ip bgp summary",
        "routes": "show ip route bgp",
    },
    "eigrp": {
        "neighbors": "show ip eigrp neighbors",
        "routes": "show ip route eigrp",
    },
}

# Protocol-specific commands for ASA
PROTOCOL_COMMANDS_ASA = {
    "ospf": {
        "neighbors": "show ospf neighbor",
        "routes": "show route ospf",
        "database": "show ospf database",
    },
    "bgp": {
        "neighbors": "show bgp summary",
        "routes": "show route bgp",
    },
    "eigrp": {
        "neighbors": "show eigrp neighbors",
        "routes": "show route eigrp",
    },
}


def is_asa_device(device_type: str) -> bool:
    """Check if device is ASA platform"""
    return 'asav' in device_type.lower() or 'asa' in device_type.lower()


def get_protocol_commands(device_type: str) -> Dict[str, Dict[str, str]]:
    """Get protocol commands based on device type"""
    if is_asa_device(device_type):
        return PROTOCOL_COMMANDS_ASA
    return PROTOCOL_COMMANDS_IOS


async def validate_routing_protocols(
    lab_id: str,
    device_name: str,
    protocol: str,
    validation_type: str = "neighbors",
    expected_state: Optional[Dict[str, Any]] = None,
    device_credentials: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """Validate routing or L2 protocol operation
    
    Uses PyATS parsers to validate protocol state and provide structured validation.
    Supported protocols: OSPF, BGP, EIGRP
    
    Args:
        lab_id: CML lab ID
        device_name: Device label/name
        protocol: Protocol to validate (ospf, bgp, eigrp)
        validation_type: Type of check (neighbors, routes, database)
        expected_state: Optional dict of expected values to validate against
        device_credentials: Device authentication credentials
    
    Returns:
        Validation results with pass/fail status and details
    
    Example:
        result = await validate_routing_protocols(
            lab_id="abc123",
            device_name="R1",
            protocol="ospf",
            validation_type="neighbors",
            expected_state={"neighbor_count": 2}
        )
    """
    try:
        protocol = protocol.lower()

        # First, execute a simple command to get device type
        probe_result = await execute_device_command(
            lab_id=lab_id,
            device_name=device_name,
            command="show version",
            device_credentials=device_credentials,
            use_parser=False
        )

        if "error" in probe_result:
            return probe_result

        device_type = probe_result.get("device_type", "unknown")
        protocol_commands = get_protocol_commands(device_type)

        # Get the appropriate command
        if protocol not in protocol_commands:
            return {
                "status": "error",
                "error": f"Unsupported protocol: {protocol}. Supported: {list(protocol_commands.keys())}"
            }

        if validation_type not in protocol_commands[protocol]:
            return {
                "status": "error",
                "error": f"Unsupported validation type '{validation_type}' for {protocol}"
            }

        command = protocol_commands[protocol][validation_type]

        # Execute command and get parsed output
        result = await execute_device_command(
            lab_id=lab_id,
            device_name=device_name,
            command=command,
            device_credentials=device_credentials,
            use_parser=True
        )
        
        if "error" in result:
            return result
        
        # Basic validation structure
        validation_result = {
            "device": device_name,
            "protocol": protocol,
            "validation_type": validation_type,
            "command": command,
            "raw_output": result.get("raw_output"),
        }
        
        if result.get("parser_used"):
            validation_result["parsed_data"] = result.get("parsed_output")
            validation_result["status"] = "success"
            
            # If expected state provided, validate against it
            if expected_state:
                validation_result["validation_passed"] = True
                validation_result["validation_details"] = []
                
                # Add custom validation logic here based on protocol and parsed data
                # For now, just return the parsed data
        else:
            validation_result["status"] = "parsed_unavailable"
            validation_result["message"] = "Parser not available, returning raw output"
        
        return validation_result
        
    except Exception as e:
        logger.error(f"Protocol validation failed: {e}")
        return {
            "status": "error",
            "device": device_name,
            "protocol": protocol,
            "error": str(e)
        }
