"""Configuration management tools for retrieving and comparing device configs."""

import logging
from typing import Optional, Any
from .execution import execute_command
from .auth import require_client
from ..utils import compare_configs as compare_config_strings

logger = logging.getLogger(__name__)


async def get_device_config(
    lab_id: str,
    device_name: str,
    config_type: str = "running"
) -> dict[str, Any]:
    """
    Retrieve device configuration.
    
    Gets running or startup configuration from a device.
    
    Args:
        lab_id: CML lab ID
        device_name: Device label/name
        config_type: "running" or "startup"
        
    Returns:
        Dictionary with configuration:
        - status: "success" or "error"
        - config_type: Type of config retrieved
        - device: Device name
        - configuration: Configuration text
        - line_count: Number of lines in config
    """
    require_client()
    
    config_type = config_type.lower()
    
    if config_type not in ["running", "startup"]:
        return {
            "status": "error",
            "error": f"Invalid config_type: {config_type}. Must be 'running' or 'startup'",
            "supported_types": ["running", "startup"]
        }
    
    try:
        # Build command based on config type
        if config_type == "running":
            command = "show running-config"
        else:
            command = "show startup-config"
        
        # Execute command
        result = await execute_command(
            lab_id=lab_id,
            device_name=device_name,
            command=command,
            use_parser=False  # Config doesn't need parsing
        )
        
        if not result["success"]:
            return {
                "status": "error",
                "error": result.get("error", "Command execution failed"),
                "device": device_name,
                "config_type": config_type
            }
        
        configuration = result.get("output", "")
        
        # Clean up configuration (remove command echo, prompts, etc.)
        config_lines = configuration.split('\n')
        clean_lines = []
        
        in_config = False
        for line in config_lines:
            # Start capturing after the command line
            if "show running-config" in line or "show startup-config" in line:
                in_config = True
                continue
            
            # Stop at the prompt
            if in_config and (line.startswith("!") or line.strip() == "end"):
                clean_lines.append(line)
            elif in_config and not any(c in line for c in ["#", ">"]):
                clean_lines.append(line)
        
        clean_config = '\n'.join(clean_lines)
        
        return {
            "status": "success",
            "device": device_name,
            "config_type": config_type,
            "configuration": clean_config,
            "line_count": len(clean_lines),
            "command": command
        }
        
    except Exception as e:
        logger.error(f"Failed to get device config: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "device": device_name,
            "config_type": config_type
        }


async def compare_configs(
    config1: str,
    config2: str,
    ignore_whitespace: bool = True,
    context_lines: int = 3,
    label1: str = "config1",
    label2: str = "config2"
) -> dict[str, Any]:
    """
    Compare two device configurations.
    
    Returns a unified diff showing additions, deletions, and changes.
    
    Args:
        config1: First configuration text
        config2: Second configuration text
        ignore_whitespace: If True, ignore whitespace differences
        context_lines: Number of context lines to show around changes
        label1: Label for first config
        label2: Label for second config
        
    Returns:
        Dictionary with comparison results:
        - status: "success"
        - identical: Whether configs are identical
        - additions: Number of added lines
        - deletions: Number of deleted lines
        - total_changes: Total number of changes
        - diff: Unified diff text
        - summary: Human-readable summary
    """
    try:
        # Use utility function to compare
        comparison = compare_config_strings(
            config1,
            config2,
            ignore_whitespace=ignore_whitespace,
            context_lines=context_lines
        )
        
        # Update diff with custom labels
        if comparison["diff"]:
            diff_lines = comparison["diff"].split('\n')
            if len(diff_lines) >= 2:
                diff_lines[0] = diff_lines[0].replace('config1', label1)
                diff_lines[1] = diff_lines[1].replace('config2', label2)
                comparison["diff"] = '\n'.join(diff_lines)
        
        # Add status and summary
        result = {
            "status": "success",
            **comparison
        }
        
        if comparison["identical"]:
            result["summary"] = f"Configurations are identical"
        else:
            result["summary"] = (
                f"Found {comparison['total_changes']} change(s): "
                f"{comparison['additions']} addition(s), "
                f"{comparison['deletions']} deletion(s)"
            )
        
        return result
        
    except Exception as e:
        logger.error(f"Config comparison failed: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e)
        }


async def compare_device_configs(
    lab_id: str,
    device_name: str,
    compare_type: str = "running_vs_startup",
    ignore_whitespace: bool = True,
    context_lines: int = 3
) -> dict[str, Any]:
    """
    Compare configurations on a device.
    
    Can compare running vs startup configs on the same device.
    
    Args:
        lab_id: CML lab ID
        device_name: Device label/name
        compare_type: Type of comparison:
            - "running_vs_startup": Compare running-config to startup-config
        ignore_whitespace: If True, ignore whitespace differences
        context_lines: Number of context lines around changes
        
    Returns:
        Dictionary with comparison results
    """
    require_client()
    
    if compare_type != "running_vs_startup":
        return {
            "status": "error",
            "error": f"Unsupported compare_type: {compare_type}",
            "supported_types": ["running_vs_startup"]
        }
    
    try:
        # Get running config
        running_result = await get_device_config(
            lab_id=lab_id,
            device_name=device_name,
            config_type="running"
        )
        
        if running_result["status"] != "success":
            return running_result
        
        # Get startup config
        startup_result = await get_device_config(
            lab_id=lab_id,
            device_name=device_name,
            config_type="startup"
        )
        
        if startup_result["status"] != "success":
            return startup_result
        
        # Compare configs
        comparison = await compare_configs(
            config1=running_result["configuration"],
            config2=startup_result["configuration"],
            ignore_whitespace=ignore_whitespace,
            context_lines=context_lines,
            label1="running-config",
            label2="startup-config"
        )
        
        # Add device context
        comparison["device"] = device_name
        comparison["compare_type"] = compare_type
        
        return comparison
        
    except Exception as e:
        logger.error(f"Device config comparison failed: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "device": device_name
        }


async def backup_device_config(
    lab_id: str,
    device_name: str,
    config_type: str = "running",
    backup_path: Optional[str] = None
) -> dict[str, Any]:
    """
    Backup device configuration to a file.
    
    Args:
        lab_id: CML lab ID
        device_name: Device label/name
        config_type: "running" or "startup"
        backup_path: Path to save backup (None = return in response only)
        
    Returns:
        Dictionary with backup status and configuration
    """
    require_client()
    
    try:
        # Get configuration
        result = await get_device_config(
            lab_id=lab_id,
            device_name=device_name,
            config_type=config_type
        )
        
        if result["status"] != "success":
            return result
        
        # Optionally save to file
        if backup_path:
            try:
                with open(backup_path, 'w') as f:
                    f.write(result["configuration"])
                result["backup_path"] = backup_path
                result["summary"] = f"Configuration backed up to {backup_path}"
            except Exception as e:
                logger.error(f"Failed to write backup file: {e}")
                result["warning"] = f"Could not write to {backup_path}: {str(e)}"
        else:
            result["summary"] = "Configuration retrieved (not saved to file)"
        
        return result
        
    except Exception as e:
        logger.error(f"Config backup failed: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "device": device_name
        }
