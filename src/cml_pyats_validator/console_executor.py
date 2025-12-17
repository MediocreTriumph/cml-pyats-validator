"""
Console Execution via SSH

Handles command execution on CML nodes via SSH to console server.

FIXES APPLIED:
1. Added 0.2s delay after sendline() to let command start executing
2. Implemented retry logic for expect() to handle slow output
3. Buffer accumulation across retry attempts
4. Better timeout handling that doesn't lose partial output
"""

import pexpect
import asyncio
from typing import Optional, List
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
        child = None
        try:
            # SSH to CML console server
            logger.info(f"Connecting to CML console server at {cml_host}")
            child = pexpect.spawn(
                f"ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null {cml_user}@{cml_host}",
                timeout=timeout,
                encoding='utf-8',
                codec_errors='replace'
            )
            
            # Enable logging for debugging
            child.logfile_read = LogAdapter(logger, logging.DEBUG, "RECV")
            
            # Handle SSH authentication to console server
            i = child.expect([
                r"[Pp]assword:",
                r"consoles>",
                pexpect.TIMEOUT,
                pexpect.EOF
            ], timeout=15)
            
            if i == 0:  # Password prompt
                logger.info("Got password prompt, authenticating")
                child.sendline(cml_pass)
                child.expect(r"consoles>", timeout=10)
            elif i == 1:  # Already at consoles prompt (key auth)
                logger.info("Already at consoles> prompt")
            elif i == 2:
                raise TimeoutError("Timeout waiting for SSH password prompt or consoles>")
            elif i == 3:
                raise ConnectionError("SSH connection closed unexpectedly")
            
            logger.info(f"Connected to CML console server, connecting to node {node_uuid}")
            
            # Connect to node console via console_key
            child.sendline(f"connect {node_uuid}")
            
            # Wait for BOTH connection messages
            # First: "Connected to CML terminalserver"
            child.expect(r"Connected to CML terminalserver", timeout=10)
            logger.info("Received 'Connected to CML terminalserver'")
            
            # Second: "Escape character is '^]'." - this is critical
            child.expect(r"Escape character is", timeout=5)
            logger.info("Received escape character message, device console is now ready")
            
            # Small delay for the console to be fully ready
            time.sleep(0.5)
            
            # Clear any buffered data by reading what's available
            try:
                child.read_nonblocking(size=4096, timeout=0.5)
            except pexpect.TIMEOUT:
                pass
            
            # Send carriage return to trigger prompt (not just newline)
            # IOSv devices expect \r or \r\n
            logger.info("Sending CR to trigger device prompt")
            child.send("\r")
            time.sleep(0.3)
            child.send("\r")
            
            # Cisco IOS prompt patterns:
            # - hostname>           (user EXEC mode)
            # - hostname#           (privileged EXEC mode)
            # - hostname(config)#   (global config mode)
            # - hostname(config-if)# (interface config mode)
            # Hostname can contain letters, numbers, hyphens, underscores
            cisco_prompt = r"[\w\-\.]+(\([^\)]+\))?[>#]\s*$"
            
            # Also match simple prompts in case hostname isn't set
            simple_prompt = r"[>#]\s*$"
            
            # Combined pattern - try cisco first, fall back to simple
            combined_prompt = f"({cisco_prompt}|{simple_prompt})"
            
            # Try to detect what state we're in
            logger.info("Waiting for device prompt...")
            i = child.expect([
                r"[Uu]sername:",
                r"[Ll]ogin:",
                r"[Pp]assword:",
                cisco_prompt,
                simple_prompt,
                pexpect.TIMEOUT
            ], timeout=15)
            
            if i == 5:  # Timeout
                # Log what we have in the buffer for debugging
                logger.warning(f"Timeout waiting for prompt. Buffer contents: {repr(child.before)}")
                
                # Try a few more times with different approaches
                for attempt in range(3):
                    logger.info(f"Retry attempt {attempt + 1}: sending CR")
                    child.send("\r")
                    time.sleep(0.5)
                    
                    try:
                        j = child.expect([cisco_prompt, simple_prompt, pexpect.TIMEOUT], timeout=5)
                        if j < 2:
                            logger.info(f"Got prompt on retry {attempt + 1}")
                            break
                    except pexpect.TIMEOUT:
                        continue
                else:
                    # Last resort: check if there's anything that looks like a prompt
                    buffer = child.before if child.before else ""
                    if re.search(r'[>#]\s*$', buffer):
                        logger.info("Found prompt-like pattern in buffer, proceeding")
                    else:
                        raise TimeoutError(
                            f"Could not detect device prompt after multiple attempts. "
                            f"Buffer: {repr(buffer)}"
                        )
                        
            elif i in [0, 1]:  # Username/Login prompt
                if not device_user:
                    raise ValueError(
                        "Device requires authentication but no credentials provided"
                    )
                
                logger.info("Device requires authentication, logging in")
                child.sendline(device_user)
                child.expect(r"[Pp]assword:", timeout=5)
                child.sendline(device_pass)
                child.expect(cisco_prompt, timeout=10)
                
            elif i == 2:  # Password prompt directly (no username)
                if not device_pass:
                    raise ValueError(
                        "Device requires password but none provided"
                    )
                logger.info("Device requires password, authenticating")
                child.sendline(device_pass)
                child.expect(cisco_prompt, timeout=10)
            
            # We're now at a prompt
            current_prompt = child.after.strip() if child.after else "unknown"
            logger.info(f"Device prompt detected: '{current_prompt}'")
            
            # Determine if we're in user mode (>) or privileged mode (#)
            in_enable_mode = current_prompt.endswith('#') if current_prompt else False
            
            # If enable password provided and we're not in enable mode, enter it
            if device_enable_pass and not in_enable_mode:
                logger.info("Entering enable mode")
                child.sendline("enable")
                i = child.expect([r"[Pp]assword:", cisco_prompt], timeout=5)
                if i == 0:
                    child.sendline(device_enable_pass)
                    child.expect(r"#", timeout=5)
                    logger.info("Now in enable mode")
            
            # Clear buffer before sending command
            child.send("\r")
            child.expect([cisco_prompt, simple_prompt], timeout=5)
            
            logger.info(f"Executing command: {command}")
            
            # Send the command
            child.sendline(command)
            
            # CRITICAL FIX: Allow time for command to execute and output to buffer
            # Without this, fast consecutive commands create a race condition where
            # expect() might match the prompt before output has been generated
            time.sleep(0.2)
            
            # Wait for prompt to return (command completion)
            # Handle pagination dynamically by watching for --More-- prompts
            # This works across all platforms and modes (IOS, ASA, NX-OS, config mode, etc.)
            output_buffer = []
            max_iterations = 50  # Prevent infinite loop on very long output
            
            for iteration in range(max_iterations):
                try:
                    i = child.expect([
                        cisco_prompt, 
                        simple_prompt, 
                        r"--More--",              # IOS/IOS-XE pagination
                        r"<--- More --->",        # NX-OS pagination  
                        r"\(yes/no\)",            # Confirmation prompts
                        r"[Cc]onfirm",            # Alternative confirmation
                    ], timeout=timeout)
                    
                    # Capture output before the match
                    if child.before:
                        output_buffer.append(child.before)
                    
                    if i in [0, 1]:  # Got prompt - command completed
                        logger.info(f"Command completed successfully after {iteration + 1} iteration(s)")
                        break
                    
                    elif i in [2, 3]:  # Hit pagination prompt (--More-- or <--- More --->)
                        logger.debug(f"Pagination prompt detected (iteration {iteration + 1}), continuing...")
                        child.send(" ")  # Send space to continue pagination
                        time.sleep(0.05)  # Small delay for next page to start loading
                        continue
                    
                    elif i in [4, 5]:  # Confirmation prompt
                        logger.info("Confirmation prompt detected, sending 'yes'")
                        child.sendline("yes")
                        time.sleep(0.1)
                        continue
                    
                except pexpect.TIMEOUT:
                    # Timeout could mean:
                    # 1. Command is still executing (rare)
                    # 2. We missed a prompt pattern
                    # 3. Device is hung
                    
                    if child.before:
                        output_buffer.append(child.before)
                        logger.warning(f"Timeout on iteration {iteration + 1}, captured {len(child.before)} chars")
                    
                    # Check if we at least have some output - if so, this might be OK
                    if output_buffer:
                        logger.warning("Timeout but we have output, attempting to recover")
                        # Try sending newline to see if we can get a prompt
                        child.send("\r")
                        time.sleep(0.3)
                        try:
                            child.expect([cisco_prompt, simple_prompt], timeout=2)
                            logger.info("Recovered from timeout")
                            if child.before:
                                output_buffer.append(child.before)
                            break
                        except pexpect.TIMEOUT:
                            pass
                    
                    # Final timeout - raise it
                    logger.error(f"Command timed out after {iteration + 1} iteration(s)")
                    raise
            
            else:
                # Hit max_iterations without getting a final prompt
                logger.warning(f"Hit max iterations ({max_iterations}) without final prompt, using collected output")
                # Don't raise - we may have collected valid output
            
            # Combine all output chunks captured across retries
            output = ''.join(output_buffer)
            
            logger.info(f"Command output length: {len(output) if output else 0} chars")
            
            # Clean exit from console
            logger.info("Disconnecting from device console")
            child.sendcontrol(']')  # Ctrl+]
            
            # Wait for consoles> prompt
            try:
                child.expect(r"consoles>", timeout=5)
                child.sendline("exit")
            except pexpect.TIMEOUT:
                logger.warning("Timeout waiting for consoles> after Ctrl+], forcing close")
            
            child.close()
            
            # Clean up output
            if output:
                output = _clean_output(output, command)
            else:
                output = ""
            
            return output
            
        except pexpect.TIMEOUT as e:
            buffer_content = ""
            before_content = ""
            if child:
                try:
                    buffer_content = child.buffer if hasattr(child, 'buffer') else 'N/A'
                    before_content = child.before if hasattr(child, 'before') else 'N/A'
                except Exception:
                    pass
            logger.error(f"Timeout. Buffer: {repr(buffer_content)}")
            logger.error(f"Before: {repr(before_content)}")
            if child:
                child.close(force=True)
            raise TimeoutError(
                f"Command timed out after {timeout}s. "
                f"Buffer: {repr(buffer_content)}, Before: {repr(before_content)}"
            )
        except pexpect.EOF as e:
            logger.error("SSH connection closed unexpectedly")
            if child:
                child.close(force=True)
            raise ConnectionError(f"SSH connection closed unexpectedly: {str(e)}")
        except Exception as e:
            if child:
                child.close(force=True)
            logger.error(f"Console execution failed: {e}")
            raise RuntimeError(f"Console execution failed: {str(e)}")
    
    # Run in executor to avoid blocking
    loop = asyncio.get_event_loop()
    output = await loop.run_in_executor(None, _ssh_console_execute)
    return output


