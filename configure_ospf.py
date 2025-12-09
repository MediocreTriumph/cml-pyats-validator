#!/usr/bin/env python3
"""
OSPF Configuration Script for CML Lab

Configures OSPF on all three routers (R1, R2, R3) in the test lab.

Topology:
    R1 -------- R2
     \        /
      \      /
       \    /
        \  /
         R3

IP Addressing:
    R1 Loopback0: 1.1.1.1/32
    R2 Loopback0: 2.2.2.2/32
    R3 Loopback0: 3.3.3.3/32
    
    R1-R2 Link: 10.1.2.0/24 (R1=.1, R2=.2)
    R1-R3 Link: 10.1.3.0/24 (R1=.1, R3=.3)
    R2-R3 Link: 10.2.3.0/24 (R2=.2, R3=.3)

All interfaces in OSPF Area 0.

Usage:
    python configure_ospf.py
"""

import pexpect
import time
import sys
import os
import httpx

# =============================================================================
# CONFIGURATION
# =============================================================================
CML_HOST = os.environ.get("CML_HOST", "23.137.84.109")
CML_USER = os.environ.get("CML_USER", "mediocretriumph")
CML_PASS = os.environ.get("CML_PASS", "tavbyg-Moxvet-0pibxe")
LAB_ID = "e65d8b6e-c8ac-4e79-82f6-736169c69c73"

# Router configurations
ROUTER_CONFIGS = {
    "R1": {
        "hostname": "R1",
        "loopback": "1.1.1.1",
        "interfaces": {
            "GigabitEthernet0/1": {"ip": "10.1.2.1", "mask": "255.255.255.0", "description": "Link to R2"},
            "GigabitEthernet0/2": {"ip": "10.1.3.1", "mask": "255.255.255.0", "description": "Link to R3"},
        }
    },
    "R2": {
        "hostname": "R2",
        "loopback": "2.2.2.2",
        "interfaces": {
            "GigabitEthernet0/1": {"ip": "10.1.2.2", "mask": "255.255.255.0", "description": "Link to R1"},
            "GigabitEthernet0/2": {"ip": "10.2.3.2", "mask": "255.255.255.0", "description": "Link to R3"},
        }
    },
    "R3": {
        "hostname": "R3",
        "loopback": "3.3.3.3",
        "interfaces": {
            "GigabitEthernet0/1": {"ip": "10.1.3.3", "mask": "255.255.255.0", "description": "Link to R1"},
            "GigabitEthernet0/2": {"ip": "10.2.3.3", "mask": "255.255.255.0", "description": "Link to R2"},
        }
    }
}


def get_console_keys():
    """Get console keys for all nodes from CML API"""
    import urllib3
    urllib3.disable_warnings()
    
    print("Fetching console keys from CML API...")
    
    with httpx.Client(verify=False, timeout=30.0) as client:
        # Authenticate
        resp = client.post(
            f"https://{CML_HOST}/api/v0/authenticate",
            json={"username": CML_USER, "password": CML_PASS}
        )
        
        if resp.status_code != 200:
            print(f"Authentication failed: {resp.status_code} - {resp.text}")
            return None
        
        token = resp.text.strip('"')
        headers = {"Authorization": f"Bearer {token}"}
        
        # Get topology
        resp = client.get(
            f"https://{CML_HOST}/api/v0/labs/{LAB_ID}/topology",
            headers=headers
        )
        
        if resp.status_code != 200:
            print(f"Failed to get topology: {resp.status_code}")
            return None
        
        topology = resp.json()
        nodes = topology.get('nodes', [])
        
        console_keys = {}
        for node in nodes:
            label = node.get('label', 'unknown')
            consoles = node.get('serial_consoles', [])
            if consoles:
                console_keys[label] = consoles[0].get('console_key')
        
        return console_keys


