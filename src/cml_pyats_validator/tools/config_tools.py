"""
Configuration Management Tools

Handles device configuration retrieval and comparison.
"""

from typing import Dict, Any, Optional
from .execution import execute_device_command
import difflib
import logging

logger = logging.getLogger(__name__)


async def get_configuration(
    lab_id: str,
    device_name: str,
    config_type: str = "running",
    device_credentials: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """Retrieve device configuration
    
    Gets the running or startup configuration from a device.
    
    Args:
        lab_id: CML lab ID
        device_name: Device label/name
        config_type: "running" or "startup"
        device_credentials: Device authentication credentials
    
    Returns:
        Device configuration as text
    
    Example:
        result = await get_configuration(
            lab_id="abc123",
            device_name="R1",
            config_type="running"
        )
    """
    try:
        # Build command based on config type
        if config_type == "running":
            command = "show running-config"
        elif config_type == "startup":
            command = "show startup-config"
        else:
            return {
                "status": "error",
                "error": f"Invalid config_type: {config_type}. Use 'running' or 'startup'"
            }
        
        # Execute command (no parser needed for config)
        result = await execute_device_command(
            lab_id=lab_id,
            device_name=device_name,
            command=command,
            device_credentials=device_credentials,
            use_parser=False
        )
        
        if "error" in result:
            return result
        
        return {
            "device": device_name,
            "config_type": config_type,
            "configuration": result.get("raw_output"),
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Configuration retrieval failed: {e}")
        return {
            "status": "error",
            "device": device_name,
            "error": str(e)
        }


async def compare_configurations(
    config1: str,
    config2: str,
    ignore_whitespace: bool = True,
    context_lines: int = 3
) -> Dict[str, Any]:
    """Compare two device configurations
    
    Generates a unified diff showing differences between configurations.
    
    Args:
        config1: First configuration text
        config2: Second configuration text
        ignore_whitespace: Ignore whitespace differences
        context_lines: Lines of context around changes
    
    Returns:
        Comparison results with unified diff
    
    Example:
        result = await compare_configurations(
            config1=old_config,
            config2=new_config,
            ignore_whitespace=True
        )
    """
    try:
        # Split into lines
        lines1 = config1.splitlines(keepends=True)
        lines2 = config2.splitlines(keepends=True)
        
        # Generate unified diff
        diff = list(difflib.unified_diff(
            lines1,
            lines2,
            fromfile='config1',
            tofile='config2',
            lineterm='',
            n=context_lines
        ))
        
        # Count changes
        additions = sum(1 for line in diff if line.startswith('+') and not line.startswith('+++'))
        deletions = sum(1 for line in diff if line.startswith('-') and not line.startswith('---'))
        
        return {
            "status": "success",
            "identical": len(diff) == 0,
            "additions": additions,
            "deletions": deletions,
            "total_changes": additions + deletions,
            "diff": ''.join(diff)
        }
        
    except Exception as e:
        logger.error(f"Configuration comparison failed: {e}")
        return {
            "status": "error",
            "error": str(e)
        }
