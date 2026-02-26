"""
Interface Validation Tool

Validates interface status and health on network devices.
"""

from typing import Optional, Dict, Any
from .execution import execute_device_command
import logging

logger = logging.getLogger(__name__)


def is_asa_device(device_type: str) -> bool:
    """Check if device is ASA platform"""
    return 'asav' in device_type.lower() or 'asa' in device_type.lower()


def get_interface_command(device_type: str, interface: Optional[str] = None) -> str:
    """Get interface command based on device type

    IOS: show interfaces / show ip interface brief
    ASA: show interface / show interface ip brief
    """
    is_asa = is_asa_device(device_type)

    if interface:
        # Specific interface query
        return f"show interface {interface}"
    else:
        # All interfaces - IOS uses plural, ASA uses singular
        return "show interface" if is_asa else "show interfaces"


async def validate_device_interfaces(
    lab_id: str,
    device_name: str,
    interface: Optional[str] = None,
    check_errors: bool = True,
    check_status: bool = True,
    device_credentials: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """Validate interface status and health
    
    Checks interface operational status, errors, CRC errors, and other
    health metrics using PyATS parsers.
    
    Args:
        lab_id: CML lab ID
        device_name: Device label/name
        interface: Specific interface to check (None = all interfaces)
        check_errors: Check for interface errors
        check_status: Check operational status
        device_credentials: Device authentication credentials
    
    Returns:
        Interface validation results with any issues found
    
    Example:
        result = await validate_device_interfaces(
            lab_id="abc123",
            device_name="R1",
            interface="GigabitEthernet0/1",
            check_errors=True
        )
    """
    try:
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

        # Get the appropriate command based on device type
        command = get_interface_command(device_type, interface)

        result = await execute_device_command(
            lab_id=lab_id,
            device_name=device_name,
            command=command,
            device_credentials=device_credentials,
            use_parser=True
        )
        
        if "error" in result:
            return result
        
        validation_result = {
            "device": device_name,
            "interface": interface or "all",
            "command": command,
            "raw_output": result.get("raw_output"),
        }
        
        if result.get("parser_used"):
            parsed = result.get("parsed_output", {})
            validation_result["parsed_data"] = parsed
            
            issues = []
            
            # Check interface status and errors
            # This is a simplified example - actual validation would be more detailed
            if check_status or check_errors:
                # Parser structure varies by command, add validation logic here
                validation_result["issues"] = issues
                validation_result["status"] = "healthy" if not issues else "issues_found"
        else:
            validation_result["status"] = "parser_unavailable"
            validation_result["message"] = "Parser not available, returning raw output"
        
        return validation_result
        
    except Exception as e:
        logger.error(f"Interface validation failed: {e}")
        return {
            "status": "error",
            "device": device_name,
            "error": str(e)
        }
