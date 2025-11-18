"""Reachability validation tool for ping and traceroute testing."""

import logging
from typing import Optional, Any
from .execution import execute_command
from .auth import require_client
from ..utils import parse_ping_output, parse_traceroute_output, validate_reachability_result

logger = logging.getLogger(__name__)


async def validate_reachability(
    lab_id: str,
    source_device: str,
    destination: str,
    test_type: str = "ping",
    count: int = 5,
    expected_success: bool = True
) -> dict[str, Any]:
    """
    Test network reachability using ping or traceroute.
    
    Args:
        lab_id: CML lab ID
        source_device: Source device label/name
        destination: Destination IP address or hostname
        test_type: "ping" or "traceroute"
        count: Number of packets to send (ping only)
        expected_success: Whether connectivity is expected to work
        
    Returns:
        Dictionary with reachability test results:
        - status: "pass" or "fail"
        - test_type: Type of test performed
        - source: Source device
        - destination: Target IP/hostname
        - reachable: Whether destination was reachable
        - details: Test-specific details (RTT, packet loss, hops, etc.)
        - summary: Human-readable summary
    """
    require_client()
    
    test_type = test_type.lower()
    
    if test_type not in ["ping", "traceroute"]:
        return {
            "status": "error",
            "error": f"Invalid test_type: {test_type}. Must be 'ping' or 'traceroute'",
            "supported_types": ["ping", "traceroute"]
        }
    
    try:
        # Build command
        if test_type == "ping":
            command = f"ping {destination} repeat {count}"
        else:  # traceroute
            command = f"traceroute {destination}"
        
        # Execute command
        result = await execute_command(
            lab_id=lab_id,
            device_name=source_device,
            command=command,
            use_parser=True  # Try to use parser if available
        )
        
        if not result["success"]:
            return {
                "status": "error",
                "error": result.get("error", "Command execution failed"),
                "test_type": test_type,
                "source": source_device,
                "destination": destination
            }
        
        # Parse output based on test type
        raw_output = result.get("output", "")
        
        if test_type == "ping":
            return _validate_ping_result(
                source_device,
                destination,
                raw_output,
                result.get("parsed"),
                result.get("data"),
                expected_success
            )
        else:  # traceroute
            return _validate_traceroute_result(
                source_device,
                destination,
                raw_output,
                result.get("parsed"),
                result.get("data")
            )
        
    except Exception as e:
        logger.error(f"Reachability test failed: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "test_type": test_type,
            "source": source_device,
            "destination": destination
        }


def _validate_ping_result(
    source: str,
    destination: str,
    raw_output: str,
    parsed: bool,
    data: Any,
    expected_success: bool
) -> dict:
    """Validate ping results."""
    
    # Try to extract ping statistics
    if parsed and isinstance(data, dict):
        # If parser gave us structured data, use it
        success_rate = data.get("success_rate_percent", 0)
        reachable = success_rate > 0
        
        stats = {
            "packets_sent": data.get("packets_sent", 0),
            "packets_received": data.get("packets_received", 0),
            "packet_loss_percent": 100 - success_rate,
            "rtt_min": data.get("rtt_min"),
            "rtt_avg": data.get("rtt_avg"),
            "rtt_max": data.get("rtt_max")
        }
    else:
        # Parse raw output
        ping_stats = parse_ping_output(raw_output)
        reachable = ping_stats["success"]
        stats = {
            "packets_sent": ping_stats["packets_sent"],
            "packets_received": ping_stats["packets_received"],
            "packet_loss_percent": ping_stats["packet_loss_percent"],
            "rtt_min": ping_stats["rtt_min"],
            "rtt_avg": ping_stats["rtt_avg"],
            "rtt_max": ping_stats["rtt_max"]
        }
    
    # Validate against expected result
    validation = validate_reachability_result(
        {"success": reachable, **stats},
        expected_success
    )
    
    # Build result
    result = {
        "status": "pass" if validation["passed"] else "fail",
        "test_type": "ping",
        "source": source,
        "destination": destination,
        "reachable": reachable,
        "expected_reachable": expected_success,
        "details": stats,
        "raw_output": raw_output if not parsed else None
    }
    
    # Generate summary
    if reachable:
        result["summary"] = (
            f"Ping from {source} to {destination} successful: "
            f"{stats['packets_received']}/{stats['packets_sent']} packets received, "
            f"avg RTT {stats['rtt_avg']}ms"
        )
    else:
        result["summary"] = (
            f"Ping from {source} to {destination} failed: "
            f"{stats['packet_loss_percent']:.0f}% packet loss"
        )
    
    # Add validation message
    if not validation["passed"]:
        result["summary"] += f" (Expected {'success' if expected_success else 'failure'})"
    
    return result


