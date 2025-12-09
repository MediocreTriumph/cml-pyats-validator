#!/usr/bin/env python3
"""
Debug script for CML console connections

Run this directly to test console connectivity without MCP overhead.

Usage:
    python debug_console.py
    python debug_console.py --get-keys

Set environment variables or edit the values below.
"""

import pexpect
import time
import sys
import os

# =============================================================================
# CONFIGURATION - Edit these or set as environment variables
# =============================================================================
CML_HOST = os.environ.get("CML_HOST", "23.137.84.109")
CML_USER = os.environ.get("CML_USER", "mediocretriumph")
CML_PASS = os.environ.get("CML_PASS", "tavbyg-Moxvet-0pibxe")

# Console key for the device you want to test
# Get this from CML API: GET /api/v0/labs/{lab_id}/nodes/{node_id}
# Look for serial_consoles[0].console_key
CONSOLE_KEY = os.environ.get("CONSOLE_KEY", "")  # You need to fill this in

# Command to test
TEST_COMMAND = "show ip interface brief"


def debug_console_connection():
    """Step-by-step console connection with verbose output"""
    
    print("=" * 60)
    print("CML Console Connection Debug Script")
    print("=" * 60)
    print(f"Host: {CML_HOST}")
    print(f"User: {CML_USER}")
    print(f"Console Key: {CONSOLE_KEY or 'NOT SET - please set CONSOLE_KEY'}")
    print("=" * 60)
    
    if not CONSOLE_KEY:
        print("\nERROR: CONSOLE_KEY not set!")
        print("\nTo get the console key:")
        print("1. Use the CML API: GET /api/v0/labs/{lab_id}/nodes/{node_id}")
        print("2. Look for: serial_consoles[0].console_key")
        print("3. Set CONSOLE_KEY environment variable or edit this script")
        print("\nOr run: python debug_console.py --get-keys")
        return
    
    print("\n[STEP 1] Spawning SSH connection...")
    child = pexpect.spawn(
        f"ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null {CML_USER}@{CML_HOST}",
        timeout=30,
        encoding='utf-8',
        codec_errors='replace'
    )
    
    # Log everything to stdout for debugging
    child.logfile_read = sys.stdout
    
    try:
        print("\n[STEP 2] Waiting for password prompt or consoles>...")
        i = child.expect([
            r"[Pp]assword:",
            r"consoles>",
            pexpect.TIMEOUT
        ], timeout=15)
        
        if i == 0:
            print("\n[STEP 2a] Got password prompt, sending password...")
            child.sendline(CML_PASS)
            child.expect(r"consoles>", timeout=10)
        elif i == 1:
            print("\n[STEP 2a] Already at consoles> (key auth)")
        else:
            print("\n[ERROR] Timeout waiting for prompt!")
            return
        
        print(f"\n[STEP 3] Connecting to console: {CONSOLE_KEY}...")
        child.sendline(f"connect {CONSOLE_KEY}")
        
        print("\n[STEP 4] Waiting for 'Connected to CML terminalserver'...")
        child.expect(r"Connected to CML terminalserver", timeout=10)
        print("  -> Got terminalserver message")
        
        print("\n[STEP 5] Waiting for escape character message...")
        child.expect(r"Escape character", timeout=5)
        print("  -> Got escape character message")
        
        print("\n[STEP 6] Small delay for console to stabilize...")
        time.sleep(0.5)
        
        print("\n[STEP 7] Clearing buffer...")
        try:
            data = child.read_nonblocking(size=4096, timeout=0.5)
            print(f"  -> Cleared: {repr(data)}")
        except pexpect.TIMEOUT:
            print("  -> Buffer was empty")
        
        print("\n[STEP 8] Sending carriage return to trigger prompt...")
        child.send("\r")
        time.sleep(0.3)
        
        print("\n[STEP 9] Looking for device prompt...")
        # Use a very flexible pattern first
        i = child.expect([
            r"[\w\-\.]+[>#]\s*$",  # Standard Cisco prompt
            r"[>#]\s*$",           # Minimal prompt
            r"[Uu]sername:",       # Login required
            pexpect.TIMEOUT
        ], timeout=10)
        
        if i == 0 or i == 1:
            print(f"  -> SUCCESS! Prompt detected: {repr(child.after)}")
        elif i == 2:
            print("  -> Device requires login (username prompt)")
            return
        else:
            print("\n[WARNING] Timeout on first attempt, trying again...")
            child.send("\r")
            time.sleep(0.5)
            child.send("\r")
            time.sleep(0.5)
            
            try:
                child.expect([r"[>#]"], timeout=5)
                print(f"  -> SUCCESS on retry! Prompt: {repr(child.after)}")
            except pexpect.TIMEOUT:
                print(f"\n[ERROR] Could not detect prompt!")
                print(f"Buffer contents: {repr(child.before)}")
                return
        
        print(f"\n[STEP 10] Executing command: {TEST_COMMAND}")
        child.sendline(TEST_COMMAND)
        
        child.expect([r"[>#]"], timeout=30)
        output = child.before
        
        print("\n" + "=" * 60)
        print("COMMAND OUTPUT:")
        print("=" * 60)
        print(output)
        print("=" * 60)
        
        print("\n[STEP 11] Disconnecting...")
        child.sendcontrol(']')
        try:
            child.expect(r"consoles>", timeout=5)
            child.sendline("exit")
        except pexpect.TIMEOUT:
            print("  -> Timeout waiting for consoles>, forcing close")
        
        print("\n[SUCCESS] Test completed!")
        
    except pexpect.TIMEOUT as e:
        print(f"\n[ERROR] Timeout: {e}")
        print(f"Buffer: {repr(child.buffer) if hasattr(child, 'buffer') else 'N/A'}")
        print(f"Before: {repr(child.before) if hasattr(child, 'before') else 'N/A'}")
    except Exception as e:
        print(f"\n[ERROR] {type(e).__name__}: {e}")
    finally:
        child.close()