async def execute_config_commands(
    cml_host: str,
    cml_user: str,
    cml_pass: str,
    node_uuid: str,
    commands: List[str],
    device_user: Optional[str] = None,
    device_pass: Optional[str] = None,
    device_enable_pass: Optional[str] = None,
    timeout: int = 60
) -> str:
    """Execute configuration commands via SSH to CML console server
    
    Enters config mode, executes all commands, then exits config mode.
    
    Args:
        cml_host: CML server hostname/IP
        cml_user: CML SSH username
        cml_pass: CML SSH password
        node_uuid: Console key for the node
        commands: List of configuration commands to execute
        device_user: Device username (if authentication required)
        device_pass: Device password (if authentication required)
        device_enable_pass: Device enable password (for Cisco devices)
        timeout: Total timeout in seconds
    
    Returns:
        Command output as string
    
    Raises:
        TimeoutError: Command execution timed out
        ConnectionError: SSH connection failed
        RuntimeError: Other execution errors
    """
    
    def _ssh_config_execute():
        """Internal sync function for pexpect config execution"""
        child = None
        all_output = []
        
        try:
            # SSH to CML console server
            logger.info(f"Connecting to CML console server at {cml_host}")
            child = pexpect.spawn(
                f"ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null {cml_user}@{cml_host}",
                timeout=timeout,
                encoding='utf-8',
                codec_errors='replace'
            )
            
            # Enable logging for debugging
            child.logfile_read = LogAdapter(logger, logging.DEBUG, "RECV")
            
            # Handle SSH authentication to console server
            i = child.expect([
                r"[Pp]assword:",
                r"consoles>",
                pexpect.TIMEOUT,
                pexpect.EOF
            ], timeout=15)
            
            if i == 0:  # Password prompt
                logger.info("Got password prompt, authenticating")
                child.sendline(cml_pass)
                child.expect(r"consoles>", timeout=10)
            elif i == 1:  # Already at consoles prompt (key auth)
                logger.info("Already at consoles> prompt")
            elif i == 2:
                raise TimeoutError("Timeout waiting for SSH password prompt or consoles>")
            elif i == 3:
                raise ConnectionError("SSH connection closed unexpectedly")
            
            logger.info(f"Connected to CML console server, connecting to node {node_uuid}")
            
            # Connect to node console via console_key
            child.sendline(f"connect {node_uuid}")
            
            # Wait for BOTH connection messages
            child.expect(r"Connected to CML terminalserver", timeout=10)
            logger.info("Received 'Connected to CML terminalserver'")
            
            child.expect(r"Escape character is", timeout=5)
            logger.info("Received escape character message, device console is now ready")
            
            # Small delay for the console to be fully ready
            time.sleep(0.5)
            
            # Clear any buffered data
            try:
                child.read_nonblocking(size=4096, timeout=0.5)
            except pexpect.TIMEOUT:
                pass
            
            # Send carriage return to trigger prompt
            logger.info("Sending CR to trigger device prompt")
            child.send("\r")
            time.sleep(0.3)
            child.send("\r")
            
            # Cisco prompt patterns for all modes
            exec_prompt = r"[\w\-\.]+[>#]\s*$"
            config_prompt = r"[\w\-\.]+\([^\)]+\)#\s*$"
            any_prompt = r"[\w\-\.]+(\([^\)]+\))?[>#]\s*$"
            
            # Try to detect what state we're in
            logger.info("Waiting for device prompt...")
            i = child.expect([
                r"[Uu]sername:",
                r"[Ll]ogin:",
                r"[Pp]assword:",
                any_prompt,
                pexpect.TIMEOUT
            ], timeout=15)
            
            if i == 4:  # Timeout
                logger.warning(f"Timeout waiting for prompt. Buffer: {repr(child.before)}")
                for attempt in range(3):
                    child.send("\r")
                    time.sleep(0.5)
                    try:
                        child.expect([any_prompt], timeout=5)
                        break
                    except pexpect.TIMEOUT:
                        continue
                else:
                    raise TimeoutError("Could not detect device prompt")
                        
            elif i in [0, 1]:  # Username/Login prompt
                if not device_user:
                    raise ValueError("Device requires authentication but no credentials provided")
                logger.info("Device requires authentication, logging in")
                child.sendline(device_user)
                child.expect(r"[Pp]assword:", timeout=5)
                child.sendline(device_pass)
                child.expect(any_prompt, timeout=10)
                
            elif i == 2:  # Password prompt directly
                if not device_pass:
                    raise ValueError("Device requires password but none provided")
                child.sendline(device_pass)
                child.expect(any_prompt, timeout=10)
            
            current_prompt = child.after.strip() if child.after else ""
            logger.info(f"Device prompt detected: '{current_prompt}'")
            
            # Enter enable mode if needed
            if current_prompt.endswith('>'):
                logger.info("In user mode, entering enable mode")
                child.sendline("enable")
                i = child.expect([r"[Pp]assword:", r"#"], timeout=5)
                if i == 0 and device_enable_pass:
                    child.sendline(device_enable_pass)
                    child.expect(r"#", timeout=5)
            
            # Enter config mode
            logger.info("Entering configuration mode")
            child.sendline("configure terminal")
            child.expect(config_prompt, timeout=5)
            all_output.append("Entered configuration mode")
            
            # Execute each config command with same timing fix
            for cmd in commands:
                logger.info(f"Executing config command: {cmd}")
                child.sendline(cmd)
                
                # Apply same timing fix for config commands
                time.sleep(0.2)
                
                # Wait for next prompt (could be config or sub-config mode)
                child.expect([config_prompt, any_prompt], timeout=10)
                output = child.before
                if output:
                    all_output.append(f"{cmd}: {output.strip()}")
                else:
                    all_output.append(f"{cmd}: OK")
            
            # Exit config mode
            logger.info("Exiting configuration mode")
            child.sendline("end")
            child.expect(exec_prompt, timeout=5)
            all_output.append("Exited configuration mode")
            
            # Optionally save config
            # child.sendline("write memory")
            # child.expect(exec_prompt, timeout=30)
            # all_output.append("Configuration saved")
            
            # Clean exit from console
            logger.info("Disconnecting from device console")
            child.sendcontrol(']')
            
            try:
                child.expect(r"consoles>", timeout=5)
                child.sendline("exit")
            except pexpect.TIMEOUT:
                logger.warning("Timeout waiting for consoles>, forcing close")
            
            child.close()
            
            return "\n".join(all_output)
            
        except pexpect.TIMEOUT as e:
            buffer_content = child.buffer if child and hasattr(child, 'buffer') else 'N/A'
            before_content = child.before if child and hasattr(child, 'before') else 'N/A'
            logger.error(f"Timeout. Buffer: {repr(buffer_content)}, Before: {repr(before_content)}")
            if child:
                child.close(force=True)
            raise TimeoutError(
                f"Config command timed out. Buffer: {repr(buffer_content)}, Before: {repr(before_content)}"
            )
        except pexpect.EOF as e:
            logger.error("SSH connection closed unexpectedly")
            if child:
                child.close(force=True)
            raise ConnectionError(f"SSH connection closed: {str(e)}")
        except Exception as e:
            if child:
                child.close(force=True)
            logger.error(f"Config execution failed: {e}")
            raise RuntimeError(f"Config execution failed: {str(e)}")
    
    loop = asyncio.get_event_loop()
    output = await loop.run_in_executor(None, _ssh_config_execute)
    return output


