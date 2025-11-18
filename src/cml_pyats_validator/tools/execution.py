"""Command execution tool using tmux console access and PyATS parsers."""

import logging
from typing import Optional, Any
from .auth import require_client
from ..pyats_helper import PyATSHelper
from ..utils import sanitize_session_name

logger = logging.getLogger(__name__)

# Note: This assumes tmux-mcp tools are available in the MCP environment
# The actual tmux tool calls would be made through the MCP framework


async def execute_command(
    lab_id: str,
    device_name: str,
    command: str,
    use_parser: bool = True
) -> dict[str, Any]:
    """
    Execute command on a device via console and optionally parse output.
    
    This tool uses tmux to establish console sessions with devices and
    applies PyATS/Genie parsers when available (Cisco devices only).
    
    Args:
        lab_id: CML lab ID
        device_name: Device label/name in the lab
        command: Command to execute
        use_parser: If True, attempt to parse output with Genie (Cisco only)
        
    Returns:
        Dictionary containing:
        - success (bool): Whether command executed successfully
        - command (str): The command that was executed
        - output (str): Raw command output
        - parsed (bool): Whether output was parsed
        - data (dict|str): Parsed data if available, raw output otherwise
        - parser_used (str|None): Name of parser used, if any
        - device (str): Device name
        - device_os (str|None): Detected device OS type
    """
    client = require_client()
    
    try:
        # Get lab and node information
        lab = await client.get_lab(lab_id)
        node = await client.get_node_by_label(lab_id, device_name)
        
        if not node:
            return {
                "success": False,
                "error": f"Device '{device_name}' not found in lab",
                "device": device_name
            }
        
        node_definition = node.get("data", {}).get("node_definition", "")
        node_id = node.get("id")
        
        # Determine device OS type
        device_os = PyATSHelper.get_device_os(node_definition)
        is_cisco = PyATSHelper.is_cisco_device(node_definition)
        
        # TODO: Execute command via tmux console
        # This is a placeholder - actual implementation would use tmux MCP tools:
        # 1. Create/attach to tmux session for this device
        # 2. Send command via tmux send-keys
        # 3. Capture output via tmux capture-pane
        
        # For now, return a structure showing what would happen
        result = {
            "success": True,
            "command": command,
            "device": device_name,
            "device_os": device_os,
            "node_definition": node_definition,
            "lab_id": lab_id,
            "node_id": node_id,
            "note": "Command execution requires tmux MCP integration"
        }
        
        # Placeholder for actual output
        raw_output = ""
        
        # If we have output and should parse it
        if raw_output and use_parser and is_cisco:
            normalized_cmd = PyATSHelper.normalize_command(command)
            parse_result = PyATSHelper.parse_output(
                normalized_cmd,
                raw_output,
                device_os,
                device_name
            )
            
            result.update({
                "output": raw_output,
                "parsed": parse_result["parsed"],
                "data": parse_result["data"],
                "parser_used": parse_result.get("parser_used"),
                "parser_note": parse_result.get("note")
            })
        else:
            result.update({
                "output": raw_output,
                "parsed": False,
                "data": raw_output,
                "parser_used": None
            })
            
            if not is_cisco:
                result["note"] = f"Device type '{node_definition}' is not Cisco - returning raw output"
        
        return result
        
    except Exception as e:
        logger.error(f"Error executing command on {device_name}: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "device": device_name,
            "command": command
        }


async def _execute_via_tmux(
    lab_id: str,
    device_name: str,
    command: str
) -> str:
    """
    Execute command via tmux console session.
    
    This is a helper function that would integrate with tmux MCP tools.
    
    Implementation steps:
    1. Create session name from lab_id + device_name
    2. Check if tmux session exists, create if needed
    3. Get console connection details from CML API
    4. Establish console connection in tmux session
    5. Send command
    6. Capture output
    7. Return output text
    
    Args:
        lab_id: CML lab ID
        device_name: Device name
        command: Command to execute
        
    Returns:
        Raw command output as string
    """
    # This would use the tmux MCP tools available in the environment
    # Example flow:
    # - tmux:tmux_create_session(session_name)
    # - tmux:tmux_send_keys(session_name, command)
    # - output = tmux:tmux_capture_pane(session_name)
    
    session_name = sanitize_session_name(f"cml_{lab_id}_{device_name}")
    
    # Placeholder for actual tmux integration
    raise NotImplementedError(
        "Tmux console integration is not yet implemented. "
        "This requires tmux MCP tools to be available."
    )
