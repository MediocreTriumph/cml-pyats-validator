"""
Command Execution Tool

Executes commands on devices via SSH console access and optionally parses with PyATS.
"""

from typing import Optional, Dict, Any
from .auth import get_cml_client
from ..console_executor import execute_via_console
from ..pyats_helper import get_genie_os, is_cisco_device, parse_output
import logging

logger = logging.getLogger(__name__)


async def execute_device_command(
    lab_id: str,
    device_name: str,
    command: str,
    device_credentials: Optional[Dict[str, str]] = None,
    use_parser: bool = True,
    device_prompt: Optional[str] = None
) -> Dict[str, Any]:
    """Execute command on a network device via console access
    
    Connects to device via SSH to CML console server, executes command,
    and optionally parses output using PyATS/Genie parsers.
    
    Args:
        lab_id: CML lab ID
        device_name: Device label/name in the lab
        command: Command to execute (e.g., 'show ip interface brief')
        device_credentials: Optional device authentication:
            {
                "username": "cisco",
                "password": "cisco",
                "enable_password": "cisco"  # For Cisco devices
            }
        use_parser: Attempt to parse output with PyATS (default: True)
        device_prompt: Expected device prompt pattern (default: auto-detect)
    
    Returns:
        Dictionary containing:
            - device: Device name
            - command: Command executed
            - raw_output: Raw command output
            - parsed_output: Parsed data (if use_parser=True and available)
            - parser_used: Whether parser was used
            - parser_error: Error message if parsing failed
    
    Example:
        result = await execute_device_command(
            lab_id="abc123",
            device_name="R1",
            command="show ip interface brief",
            device_credentials={"username": "cisco", "password": "cisco"},
            use_parser=True
        )
    """
    try:
        client = get_cml_client()
        
        # Get node information from CML API
        node = await client.find_node_by_label(lab_id, device_name)
        if not node:
            return {
                "status": "error",
                "error": f"Device '{device_name}' not found in lab '{lab_id}'"
            }
        
        node_id = node['id']
        device_type = node.get('node_definition', 'unknown')
        
        logger.info(f"Found device {device_name} with node ID {node_id}")
        
        # Get console key via dedicated API endpoint
        # Console keys are NOT in the topology or node details - they require a separate call
        # API: GET /api/v0/labs/{lab_id}/nodes/{node_id}/keys/console?line=0
        try:
            console_key = await client.get_console_key(lab_id, node_id, line=0)
        except Exception as e:
            logger.error(f"Failed to get console key for {device_name}: {e}")
            return {
                "status": "error",
                "error": f"Failed to get console key for device '{device_name}': {e}"
            }
        
        if not console_key:
            return {
                "status": "error",
                "error": f"No console key returned for device '{device_name}'"
            }
        
        logger.info(f"Using console key {console_key} for {device_name}")
        logger.info(f"Executing '{command}' on {device_name} ({device_type})")
        
        # Extract CML hostname from URL
        cml_host = client.url.replace("https://", "").replace("http://", "").split(":")[0]
        
        # Auto-detect prompt pattern if not provided
        if not device_prompt:
            cisco_types = ['iosv', 'csr1000v', 'iosvl2', 'nxosv', 'iosxrv', 'asav']
            if any(dt in device_type for dt in cisco_types):
                device_prompt = r"[#>]"
            else:
                device_prompt = r"[#>$]"
        
        # Extract device credentials
        device_user = None
        device_pass = None
        device_enable_pass = None
        if device_credentials:
            device_user = device_credentials.get("username")
            device_pass = device_credentials.get("password")
            device_enable_pass = device_credentials.get("enable_password")
        
        # Execute command via SSH console using console_key
        raw_output = await execute_via_console(
            cml_host=cml_host,
            cml_user=client.username,
            cml_pass=client.password,
            node_uuid=console_key,  # This is the console_key, not node UUID
            command=command,
            device_user=device_user,
            device_pass=device_pass,
            device_enable_pass=device_enable_pass,
            device_prompt=device_prompt,
            timeout=30
        )
        
        result = {
            "device": device_name,
            "command": command,
            "raw_output": raw_output,
            "node_id": node_id,
            "console_key": console_key,
            "device_type": device_type
        }
        
        # Parse output if requested
        if use_parser and is_cisco_device(device_type):
            try:
                genie_os = get_genie_os(device_type)
                parsed = parse_output(command, raw_output, genie_os)
                
                result["parsed_output"] = parsed
                result["parser_used"] = True
                
                logger.info(f"Successfully parsed output for '{command}'")
                
            except Exception as e:
                result["parser_error"] = str(e)
                result["parser_used"] = False
                logger.warning(f"Parsing failed for '{command}': {e}")
        else:
            result["parser_used"] = False
            if use_parser and not is_cisco_device(device_type):
                result["parser_error"] = (
                    f"No PyATS parser available for device type: {device_type}"
                )
        
        return result
        
    except Exception as e:
        logger.error(f"Command execution failed: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {
            "status": "error",
            "device": device_name,
            "command": command,
            "error": str(e)
        }
