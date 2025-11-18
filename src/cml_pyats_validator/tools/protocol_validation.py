"""Protocol validation tool for routing and L2 protocols."""

import logging
from typing import Optional, Any
from .execution import execute_command
from .auth import require_client

logger = logging.getLogger(__name__)

# Protocol command mappings
PROTOCOL_COMMANDS = {
    "ospf": {
        "neighbors": "show ip ospf neighbor",
        "routes": "show ip route ospf",
        "state": "show ip ospf",
        "interface": "show ip ospf interface",
        "database": "show ip ospf database"
    },
    "bgp": {
        "neighbors": "show ip bgp summary",
        "routes": "show ip route bgp",
        "state": "show ip bgp",
        "peers": "show ip bgp neighbors"
    },
    "eigrp": {
        "neighbors": "show ip eigrp neighbors",
        "routes": "show ip route eigrp",
        "topology": "show ip eigrp topology",
        "interfaces": "show ip eigrp interfaces"
    },
    "rip": {
        "neighbors": "show ip rip neighbors",
        "routes": "show ip route rip",
        "database": "show ip rip database"
    },
    "stp": {
        "state": "show spanning-tree",
        "root": "show spanning-tree root",
        "bridge": "show spanning-tree bridge",
        "summary": "show spanning-tree summary"
    },
    "vtp": {
        "status": "show vtp status",
        "counters": "show vtp counters"
    },
    "hsrp": {
        "brief": "show standby brief",
        "state": "show standby"
    },
    "vrrp": {
        "brief": "show vrrp brief",
        "state": "show vrrp"
    }
}


async def validate_protocols(
    lab_id: str,
    device_name: str,
    protocol: str,
    validation_type: str = "neighbors",
    expected_state: Optional[dict] = None
) -> dict[str, Any]:
    """
    Validate routing or L2 protocol status using PyATS parsers.
    
    Supports: OSPF, BGP, EIGRP, RIP, STP, VTP, HSRP, VRRP
    
    Args:
        lab_id: CML lab ID
        device_name: Device label/name
        protocol: Protocol to validate (ospf, bgp, eigrp, stp, etc.)
        validation_type: Type of validation (neighbors, routes, state, etc.)
        expected_state: Optional dictionary of expected values to validate against
        
    Returns:
        Dictionary with validation results:
        - status: "pass" or "fail"
        - protocol: Protocol being validated
        - validation_type: Type of validation performed
        - data: Parsed protocol data
        - issues: List of any issues found
        - summary: Human-readable summary
    """
    require_client()
    
    protocol = protocol.lower()
    validation_type = validation_type.lower()
    
    # Check if protocol is supported
    if protocol not in PROTOCOL_COMMANDS:
        return {
            "status": "error",
            "error": f"Unsupported protocol: {protocol}",
            "supported_protocols": list(PROTOCOL_COMMANDS.keys())
        }
    
    # Check if validation type is supported for this protocol
    if validation_type not in PROTOCOL_COMMANDS[protocol]:
        return {
            "status": "error",
            "error": f"Unsupported validation type '{validation_type}' for {protocol}",
            "supported_types": list(PROTOCOL_COMMANDS[protocol].keys())
        }
    
    # Get the command to execute
    command = PROTOCOL_COMMANDS[protocol][validation_type]
    
    try:
        # Execute command and get parsed output
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
                "protocol": protocol,
                "validation_type": validation_type
            }
        
        # Build validation result
        validation_result = {
            "status": "pass",  # Will change to "fail" if issues found
            "protocol": protocol,
            "validation_type": validation_type,
            "command": command,
            "device": device_name,
            "parsed": result.get("parsed", False),
            "data": result.get("data"),
            "issues": [],
            "summary": ""
        }
        
        # Protocol-specific validation logic
        if result.get("parsed"):
            validation_result.update(
                _validate_parsed_protocol_data(
                    protocol,
                    validation_type,
                    result["data"],
                    expected_state
                )
            )
        else:
            # Can't validate unparsed data deeply
            validation_result["summary"] = (
                f"Command executed but output not parsed. "
                f"Review raw output for {protocol} status."
            )
            validation_result["raw_output"] = result.get("output", "")
        
        return validation_result
        
    except Exception as e:
        logger.error(f"Protocol validation failed: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "protocol": protocol,
            "validation_type": validation_type,
            "device": device_name
        }


