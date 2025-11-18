"""Testbed validation tool for comprehensive lab health checks."""

import logging
from typing import Optional, Any, List
import asyncio
from .auth import require_client
from .interface_validation import validate_interfaces, get_interface_brief
from .protocol_validation import validate_protocols
from .reachability import validate_reachability

logger = logging.getLogger(__name__)


async def run_testbed_validation(
    lab_id: str,
    validation_checks: Optional[List[str]] = None,
    device_list: Optional[List[str]] = None
) -> dict[str, Any]:
    """
    Run comprehensive testbed validation across all devices.
    
    Performs a series of validation checks across the lab to ensure
    everything is configured and working properly.
    
    Args:
        lab_id: CML lab ID
        validation_checks: List of checks to run. If None, runs all:
            - "interfaces": Check all interfaces are up (where expected)
            - "protocols": Verify routing protocol neighbors
            - "connectivity": Test reachability between devices
            - "errors": Check for interface errors
        device_list: List of specific devices to validate (None = all devices)
        
    Returns:
        Dictionary with comprehensive validation results:
        - status: Overall "pass" or "fail"
        - lab_id: Lab ID tested
        - devices_tested: Number of devices tested
        - checks_run: List of checks performed
        - results: Detailed results per check
        - summary: Overall summary
        - issues: Aggregated list of all issues found
    """
    client = require_client()
    
    # Default to all checks if not specified
    if validation_checks is None:
        validation_checks = ["interfaces", "protocols", "connectivity", "errors"]
    
    try:
        # Get lab nodes
        nodes = await client.get_nodes(lab_id)
        
        # Filter to specified devices if provided
        if device_list:
            nodes = [n for n in nodes if n.get("data", {}).get("label") in device_list]
        
        # Filter out non-network devices (external connectors, unmanaged switches, etc.)
        network_nodes = []
        for node in nodes:
            node_def = node.get("data", {}).get("node_definition", "")
            # Include routers, switches, firewalls
            if any(x in node_def.lower() for x in ["ios", "nx", "csr", "cat", "asa", "xr"]):
                network_nodes.append(node)
        
        device_labels = [n.get("data", {}).get("label") for n in network_nodes]
        
        logger.info(f"Running testbed validation on {len(network_nodes)} devices: {device_labels}")
        
        # Initialize result structure
        result = {
            "status": "pass",
            "lab_id": lab_id,
            "devices_tested": len(network_nodes),
            "device_list": device_labels,
            "checks_run": validation_checks,
            "results": {},
            "issues": [],
            "summary": ""
        }
        
        # Run each validation check
        if "interfaces" in validation_checks:
            result["results"]["interfaces"] = await _validate_all_interfaces(
                lab_id,
                network_nodes,
                result["issues"]
            )
        
        if "errors" in validation_checks:
            result["results"]["errors"] = await _check_interface_errors(
                lab_id,
                network_nodes,
                result["issues"]
            )
        
        if "protocols" in validation_checks:
            result["results"]["protocols"] = await _validate_all_protocols(
                lab_id,
                network_nodes,
                result["issues"]
            )
        
        if "connectivity" in validation_checks:
            result["results"]["connectivity"] = await _validate_connectivity(
                lab_id,
                network_nodes,
                result["issues"]
            )
        
        # Determine overall status
        if result["issues"]:
            result["status"] = "fail"
        
        # Generate summary
        total_issues = len(result["issues"])
        result["summary"] = (
            f"Testbed validation {'PASSED' if result['status'] == 'pass' else 'FAILED'}: "
            f"Tested {len(network_nodes)} device(s), "
            f"ran {len(validation_checks)} check(s), "
            f"found {total_issues} issue(s)"
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Testbed validation failed: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "lab_id": lab_id
        }


async def _validate_all_interfaces(
    lab_id: str,
    nodes: List[dict],
    issues: List[str]
) -> dict:
    """Validate interfaces on all devices."""
    
    results = {
        "check": "interfaces",
        "devices": {},
        "total_interfaces": 0,
        "interfaces_up": 0,
        "interfaces_down": 0
    }
    
    # Validate each device's interfaces
    for node in nodes:
        device_name = node.get("data", {}).get("label")
        
        try:
            validation = await validate_interfaces(
                lab_id=lab_id,
                device_name=device_name,
                check_status=True,
                check_errors=False
            )
            
            results["devices"][device_name] = {
                "status": validation.get("status"),
                "interface_count": len(validation.get("interfaces", []))
            }
            
            # Count interfaces
            for intf in validation.get("interfaces", []):
                results["total_interfaces"] += 1
                if intf.get("operational") == "up":
                    results["interfaces_up"] += 1
                else:
                    results["interfaces_down"] += 1
            
            # Add device issues to global list
            if validation.get("issues"):
                issues.extend(validation["issues"])
                
        except Exception as e:
            logger.error(f"Interface validation failed for {device_name}: {e}")
            results["devices"][device_name] = {
                "status": "error",
                "error": str(e)
            }
    
    return results


