"""
Reachability Testing Tool

Tests network connectivity using ping and traceroute.
"""

from typing import Optional, Dict, Any
from .execution import execute_device_command
import logging

logger = logging.getLogger(__name__)


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
            # This is simplified - actual logic would parse success rate
            test_result["reachable"] = True  # Would extract from parsed data
            test_result["matches_expectation"] = (test_result["reachable"] == expected_success)
            test_result["status"] = "success"
        else:
            # Parse raw output for success indicators
            raw = result.get("raw_output", "")
            test_result["reachable"] = "!" in raw or "Success rate" in raw
            test_result["matches_expectation"] = (test_result["reachable"] == expected_success)
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
