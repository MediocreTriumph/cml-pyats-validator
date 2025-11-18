"""Main FastMCP server for CML PyATS Validator."""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv
from fastmcp import FastMCP

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastMCP server
mcp = FastMCP("CML PyATS Validator")

# Import tools
from .tools import (
    initialize_client,
    execute_command,
    validate_protocols,
    validate_interfaces,
    validate_reachability,
    get_device_config,
    compare_configs,
    run_testbed_validation
)


@mcp.tool()
async def initialize_cml_client(
    cml_url: str,
    username: str,
    password: str,
    verify_ssl: bool = True
) -> dict:
    """
    Initialize connection to CML server.
    
    Must be called before using other validation tools. Authenticates with
    CML and stores credentials for subsequent operations.
    
    Args:
        cml_url: CML server URL (e.g., https://cml-server)
        username: CML username
        password: CML password
        verify_ssl: Verify SSL certificates (set to False for self-signed certs)
        
    Returns:
        Authentication status and server information
    """
    return await initialize_client(cml_url, username, password, verify_ssl)


@mcp.tool()
async def execute_device_command(
    lab_id: str,
    device_name: str,
    command: str,
    use_parser: bool = True
) -> dict:
    """
    Execute command on a network device.
    
    Sends a command to a device via console access and optionally parses
    the output using PyATS/Genie parsers (Cisco devices only).
    
    For Cisco devices with available parsers, returns structured data.
    For other devices or commands without parsers, returns raw text output.
    
    Args:
        lab_id: CML lab ID
        device_name: Device label/name in the lab
        command: Command to execute
        use_parser: Attempt to parse output with Genie (default: True)
        
    Returns:
        Command execution results with parsed or raw output
    """
    return await execute_command(lab_id, device_name, command, use_parser)


@mcp.tool()
async def validate_routing_protocols(
    lab_id: str,
    device_name: str,
    protocol: str,
    validation_type: str = "neighbors",
    expected_state: dict | None = None
) -> dict:
    """
    Validate routing or L2 protocol operation.
    
    Checks protocol status using PyATS parsers to provide structured validation.
    Supported protocols: OSPF, BGP, EIGRP, RIP, STP, VTP, HSRP, VRRP
    
    Args:
        lab_id: CML lab ID
        device_name: Device label/name
        protocol: Protocol to validate (ospf, bgp, eigrp, stp, etc.)
        validation_type: Type of check (neighbors, routes, state, etc.)
        expected_state: Optional dict of expected values
        
    Returns:
        Validation results with pass/fail status and details
    """
    return await validate_protocols(
        lab_id, device_name, protocol, validation_type, expected_state
    )


@mcp.tool()
async def validate_device_interfaces(
    lab_id: str,
    device_name: str,
    interface: str | None = None,
    check_errors: bool = True,
    check_status: bool = True
) -> dict:
    """
    Validate interface status and health.
    
    Checks interface operational status, errors, CRC errors, and other
    health metrics. Can check a specific interface or all interfaces.
    
    Args:
        lab_id: CML lab ID
        device_name: Device label/name
        interface: Specific interface (None = all interfaces)
        check_errors: Check for interface errors
        check_status: Check operational status
        
    Returns:
        Interface validation results with any issues found
    """
    return await validate_interfaces(
        lab_id, device_name, interface, check_errors, check_status
    )


@mcp.tool()
async def test_network_reachability(
    lab_id: str,
    source_device: str,
    destination: str,
    test_type: str = "ping",
    count: int = 5,
    expected_success: bool = True
) -> dict:
    """
    Test network reachability using ping or traceroute.
    
    Executes connectivity tests and validates against expected results.
    Useful for verifying routing and end-to-end connectivity.
    
    Args:
        lab_id: CML lab ID
        source_device: Source device label
        destination: Destination IP address or hostname
        test_type: "ping" or "traceroute"
        count: Number of packets (ping only)
        expected_success: Whether connection should work
        
    Returns:
        Reachability test results with success/failure status
    """
    return await validate_reachability(
        lab_id, source_device, destination, test_type, count, expected_success
    )


@mcp.tool()
async def get_configuration(
    lab_id: str,
    device_name: str,
    config_type: str = "running"
) -> dict:
    """
    Retrieve device configuration.
    
    Gets the running or startup configuration from a device.
    Useful for backup, review, or comparison purposes.
    
    Args:
        lab_id: CML lab ID
        device_name: Device label/name
        config_type: "running" or "startup"
        
    Returns:
        Device configuration as text
    """
    return await get_device_config(lab_id, device_name, config_type)


@mcp.tool()
async def compare_configurations(
    config1: str,
    config2: str,
    ignore_whitespace: bool = True,
    context_lines: int = 3
) -> dict:
    """
    Compare two device configurations.
    
    Generates a unified diff showing additions, deletions, and changes
    between two configuration texts. Useful for change validation.
    
    Args:
        config1: First configuration
        config2: Second configuration
        ignore_whitespace: Ignore whitespace differences
        context_lines: Lines of context around changes
        
    Returns:
        Comparison results with unified diff
    """
    return await compare_configs(
        config1, config2, ignore_whitespace, context_lines
    )


@mcp.tool()
async def run_full_validation(
    lab_id: str,
    validation_checks: list[str] | None = None,
    device_list: list[str] | None = None
) -> dict:
    """
    Run comprehensive testbed validation.
    
    Performs a complete health check across all devices in the lab,
    including interface status, protocol validation, error checking,
    and connectivity tests.
    
    Default checks if none specified:
    - interfaces: Verify interfaces are up
    - protocols: Check routing protocol neighbors
    - connectivity: Test reachability
    - errors: Check for interface errors
    
    Args:
        lab_id: CML lab ID
        validation_checks: List of checks to run (None = all)
        device_list: Specific devices to test (None = all)
        
    Returns:
        Comprehensive validation results with overall pass/fail status
    """
    return await run_testbed_validation(lab_id, validation_checks, device_list)


def main():
    """Entry point for running the MCP server."""
    logger.info("Starting CML PyATS Validator MCP Server")
    
    # Check for required environment variables
    required_vars = ["CML_URL", "CML_USERNAME", "CML_PASSWORD"]
    missing = [var for var in required_vars if not os.getenv(var)]
    
    if missing:
        logger.warning(
            f"Missing environment variables: {', '.join(missing)}. "
            "Client will need to call initialize_client with credentials."
        )
    
    # Run the server
    mcp.run()


if __name__ == "__main__":
    main()