def get_console_key_from_api():
    """Helper to get console key from CML API"""
    import httpx
    import urllib3
    urllib3.disable_warnings()
    
    print("\n" + "=" * 60)
    print("Getting console keys from CML API")
    print("=" * 60)
    
    lab_id = input("Enter lab ID (or press Enter for e65d8b6e-c8ac-4e79-82f6-736169c69c73): ").strip()
    if not lab_id:
        lab_id = "e65d8b6e-c8ac-4e79-82f6-736169c69c73"
    
    with httpx.Client(verify=False, timeout=30.0) as client:
        # Authenticate
        print("\nAuthenticating...")
        resp = client.post(
            f"https://{CML_HOST}/api/v0/authenticate",
            json={"username": CML_USER, "password": CML_PASS}
        )
        
        if resp.status_code != 200:
            print(f"Authentication failed: {resp.status_code} - {resp.text}")
            return
        
        token = resp.text.strip('"')
        headers = {"Authorization": f"Bearer {token}"}
        
        # Get topology
        print("Getting lab topology...")
        resp = client.get(
            f"https://{CML_HOST}/api/v0/labs/{lab_id}/topology",
            headers=headers
        )
        
        if resp.status_code != 200:
            print(f"Failed to get topology: {resp.status_code}")
            return
        
        topology = resp.json()
        nodes = topology.get('nodes', [])
        
        print(f"\nFound {len(nodes)} nodes:\n")
        print(f"{'Label':<15} {'Node ID':<40} {'Console Key':<40}")
        print("-" * 95)
        
        for node in nodes:
            label = node.get('label', 'unknown')
            node_id = node.get('id', 'unknown')
            consoles = node.get('serial_consoles', [])
            console_key = consoles[0].get('console_key', 'N/A') if consoles else 'N/A'
            
            print(f"{label:<15} {node_id:<40} {console_key:<40}")
        
        print("\nUse one of the console keys above with this script.")
        print("Example: CONSOLE_KEY=<key> python debug_console.py")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--get-keys":
        get_console_key_from_api()
    else:
        print("\nTip: Run with --get-keys to fetch console keys from CML API\n")
        debug_console_connection()