def _validate_traceroute_result(
    source: str,
    destination: str,
    raw_output: str,
    parsed: bool,
    data: Any
) -> dict:
    """Validate traceroute results."""
    
    # Try to extract hop information
    if parsed and isinstance(data, dict):
        # If parser gave us structured data, use it
        hops = []
        if "hops" in data:
            for hop_num, hop_data in data["hops"].items():
                hops.append({
                    "hop": int(hop_num),
                    "ip": hop_data.get("ip"),
                    "hostname": hop_data.get("hostname"),
                    "rtt": hop_data.get("rtt")
                })
        
        destination_reached = any(h.get("ip") == destination for h in hops)
    else:
        # Parse raw output
        trace_stats = parse_traceroute_output(raw_output)
        hops = trace_stats["hops"]
        destination_reached = trace_stats["destination_reached"]
    
    # Build result
    result = {
        "status": "pass" if destination_reached else "fail",
        "test_type": "traceroute",
        "source": source,
        "destination": destination,
        "destination_reached": destination_reached,
        "hop_count": len(hops),
        "hops": hops,
        "raw_output": raw_output if not parsed else None
    }
    
    # Generate summary
    if destination_reached:
        result["summary"] = (
            f"Traceroute from {source} to {destination} successful: "
            f"{len(hops)} hops"
        )
    else:
        result["summary"] = (
            f"Traceroute from {source} to {destination} incomplete: "
            f"reached {len(hops)} hops but destination not confirmed"
        )
    
    return result


async def test_connectivity_matrix(
    lab_id: str,
    devices: list[str],
    test_all_to_all: bool = True
) -> dict[str, Any]:
    """
    Test connectivity between multiple devices in a matrix.
    
    Args:
        lab_id: CML lab ID
        devices: List of device names to test
        test_all_to_all: If True, test all pairs; if False, test sequential pairs
        
    Returns:
        Dictionary with connectivity matrix results
    """
    require_client()
    
    results = {
        "status": "success",
        "lab_id": lab_id,
        "devices": devices,
        "tests": [],
        "summary": {
            "total_tests": 0,
            "successful": 0,
            "failed": 0
        }
    }
    
    # Get device IPs (would need to query devices for their IPs)
    # This is a simplified version
    
    try:
        if test_all_to_all:
            # Test every device to every other device
            for src in devices:
                for dst in devices:
                    if src != dst:
                        # Would need to get dst IP address first
                        # For now, placeholder
                        results["tests"].append({
                            "source": src,
                            "destination": dst,
                            "note": "IP lookup not implemented"
                        })
                        results["summary"]["total_tests"] += 1
        else:
            # Test sequential pairs
            for i in range(len(devices) - 1):
                src = devices[i]
                dst = devices[i + 1]
                results["tests"].append({
                    "source": src,
                    "destination": dst,
                    "note": "IP lookup not implemented"
                })
                results["summary"]["total_tests"] += 1
        
        return results
        
    except Exception as e:
        logger.error(f"Connectivity matrix test failed: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "lab_id": lab_id
        }
