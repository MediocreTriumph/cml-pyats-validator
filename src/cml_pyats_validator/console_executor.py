"""
Console Execution via SSH

Handles command execution on CML nodes via SSH to console server.
"""

import pexpect
import asyncio
from typing import Optional
import re
import time
import logging

logger = logging.getLogger(__name__)


async def execute_via_console(
    cml_host: str,
    cml_user: str,
    cml_pass: str,
    node_uuid: str,
    command: str,
    device_user: Optional[str] = None,
    device_pass: Optional[str] = None,
    device_enable_pass: Optional[str] = None,
    device_prompt: str = r"[#>$]",
    timeout: int = 30
) -> str:
    """Execute command via SSH to CML console server, then to node
    
    Args:
        cml_host: CML server hostname/IP
        cml_user: CML SSH username
        cml_pass: CML SSH password
        node_uuid: Node UUID (or console_key) to connect to
        command: Command to execute on device
        device_user: Device username (if authentication required)
        device_pass: Device password (if authentication required)
        device_enable_pass: Device enable password (for Cisco devices)
        device_prompt: Expected device prompt pattern
        timeout: Command timeout in seconds
    
    Returns:
        Command output as string
    
    Raises:
        TimeoutError: Command execution timed out
        ConnectionError: SSH connection failed
        RuntimeError: Other execution errors
    """
    
    def _ssh_console_execute():
        """Internal sync function for pexpect execution"""
        # SSH to CML console server
        child = pexpect.spawn(
            f"ssh -o StrictHostKeyChecking=no {cml_user}@{cml_host}",
            timeout=timeout,
            encoding='utf-8'
        )
        
        try:
            # Handle SSH authentication to console server
            i = child.expect([
                "password:",
                r"consoles>",  # Already authenticated
                pexpect.TIMEOUT
            ], timeout=10)
            
            if i == 0:  # Password prompt
                child.sendline(cml_pass)
                child.expect(r"consoles>", timeout=10)
            # If i == 1, already at consoles> prompt
            
            logger.info(f"Connected to CML console server, connecting to node {node_uuid}")
            
            # Connect to node console via UUID/console_key
            child.sendline(f"connect {node_uuid}")
            
            # Wait for connection confirmation
            child.expect(r"Connected to CML terminalserver", timeout=5)
            
            logger.info("Connected to device console, waiting for prompt")
            
            # Wait longer for device to be ready (banners, boot messages, etc.)
            time.sleep(3)
            
            # Send multiple newlines to trigger prompt
            child.sendline("")
            time.sleep(0.5)
            child.sendline("")
            
            # Try to detect what state we're in with a longer timeout
            i = child.expect([
                r"[Uu]sername:",
                r"[Ll]ogin:",
                r"[\w\-]+[>#]",  # More flexible prompt pattern
                pexpect.TIMEOUT
            ], timeout=15)
            
            if i == 3:  # Timeout - device might still be booting
                logger.warning("Timeout waiting for initial prompt, sending more newlines")
                child.sendline("")
                time.sleep(1)
                child.sendline("")
                # Try one more time with original prompt pattern
                child.expect(device_prompt, timeout=10)
            elif i in [0, 1]:  # Username/Login prompt
                if not device_user:
                    raise ValueError(
                        "Device requires authentication but no credentials provided"
                    )
                
                logger.info("Device requires authentication, logging in")
                
                # Send username
                child.sendline(device_user)
                
                # Wait for password prompt
                child.expect(r"[Pp]assword:", timeout=5)
                child.sendline(device_pass)
                
                # Wait for prompt after login
                child.expect(device_prompt, timeout=10)
            # If i == 2, we got a prompt, continue
            
            logger.info("Device prompt detected")
            
            # If Cisco device and we have enable password, enter enable mode
            if device_enable_pass:
                # Check current prompt to see if we're in user mode
                child.sendline("")
                i = child.expect([r">", r"#"], timeout=5)
                
                if i == 0:  # User mode (>)
                    logger.info("Entering enable mode")
                    child.sendline("enable")
                    child.expect(r"[Pp]assword:", timeout=5)
                    child.sendline(device_enable_pass)
                    
                    # Wait for privileged prompt
                    child.expect(r"#", timeout=5)
            
            # Clear any buffered output
            child.sendline("")
            child.expect(device_prompt, timeout=5)
            
            logger.info(f"Executing command: {command}")
            
            # Send actual command
            child.sendline(command)
            
            # Wait for command to complete (prompt returns)
            child.expect(device_prompt, timeout=timeout)
            
            # Extract output (everything between command and next prompt)
            output = child.before
            
            logger.info("Command executed successfully, disconnecting")
            
            # Exit node console with Ctrl+]
            child.sendcontrol(']')
            
            # Wait for disconnection message and CML console prompt
            child.expect(r"consoles>", timeout=5)
            
            # Exit SSH
            child.sendline("exit")
            child.close()
            
            # Clean up output
            # Remove command echo (first line)
            lines = output.split('\n')
            if lines and command in lines[0]:
                output = '\n'.join(lines[1:])
            
            # Remove ANSI escape sequences
            ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
            output = ansi_escape.sub('', output)
            
            # Remove extra whitespace
            output = '\n'.join(line.rstrip() for line in output.split('\n'))
            
            return output.strip()
            
        except pexpect.TIMEOUT as e:
            # Log what we got before timeout
            logger.error(f"Timeout. Buffer content: {child.buffer if hasattr(child, 'buffer') else 'N/A'}")
            logger.error(f"Before content: {child.before if hasattr(child, 'before') else 'N/A'}")
            child.close(force=True)
            raise TimeoutError(f"Command timed out after {timeout}s: {str(e)}")
        except pexpect.EOF as e:
            logger.error("SSH connection closed unexpectedly")
            raise ConnectionError(f"SSH connection closed unexpectedly: {str(e)}")
        except Exception as e:
            child.close(force=True)
            logger.error(f"Console execution failed: {e}")
            raise RuntimeError(f"Console execution failed: {str(e)}")
    
    # Run in executor to avoid blocking
    loop = asyncio.get_event_loop()
    output = await loop.run_in_executor(None, _ssh_console_execute)
    return output
