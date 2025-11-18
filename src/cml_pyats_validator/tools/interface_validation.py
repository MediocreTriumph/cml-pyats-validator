"""Interface validation tool for checking interface status and errors."""

import logging
from typing import Optional, Any
from .execution import execute_command
from .auth import require_client
from ..utils import extract_interface_errors

logger = logging.getLogger(__name__)


async def validate_interfaces(
    lab_id: str,
    device_name: str,
    interface: Optional[str] = None,
    check_errors: bool = True,
    check_status: bool = True
) -> dict[str, Any]:
    """
    Validate interface status and health.
    
    Checks interface operational status, errors, and other health metrics.
    
    Args:
        lab_id: CML lab ID
        device_name: Device label/name
        interface: Specific interface to check (None = all interfaces)
        check_errors: If True, check for interface errors
        check_status: If True, check interface operational status
        
    Returns:
        Dictionary with validation results:
        - status: "pass" or "fail"
        - interfaces: List of interface validation results
        - summary: Human-readable summary
        - issues: List of any issues found
    """
    require_client()
    
    try:
        # Determine which command to use
        if interface:
            command = f"show interfaces {interface}"
        else:
            command = "show interfaces"
        
        # Execute command with parser
        result = await execute_command(
            lab_id=lab_id,
            device_name=device_name,
            command=command,
            use_parser=True
        )
        
        if not result["success"]:
            return {
                "status": "error",
                "error": result.get("error", "Command execution failed"),
                "device": device_name
            }
        
        # Build validation result
        validation_result = {
            "status": "pass",
            "device": device_name,
            "command": command,
            "parsed": result.get("parsed", False),
            "interfaces": [],
            "issues": [],
            "summary": ""
        }
        
        # Validate parsed data
        if result.get("parsed"):
            interfaces_data = result["data"]
            validation_result["interfaces"] = _validate_interfaces_data(
                interfaces_data,
                check_errors,
                check_status,
                validation_result["issues"]
            )
        else:
            # Try to extract some info from raw output
            raw_output = result.get("output", "")
            validation_result["raw_output"] = raw_output
            
            if check_errors:
                errors = extract_interface_errors(raw_output)
                if errors["has_errors"]:
                    validation_result["issues"].append(
                        f"Detected {errors['total_errors']} errors in raw output"
                    )
        
        # Update status if issues found
        if validation_result["issues"]:
            validation_result["status"] = "fail"
        
        # Generate summary
        total_interfaces = len(validation_result["interfaces"])
        validation_result["summary"] = (
            f"Validated {total_interfaces} interface(s), "
            f"found {len(validation_result['issues'])} issue(s)"
        )
        
        return validation_result
        
    except Exception as e:
        logger.error(f"Interface validation failed: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "device": device_name
        }


def _validate_interfaces_data(
    interfaces_data: dict,
    check_errors: bool,
    check_status: bool,
    issues: list
) -> list[dict]:
    """
    Validate parsed interface data.
    
    Args:
        interfaces_data: Parsed interface data from Genie
        check_errors: Whether to check for errors
        check_status: Whether to check operational status
        issues: List to append issues to
        
    Returns:
        List of interface validation results
    """
    validated_interfaces = []
    
    # Genie parser typically structures interfaces under an "interfaces" key
    interfaces = interfaces_data
    if isinstance(interfaces_data, dict) and "interfaces" in interfaces_data:
        interfaces = interfaces_data["interfaces"]
    
    if not isinstance(interfaces, dict):
        return validated_interfaces
    
    for intf_name, intf_data in interfaces.items():
        intf_result = {
            "name": intf_name,
            "operational": "unknown",
            "protocol": "unknown",
            "errors": {},
            "issues": []
        }
        
        # Check operational status
        if check_status:
            oper_status = intf_data.get("oper_status", "").lower()
            line_protocol = intf_data.get("line_protocol", "").lower()
            
            intf_result["operational"] = oper_status
            intf_result["protocol"] = line_protocol
            
            # Flag down interfaces (except admin down)
            if oper_status == "down":
                admin_state = intf_data.get("enabled", True)
                if admin_state:  # If enabled but down, that's an issue
                    issue = f"Interface {intf_name} is down"
                    intf_result["issues"].append(issue)
                    issues.append(issue)
            
            if "up" in oper_status and "down" in line_protocol:
                issue = f"Interface {intf_name} protocol is down (layer 2 issue)"
                intf_result["issues"].append(issue)
                issues.append(issue)
        
        # Check for errors
        if check_errors:
            counters = intf_data.get("counters", {})
            
            error_fields = [
                "in_errors",
                "in_crc_errors",
                "in_frame",
                "in_overrun",
                "in_ignored",
                "out_errors",
                "out_collision"
            ]
            
            for field in error_fields:
                error_count = counters.get(field, 0)
                if error_count > 0:
                    intf_result["errors"][field] = error_count
                    
                    # High error counts are issues
                    if error_count > 100:
                        issue = f"Interface {intf_name} has {error_count} {field}"
                        intf_result["issues"].append(issue)
                        issues.append(issue)
            
            # Check CRC specifically (any CRC is bad)
            if counters.get("in_crc_errors", 0) > 0:
                if not any("CRC" in i for i in intf_result["issues"]):
                    issue = f"Interface {intf_name} has CRC errors (possible physical issue)"
                    intf_result["issues"].append(issue)
                    issues.append(issue)
        
        validated_interfaces.append(intf_result)
    
    return validated_interfaces


async def get_interface_brief(
    lab_id: str,
    device_name: str
) -> dict[str, Any]:
    """
    Get brief interface status (similar to 'show ip interface brief').
    
    Args:
        lab_id: CML lab ID
        device_name: Device label/name
        
    Returns:
        Dictionary with brief interface information
    """
    require_client()
    
    try:
        result = await execute_command(
            lab_id=lab_id,
            device_name=device_name,
            command="show ip interface brief",
            use_parser=True
        )
        
        if not result["success"]:
            return {
                "status": "error",
                "error": result.get("error", "Command execution failed")
            }
        
        return {
            "status": "success",
            "device": device_name,
            "parsed": result.get("parsed", False),
            "data": result.get("data"),
            "raw_output": result.get("output") if not result.get("parsed") else None
        }
        
    except Exception as e:
        logger.error(f"Failed to get interface brief: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "device": device_name
        }
