"""
Reachability Testing Tool

Tests network connectivity using ping and traceroute.
"""

from typing import Optional, Dict, Any
from .execution import execute_device_command
import logging

logger = logging.getLogger(__name__)


def _parse_ping_raw_output(raw_output: str) -> bool:
    """Parse raw ping output to determine success

    Looks for:
    - IOS/ASA: "Success rate is X percent (N/M)"
    - "!" characters indicating successful replies
    - ".....!!!" pattern where dots are timeouts

    Returns:
        True if any packets succeeded, False otherwise
    """
    import re

    # Check for explicit "Success rate is X percent" line
    # Example: "Success rate is 100 percent (5/5)"
    # Example: "Success rate is 0 percent (0/5)"
    success_match = re.search(r'Success rate is (\d+) percent', raw_output)
    if success_match:
        rate = int(success_match.group(1))
        return rate > 0

    # Check for "!" characters (successful pings)
    # But make sure there are actual "!" and not just "...." (timeouts)
    if "!" in raw_output:
        # Count exclamation marks vs dots in the reply pattern
        # Look for patterns like "!!!!!" or "..!.." etc.
        # If we have at least one "!", consider it reachable
        return True

    # If we see only dots "....." that means 100% packet loss
    if "....." in raw_output or "....." in raw_output:
        return False

    # No clear indicators - default to False
    return False


async def test_network_reachability(
    lab_id: str,
    source_device: str,
    destination: str,
    test_type: str = "ping",
    count: int = 5,
    expected_success: bool = True,
    device_credentials: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """Test network reachability using ping or traceroute
    
    Executes connectivity tests and validates against expected results.
    
    Args:
        lab_id: CML lab ID
        source_device: Source device label
        destination: Destination IP address or hostname
        test_type: "ping" or "traceroute"
        count: Number of packets for ping (default: 5)
        expected_success: Whether connection should succeed
        device_credentials: Device authentication credentials
    
    Returns:
        Reachability test results with success/failure status
    
    Example:
        result = await test_network_reachability(
            lab_id="abc123",
            source_device="R1",
            destination="10.1.1.2",
            test_type="ping",
            count=5
        )
    """
    try:
        # Build command based on test type
        if test_type == "ping":
            command = f"ping {destination} repeat {count}"
        elif test_type == "traceroute":
            command = f"traceroute {destination}"
        else:
            return {
                "status": "error",
                "error": f"Unsupported test type: {test_type}. Use 'ping' or 'traceroute'"
            }
        
        # Execute command
        result = await execute_device_command(
            lab_id=lab_id,
            device_name=source_device,
            command=command,
            device_credentials=device_credentials,
            use_parser=True
        )
        
        if "error" in result:
            return result
        
        test_result = {
            "source": source_device,
            "destination": destination,
            "test_type": test_type,
            "command": command,
            "raw_output": result.get("raw_output"),
        }
        
        if result.get("parser_used"):
            parsed = result.get("parsed_output", {})
            test_result["parsed_data"] = parsed

            # Determine success based on parsed output
            # PyATS ping parser returns statistics with success_rate_percent
            reachable = False
            if isinstance(parsed, dict):
                # Try to find success rate in parsed data
                statistics = parsed.get("statistics", {})
                if isinstance(statistics, dict):
                    success_rate = statistics.get("success_rate_percent")
                    if success_rate is not None:
                        try:
                            rate = float(success_rate)
                            reachable = rate > 0  # Any successful packet means reachable
                            test_result["success_rate"] = rate
                        except (ValueError, TypeError):
                            pass

            # Fallback to raw output parsing if parser didn't provide rate
            if "success_rate" not in test_result:
                raw = result.get("raw_output", "")
                reachable = _parse_ping_raw_output(raw)

            test_result["reachable"] = reachable
            test_result["matches_expectation"] = (reachable == expected_success)
            test_result["status"] = "success"
        else:
            # Parse raw output for success indicators
            raw = result.get("raw_output", "")
            reachable = _parse_ping_raw_output(raw)
            test_result["reachable"] = reachable
            test_result["matches_expectation"] = (reachable == expected_success)
            test_result["status"] = "success"
        
        return test_result
        
    except Exception as e:
        logger.error(f"Reachability test failed: {e}")
        return {
            "status": "error",
            "source": source_device,
            "destination": destination,
            "error": str(e)
        }