def configure_router(console_key: str, router_name: str, config: dict) -> bool:
    """Configure a single router via console"""
    
    print(f"\n{'='*60}")
    print(f"Configuring {router_name}")
    print(f"{'='*60}")
    
    child = pexpect.spawn(
        f"ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null {CML_USER}@{CML_HOST}",
        timeout=60,
        encoding='utf-8',
        codec_errors='replace'
    )
    
    try:
        # SSH authentication
        i = child.expect([r"[Pp]assword:", r"consoles>"], timeout=15)
        if i == 0:
            child.sendline(CML_PASS)
            child.expect(r"consoles>", timeout=10)
        
        print(f"  Connected to console server")
        
        # Connect to device console
        child.sendline(f"connect {console_key}")
        child.expect(r"Connected to CML terminalserver", timeout=10)
        child.expect(r"Escape character", timeout=5)
        
        print(f"  Connected to device console")
        
        time.sleep(0.5)
        
        # Clear buffer
        try:
            child.read_nonblocking(size=4096, timeout=0.5)
        except pexpect.TIMEOUT:
            pass
        
        # Get to prompt
        child.send("\r")
        time.sleep(0.3)
        child.send("\r")
        
        any_prompt = r"[\w\-\.]+(\([^\)]+\))?[>#]\s*"
        config_prompt = r"[\w\-\.]+\(config[^\)]*\)#"
        
        i = child.expect([any_prompt, pexpect.TIMEOUT], timeout=10)
        if i == 1:
            print(f"  WARNING: Timeout waiting for prompt, retrying...")
            child.send("\r")
            time.sleep(1)
            child.expect([any_prompt], timeout=10)
        
        current_prompt = child.after.strip() if child.after else ""
        print(f"  Device prompt: {current_prompt}")
        
        # Enter enable mode if needed
        if current_prompt.endswith('>'):
            print(f"  Entering enable mode...")
            child.sendline("enable")
            child.expect([r"#"], timeout=5)
        
        # Enter config mode
        print(f"  Entering configuration mode...")
        child.sendline("configure terminal")
        child.expect([config_prompt], timeout=5)
        
        # Build configuration commands
        commands = []
        
        # Hostname
        commands.append(f"hostname {config['hostname']}")
        
        # Loopback interface
        commands.append("interface Loopback0")
        commands.append(f" ip address {config['loopback']} 255.255.255.255")
        commands.append(" no shutdown")
        
        # Physical interfaces
        for intf, intf_config in config['interfaces'].items():
            commands.append(f"interface {intf}")
            commands.append(f" description {intf_config['description']}")
            commands.append(f" ip address {intf_config['ip']} {intf_config['mask']}")
            commands.append(" no shutdown")
        
        # OSPF configuration
        commands.append("router ospf 1")
        commands.append(" router-id " + config['loopback'])
        commands.append(" network 0.0.0.0 255.255.255.255 area 0")  # Advertise all interfaces
        
        # Execute each command
        for cmd in commands:
            child.sendline(cmd)
            child.expect([config_prompt, any_prompt], timeout=5)
            print(f"  > {cmd}")
        
        # Exit config mode
        child.sendline("end")
        child.expect([r"#"], timeout=5)
        print(f"  Exited configuration mode")
        
        # Save configuration
        print(f"  Saving configuration...")
        child.sendline("write memory")
        child.expect([r"\[OK\]", r"#"], timeout=30)
        child.expect([r"#"], timeout=5)
        print(f"  Configuration saved")
        
        # Verify OSPF
        print(f"  Verifying OSPF...")
        child.sendline("show ip ospf neighbor")
        child.expect([r"#"], timeout=10)
        print(child.before)
        
        # Clean exit
        child.sendcontrol(']')
        try:
            child.expect(r"consoles>", timeout=5)
            child.sendline("exit")
        except pexpect.TIMEOUT:
            pass
        
        child.close()
        print(f"  {router_name} configuration complete!")
        return True
        
    except Exception as e:
        print(f"  ERROR configuring {router_name}: {e}")
        if child:
            child.close(force=True)
        return False


def main():
    print("=" * 60)
    print("OSPF Configuration Script for CML Lab")
    print("=" * 60)
    print(f"CML Host: {CML_HOST}")
    print(f"Lab ID: {LAB_ID}")
    print("=" * 60)
    
    # Get console keys
    console_keys = get_console_keys()
    if not console_keys:
        print("ERROR: Could not get console keys")
        return
    
    print(f"\nFound {len(console_keys)} devices:")
    for name, key in console_keys.items():
        print(f"  {name}: {key}")
    
    # Configure each router
    success_count = 0
    for router_name, config in ROUTER_CONFIGS.items():
        if router_name not in console_keys:
            print(f"\nWARNING: {router_name} not found in lab!")
            continue
        
        console_key = console_keys[router_name]
        if configure_router(console_key, router_name, config):
            success_count += 1
        
        # Small delay between routers
        time.sleep(2)
    
    print("\n" + "=" * 60)
    print(f"Configuration complete: {success_count}/{len(ROUTER_CONFIGS)} routers configured")
    print("=" * 60)
    
    if success_count == len(ROUTER_CONFIGS):
        print("\nNext steps:")
        print("1. Wait 30-60 seconds for OSPF adjacencies to form")
        print("2. Run: python debug_console.py to verify connectivity")
        print("3. Use the MCP validator to test OSPF neighbors")


if __name__ == "__main__":
    main()