def _clean_output(output: str, command: str) -> str:
    """Clean up command output
    
    Args:
        output: Raw output from device
        command: The command that was executed
        
    Returns:
        Cleaned output string
    """
    # Remove ANSI escape sequences
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    output = ansi_escape.sub('', output)
    
    # Remove carriage returns
    output = output.replace('\r\n', '\n').replace('\r', '\n')
    
    # Split into lines
    lines = output.split('\n')
    
    # Remove the command echo (first line often contains the command)
    if lines and command in lines[0]:
        lines = lines[1:]
    
    # Remove empty lines at start and end
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    
    # Rejoin and strip trailing whitespace from each line
    output = '\n'.join(line.rstrip() for line in lines)
    
    return output.strip()


class LogAdapter:
    """Adapter to redirect pexpect output to logger"""
    
    def __init__(self, logger, level, prefix):
        self.logger = logger
        self.level = level
        self.prefix = prefix
        self.buffer = ""
    
    def write(self, data):
        self.buffer += data
        while '\n' in self.buffer:
            line, self.buffer = self.buffer.split('\n', 1)
            if line.strip():
                self.logger.log(self.level, f"{self.prefix}: {repr(line)}")
    
    def flush(self):
        if self.buffer.strip():
            self.logger.log(self.level, f"{self.prefix}: {repr(self.buffer)}")
            self.buffer = ""