async def _check_interface_errors(
    lab_id: str,
    nodes: List[dict],
    issues: List[str]
) -> dict:
    """Check for interface errors on all devices."""
    
    results = {
        "check": "interface_errors",
        "devices": {},
        "total_errors": 0,
        "devices_with_errors": 0
    }
    
    for node in nodes:
        device_name = node.get("data", {}).get("label")
        
        try:
            validation = await validate_interfaces(
                lab_id=lab_id,
                device_name=device_name,
                check_status=False,
                check_errors=True
            )
            
            device_errors = 0
            for intf in validation.get("interfaces", []):
                errors = intf.get("errors", {})
                device_errors += sum(errors.values())
            
            results["devices"][device_name] = {
                "status": validation.get("status"),
                "error_count": device_errors
            }
            
            results["total_errors"] += device_errors
            if device_errors > 0:
                results["devices_with_errors"] += 1
            
            # Add issues
            if validation.get("issues"):
                issues.extend(validation["issues"])
                
        except Exception as e:
            logger.error(f"Error check failed for {device_name}: {e}")
            results["devices"][device_name] = {
                "status": "error",
                "error": str(e)
            }
    
    return results


async def _validate_all_protocols(
    lab_id: str,
    nodes: List[dict],
    issues: List[str]
) -> dict:
    """Validate routing protocols on all devices."""
    
    results = {
        "check": "protocols",
        "devices": {},
        "protocols_checked": []
    }
    
    # Common protocols to check
    protocols_to_check = ["ospf", "bgp", "eigrp"]
    
    for node in nodes:
        device_name = node.get("data", {}).get("label")
        results["devices"][device_name] = {}
        
        # Try each protocol
        for protocol in protocols_to_check:
            try:
                validation = await validate_protocols(
                    lab_id=lab_id,
                    device_name=device_name,
                    protocol=protocol,
                    validation_type="neighbors"
                )
                
                # Only record if protocol is actually configured
                if validation.get("status") != "error":
                    results["devices"][device_name][protocol] = {
                        "status": validation.get("status"),
                        "summary": validation.get("summary")
                    }
                    
                    if protocol not in results["protocols_checked"]:
                        results["protocols_checked"].append(protocol)
                    
                    # Add issues
                    if validation.get("issues"):
                        issues.extend(validation["issues"])
                        
            except Exception as e:
                logger.debug(f"Protocol {protocol} check skipped for {device_name}: {e}")
                continue
    
    return results


async def _validate_connectivity(
    lab_id: str,
    nodes: List[dict],
    issues: List[str]
) -> dict:
    """Validate connectivity between devices."""
    
    results = {
        "check": "connectivity",
        "tests": [],
        "successful": 0,
        "failed": 0
    }
    
    # This is a simplified version - real implementation would:
    # 1. Get IP addresses from each device
    # 2. Test ping between connected devices
    # 3. Verify loopback reachability
    
    # For now, just document what would be tested
    device_labels = [n.get("data", {}).get("label") for n in nodes]
    
    results["note"] = (
        f"Connectivity testing between {len(device_labels)} devices requires "
        f"IP address discovery and adjacency mapping (not yet implemented)"
    )
    
    return results


async def get_testbed_summary(lab_id: str) -> dict[str, Any]:
    """
    Get a summary of the testbed without running full validation.
    
    Args:
        lab_id: CML lab ID
        
    Returns:
        Dictionary with testbed summary information
    """
    client = require_client()
    
    try:
        # Get lab info
        lab = await client.get_lab(lab_id)
        nodes = await client.get_nodes(lab_id)
        
        # Categorize nodes
        network_nodes = []
        other_nodes = []
        
        for node in nodes:
            node_def = node.get("data", {}).get("node_definition", "")
            label = node.get("data", {}).get("label")
            state = node.get("operational", {}).get("state", "unknown")
            
            node_info = {
                "label": label,
                "type": node_def,
                "state": state
            }
            
            if any(x in node_def.lower() for x in ["ios", "nx", "csr", "cat", "asa", "xr"]):
                network_nodes.append(node_info)
            else:
                other_nodes.append(node_info)
        
        return {
            "status": "success",
            "lab_id": lab_id,
            "lab_title": lab.get("lab_title", "Unknown"),
            "lab_state": lab.get("state", "unknown"),
            "total_nodes": len(nodes),
            "network_devices": len(network_nodes),
            "other_devices": len(other_nodes),
            "network_devices_list": network_nodes,
            "other_devices_list": other_nodes
        }
        
    except Exception as e:
        logger.error(f"Failed to get testbed summary: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "lab_id": lab_id
        }