def _validate_parsed_protocol_data(
    protocol: str,
    validation_type: str,
    data: dict,
    expected_state: Optional[dict]
) -> dict:
    """
    Validate parsed protocol data against expected state.
    
    Returns dict with status, issues, and summary.
    """
    issues = []
    
    # OSPF validation
    if protocol == "ospf" and validation_type == "neighbors":
        neighbors = _extract_ospf_neighbors(data)
        
        if not neighbors:
            issues.append("No OSPF neighbors found")
        else:
            for neighbor in neighbors:
                if neighbor.get("state") != "FULL":
                    issues.append(
                        f"Neighbor {neighbor.get('neighbor_id')} in state "
                        f"{neighbor.get('state')} (expected FULL)"
                    )
        
        summary = f"OSPF has {len(neighbors)} neighbor(s)"
        if issues:
            summary += f", {len(issues)} issue(s) found"
    
    # BGP validation
    elif protocol == "bgp" and validation_type == "neighbors":
        neighbors = _extract_bgp_neighbors(data)
        
        if not neighbors:
            issues.append("No BGP neighbors found")
        else:
            for neighbor in neighbors:
                state = neighbor.get("state", "").lower()
                if "established" not in state:
                    issues.append(
                        f"Neighbor {neighbor.get('neighbor')} in state "
                        f"{neighbor.get('state')} (expected Established)"
                    )
        
        summary = f"BGP has {len(neighbors)} neighbor(s)"
        if issues:
            summary += f", {len(issues)} issue(s) found"
    
    # EIGRP validation
    elif protocol == "eigrp" and validation_type == "neighbors":
        neighbors = _extract_eigrp_neighbors(data)
        
        if not neighbors:
            issues.append("No EIGRP neighbors found")
        
        summary = f"EIGRP has {len(neighbors)} neighbor(s)"
    
    # Generic validation for other protocols
    else:
        summary = f"Protocol {protocol} data retrieved successfully"
        if expected_state:
            summary += " (custom validation not implemented)"
    
    # Check against expected state if provided
    if expected_state:
        for key, expected_value in expected_state.items():
            # Simple key-value comparison
            if key in data and data[key] != expected_value:
                issues.append(
                    f"Expected {key}={expected_value}, got {data[key]}"
                )
    
    return {
        "status": "fail" if issues else "pass",
        "issues": issues,
        "summary": summary
    }


def _extract_ospf_neighbors(data: dict) -> list[dict]:
    """Extract OSPF neighbor information from parsed data."""
    neighbors = []
    
    # Genie parser structure varies, try common formats
    if "interfaces" in data:
        for intf_name, intf_data in data["interfaces"].items():
            if "neighbors" in intf_data:
                for neighbor_id, neighbor_data in intf_data["neighbors"].items():
                    neighbors.append({
                        "neighbor_id": neighbor_id,
                        "interface": intf_name,
                        "state": neighbor_data.get("state"),
                        "address": neighbor_data.get("address")
                    })
    
    return neighbors


def _extract_bgp_neighbors(data: dict) -> list[dict]:
    """Extract BGP neighbor information from parsed data."""
    neighbors = []
    
    # Common BGP summary structure
    if "vrf" in data:
        for vrf_name, vrf_data in data["vrf"].items():
            if "neighbor" in vrf_data:
                for neighbor_addr, neighbor_data in vrf_data["neighbor"].items():
                    neighbors.append({
                        "neighbor": neighbor_addr,
                        "state": neighbor_data.get("address_family", {}).get("", {}).get("state"),
                        "as": neighbor_data.get("as")
                    })
    
    return neighbors


def _extract_eigrp_neighbors(data: dict) -> list[dict]:
    """Extract EIGRP neighbor information from parsed data."""
    neighbors = []
    
    # EIGRP neighbors structure
    if "eigrp_instance" in data:
        for instance, instance_data in data["eigrp_instance"].items():
            if "vrf" in instance_data:
                for vrf, vrf_data in instance_data["vrf"].items():
                    if "address_family" in vrf_data:
                        for af, af_data in vrf_data["address_family"].items():
                            if "eigrp_interface" in af_data:
                                for intf, intf_data in af_data["eigrp_interface"].items():
                                    if "eigrp_nbr" in intf_data:
                                        for nbr, nbr_data in intf_data["eigrp_nbr"].items():
                                            neighbors.append({
                                                "neighbor": nbr,
                                                "interface": intf,
                                                "hold_time": nbr_data.get("hold")
                                            })
    
    return neighbors
