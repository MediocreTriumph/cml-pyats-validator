"""Utility functions for CML PyATS Validator."""

import re
import difflib
from typing import Optional


def parse_ping_output(output: str) -> dict:
    """
    Parse ping command output to extract success rate and statistics.
    
    Args:
        output: Raw ping command output
        
    Returns:
        Dictionary with parsed ping statistics
    """
    result = {
        "success": False,
        "packets_sent": 0,
        "packets_received": 0,
        "packet_loss_percent": 100.0,
        "rtt_min": None,
        "rtt_avg": None,
        "rtt_max": None,
        "raw_output": output
    }
    
    # Parse success rate (Cisco format: "Success rate is 100 percent (5/5)")
    success_match = re.search(r'Success rate is (\d+) percent \((\d+)/(\d+)\)', output)
    if success_match:
        success_rate = int(success_match.group(1))
        received = int(success_match.group(2))
        sent = int(success_match.group(3))
        
        result["success"] = success_rate > 0
        result["packets_sent"] = sent
        result["packets_received"] = received
        result["packet_loss_percent"] = 100 - success_rate
    
    # Parse RTT statistics (Cisco format: "min/avg/max = 1/2/4 ms")
    rtt_match = re.search(r'min/avg/max = (\d+)/(\d+)/(\d+)', output)
    if rtt_match:
        result["rtt_min"] = int(rtt_match.group(1))
        result["rtt_avg"] = int(rtt_match.group(2))
        result["rtt_max"] = int(rtt_match.group(3))
    
    return result


def parse_traceroute_output(output: str) -> dict:
    """
    Parse traceroute command output to extract hop information.
    
    Args:
        output: Raw traceroute command output
        
    Returns:
        Dictionary with parsed traceroute results
    """
    result = {
        "success": False,
        "hops": [],
        "destination_reached": False,
        "raw_output": output
    }
    
    # Parse each hop line
    hop_pattern = re.compile(r'^\s*(\d+)\s+([^\s]+)\s+\(([^\)]+)\)\s+(.+)$', re.MULTILINE)
    
    for match in hop_pattern.finditer(output):
        hop_num = int(match.group(1))
        hostname = match.group(2)
        ip_address = match.group(3)
        timing_info = match.group(4)
        
        result["hops"].append({
            "hop": hop_num,
            "hostname": hostname,
            "ip": ip_address,
            "timing": timing_info.strip()
        })
        result["success"] = True
    
    # Check if destination was reached (no asterisks in last hop)
    if result["hops"]:
        last_hop = result["hops"][-1]["timing"]
        result["destination_reached"] = "*" not in last_hop
    
    return result


def compare_configs(
    config1: str,
    config2: str,
    ignore_whitespace: bool = True,
    context_lines: int = 3
) -> dict:
    """
    Compare two configuration strings and return differences.
    
    Args:
        config1: First configuration
        config2: Second configuration
        ignore_whitespace: If True, ignore whitespace differences
        context_lines: Number of context lines to show around differences
        
    Returns:
        Dictionary with comparison results
    """
    # Split into lines
    lines1 = config1.splitlines(keepends=True)
    lines2 = config2.splitlines(keepends=True)
    
    # Optionally strip whitespace
    if ignore_whitespace:
        lines1 = [line.strip() + '\n' for line in lines1]
        lines2 = [line.strip() + '\n' for line in lines2]
    
    # Generate unified diff
    diff = list(difflib.unified_diff(
        lines1,
        lines2,
        fromfile='config1',
        tofile='config2',
        n=context_lines
    ))
    
    # Count changes
    additions = sum(1 for line in diff if line.startswith('+') and not line.startswith('+++'))
    deletions = sum(1 for line in diff if line.startswith('-') and not line.startswith('---'))
    
    return {
        "identical": len(diff) == 0,
        "additions": additions,
        "deletions": deletions,
        "total_changes": additions + deletions,
        "diff": ''.join(diff),
        "diff_lines": diff
    }


def extract_interface_errors(interface_output: str) -> dict:
    """
    Extract error counts from interface output.
    
    Args:
        interface_output: Raw output from show interface command
        
    Returns:
        Dictionary with error statistics
    """
    errors = {
        "input_errors": 0,
        "output_errors": 0,
        "crc_errors": 0,
        "frame_errors": 0,
        "overrun_errors": 0,
        "ignored_errors": 0,
        "collisions": 0
    }
    
    # Parse various error counters
    patterns = {
        "input_errors": r'(\d+) input errors',
        "output_errors": r'(\d+) output errors',
        "crc_errors": r'(\d+) CRC',
        "frame_errors": r'(\d+) frame',
        "overrun_errors": r'(\d+) overrun',
        "ignored_errors": r'(\d+) ignored',
        "collisions": r'(\d+) collisions'
    }
    
    for key, pattern in patterns.items():
        match = re.search(pattern, interface_output, re.IGNORECASE)
        if match:
            errors[key] = int(match.group(1))
    
    errors["total_errors"] = sum(errors.values())
    errors["has_errors"] = errors["total_errors"] > 0
    
    return errors


def validate_reachability_result(ping_result: dict, expected_success: bool = True) -> dict:
    """
    Validate ping results against expectations.
    
    Args:
        ping_result: Parsed ping result dictionary
        expected_success: Whether ping should succeed
        
    Returns:
        Validation result dictionary
    """
    actual_success = ping_result.get("success", False)
    passed = actual_success == expected_success
    
    return {
        "passed": passed,
        "expected_success": expected_success,
        "actual_success": actual_success,
        "packet_loss": ping_result.get("packet_loss_percent", 100),
        "message": "Reachability test passed" if passed else "Reachability test failed"
    }


def sanitize_session_name(name: str) -> str:
    """
    Sanitize a string to be used as a tmux session name.
    
    Args:
        name: Input string
        
    Returns:
        Sanitized session name (alphanumeric, hyphens, underscores only)
    """
    # Replace spaces with underscores
    sanitized = name.replace(" ", "_")
    
    # Keep only alphanumeric, hyphens, and underscores
    sanitized = re.sub(r'[^a-zA-Z0-9_-]', '', sanitized)
    
    # Limit length
    sanitized = sanitized[:50]
    
    return sanitized or "cml_session"
