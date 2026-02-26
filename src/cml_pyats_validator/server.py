"""
CML PyATS Validator MCP Server

FastMCP server that provides network device validation tools for CML labs.
Uses SSH console access for command execution and PyATS parsers for output analysis.
"""

from fastmcp import FastMCP
from typing import Optional, Dict, Any, List
import logging

# Import all tools
from .tools import (
    initialize_cml_client,
    execute_device_command,
    validate_routing_protocols,
    validate_device_interfaces,
    test_network_reachability,
    get_configuration,
    compare_configurations,
    run_full_validation,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("cml-pyats-validator")


@mcp.tool()
async def initialize_cml_client_tool(
    cml_url: str,
    username: str,
    password: str,
    verify_ssl: bool = True
) -> dict:
    """Initialize connection to CML server
    
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
    return await initialize_cml_client(cml_url, username, password, verify_ssl)


@mcp.tool()
async def execute_command(
    lab_id: str,
    device_name: str,
    command: str,
    device_credentials: Optional[Dict[str, str]] = None,
    use_parser: bool = True,
    device_prompt: Optional[str] = None
) -> Dict[str, Any]:
    """Execute command on a network device
    
    Connects to device via SSH console, executes command, and optionally
    parses output using PyATS/Genie parsers (Cisco devices only).
    
    Args:
        lab_id: CML lab ID
        device_name: Device label/name in the lab
        command: Command to execute
        device_credentials: Optional device authentication:
            {"username": "cisco", "password": "cisco", "enable_password": "cisco"}
        use_parser: Attempt to parse output with Genie (default: True)
        device_prompt: Expected device prompt pattern (default: auto-detect)
    
    Returns:
        Command execution results with parsed or raw output
    """
    return await execute_device_command(
        lab_id, device_name, command, device_credentials, use_parser, device_prompt
    )


@mcp.tool()
async def validate_protocols(
    lab_id: str,
    device_name: str,
    protocol: str,
    validation_type: str = "neighbors",
    expected_state: Optional[Dict[str, Any]] = None,
    device_credentials: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """Validate routing or L2 protocol operation
    
    Checks protocol status using PyATS parsers to provide structured validation.
    Supported protocols: OSPF, BGP, EIGRP
    
    Args:
        lab_id: CML lab ID
        device_name: Device label/name
        protocol: Protocol to validate (ospf, bgp, eigrp)
        validation_type: Type of check (neighbors, routes, database)
        expected_state: Optional dict of expected values
        device_credentials: Device authentication credentials
    
    Returns:
        Validation results with pass/fail status and details
    """
    return await validate_routing_protocols(
        lab_id, device_name, protocol, validation_type, expected_state, device_credentials
    )


@mcp.tool()
async def validate_interfaces(
    lab_id: str,
    device_name: str,
    interface: Optional[str] = None,
    check_errors: bool = True,
    check_status: bool = True,
    device_credentials: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """Validate interface status and health
    
    Checks interface operational status, errors, CRC errors, and other
    health metrics. Can check a specific interface or all interfaces.
    
    Args:
        lab_id: CML lab ID
        device_name: Device label/name
        interface: Specific interface (None = all interfaces)
        check_errors: Check for interface errors
        check_status: Check operational status
        device_credentials: Device authentication credentials
    
    Returns:
        Interface validation results with any issues found
    """
    return await validate_device_interfaces(
        lab_id, device_name, interface, check_errors, check_status, device_credentials
    )


@mcp.tool()
async def test_reachability(
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
    Useful for verifying routing and end-to-end connectivity.
    
    Args:
        lab_id: CML lab ID
        source_device: Source device label
        destination: Destination IP address or hostname
        test_type: "ping" or "traceroute"
        count: Number of packets (ping only)
        expected_success: Whether connection should work
        device_credentials: Device authentication credentials
    
    Returns:
        Reachability test results with success/failure status
    """
    return await test_network_reachability(
        lab_id, source_device, destination, test_type, count, expected_success, device_credentials
    )


@mcp.tool()
async def get_device_configuration(
    lab_id: str,
    device_name: str,
    config_type: str = "running",
    device_credentials: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """Retrieve device configuration
    
    Gets the running or startup configuration from a device.
    Useful for backup, review, or comparison purposes.
    
    Args:
        lab_id: CML lab ID
        device_name: Device label/name
        config_type: "running" or "startup"
        device_credentials: Device authentication credentials
    
    Returns:
        Device configuration as text
    """
    return await get_configuration(lab_id, device_name, config_type, device_credentials)


@mcp.tool()
async def compare_device_configurations(
    config1: str,
    config2: str,
    ignore_whitespace: bool = True,
    context_lines: int = 3
) -> Dict[str, Any]:
    """Compare two device configurations
    
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
    return await compare_configurations(config1, config2, ignore_whitespace, context_lines)


@mcp.tool()
async def run_testbed_validation(
    lab_id: str,
    validation_checks: Optional[List[str]] = None,
    device_list: Optional[List[str]] = None,
    device_credentials: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """Run comprehensive testbed validation
    
    Performs a complete health check across all devices in the lab,
    including interface status, protocol validation, and error checking.
    
    Default checks: interfaces, protocols, errors
    
    Args:
        lab_id: CML lab ID
        validation_checks: List of checks to run (None = all)
        device_list: Specific devices to test (None = all)
        device_credentials: Device authentication credentials
    
    Returns:
        Comprehensive validation results with overall pass/fail status
    """
    return await run_full_validation(lab_id, validation_checks, device_list, device_credentials)


def main():
    """Main entry point for the MCP server"""
    import argparse
    import os

    parser = argparse.ArgumentParser(description="CML PyATS Validator MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http"],
        default=os.environ.get("TRANSPORT", "stdio"),
        help="MCP transport mode (default: stdio, env: TRANSPORT)",
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("HOST", "0.0.0.0"),
        help="HTTP bind address (default: 0.0.0.0, env: HOST)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("PORT", "9001")),
        help="HTTP port (default: 9001, env: PORT)",
    )
    args = parser.parse_args()

    if args.transport == "streamable-http":
        logger.info(f"Starting CML PyATS Validator in HTTP mode on {args.host}:{args.port}")
        mcp.run(transport="streamable-http", host=args.host, port=args.port)
    else:
        logger.info("Starting CML PyATS Validator in stdio mode")
        mcp.run()


if __name__ == "__main__":
    main()
