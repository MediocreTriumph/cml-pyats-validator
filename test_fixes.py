#!/usr/bin/env python3
"""
Test script for ASA command mapping and ping parsing fixes
"""
import asyncio
import sys
sys.path.insert(0, 'src')

from cml_pyats_validator.tools import (
    initialize_cml_client,
    validate_routing_protocols,
    validate_device_interfaces,
    test_network_reachability,
)


async def main():
    print("=" * 80)
    print("Testing CML PyATS Validator ASA Fixes")
    print("=" * 80)

    # Initialize CML client
    print("\n1. Initializing CML client...")
    init_result = await initialize_cml_client(
        cml_url="https://23.137.84.109",
        username="mediocretriumph",
        password="tavbyg-Moxvet-0pibxe",
        verify_ssl=False
    )
    print(f"   Result: {init_result}")

    if "error" in init_result:
        print("   FAILED: Could not initialize CML client")
        return

    # Get the lab ID for asa-bgp-basic-01
    # List all labs and fetch details to find the correct one
    from cml_pyats_validator.tools.auth import get_cml_client
    client = get_cml_client()

    print("\n2. Finding asa-bgp-basic-01 lab...")
    try:
        # Get list of lab IDs
        lab_ids = await client._request('GET', '/api/v0/labs')

        lab_id = None
        lab_title = None

        # Fetch details for each lab to find the ASA BGP lab
        for lid in lab_ids:
            try:
                lab_details = await client.get_lab(lid)
                title = lab_details.get('lab_title', '')
                print(f"   Checking lab: {title}")

                if ('asa' in title.lower() or 'asav' in title.lower()) and 'bgp' in title.lower():
                    lab_id = lid
                    lab_title = title
                    print(f"   ✓ Found ASA BGP lab: {title} (ID: {lab_id})")
                    break
            except Exception as e:
                print(f"   Warning: Could not get details for lab {lid}: {e}")
                continue

        if not lab_id:
            print("   ERROR: No ASA BGP lab found")
            print("   Please ensure the asa-bgp-basic-01 lab exists and is running")
            return

    except Exception as e:
        print(f"   ERROR: {e}")
        import traceback
        traceback.print_exc()
        return

    # Test 1: Validate BGP protocols on ASAv (should use "show bgp summary")
    print(f"\n3. Testing ASA BGP validation (lab_id: {lab_id})...")
    bgp_result = await validate_routing_protocols(
        lab_id=lab_id,
        device_name="asav-0",
        protocol="bgp",
        validation_type="neighbors",
        device_credentials={
            "username": "cisco",
            "password": "cisco",
            "enable_password": "cisco"
        }
    )
    print(f"   Command used: {bgp_result.get('command', 'N/A')}")
    print(f"   Status: {bgp_result.get('status', 'N/A')}")
    if "error" in bgp_result:
        print(f"   ERROR: {bgp_result['error']}")
    else:
        print(f"   ✓ BGP validation executed successfully")
        if bgp_result.get('command') == 'show bgp summary':
            print(f"   ✓ CORRECT: Used ASA command 'show bgp summary'")
        else:
            print(f"   ✗ WRONG: Expected 'show bgp summary', got '{bgp_result.get('command')}'")

    # Test 2: Validate interfaces on ASAv (should use "show interface")
    print(f"\n4. Testing ASA interface validation...")
    intf_result = await validate_device_interfaces(
        lab_id=lab_id,
        device_name="asav-0",
        device_credentials={
            "username": "cisco",
            "password": "cisco",
            "enable_password": "cisco"
        }
    )
    print(f"   Command used: {intf_result.get('command', 'N/A')}")
    print(f"   Status: {intf_result.get('status', 'N/A')}")
    if "error" in intf_result:
        print(f"   ERROR: {intf_result['error']}")
    else:
        print(f"   ✓ Interface validation executed successfully")
        if intf_result.get('command') == 'show interface':
            print(f"   ✓ CORRECT: Used ASA command 'show interface'")
        else:
            print(f"   ✗ WRONG: Expected 'show interface', got '{intf_result.get('command')}'")

    # Test 3: Test reachability with an unreachable destination (should report failure)
    print(f"\n5. Testing ping parsing with unreachable destination...")
    ping_result = await test_network_reachability(
        lab_id=lab_id,
        source_device="asav-0",
        destination="192.0.2.1",  # TEST-NET-1, should be unreachable
        test_type="ping",
        count=3,
        expected_success=False,  # We expect this to fail
        device_credentials={
            "username": "cisco",
            "password": "cisco",
            "enable_password": "cisco"
        }
    )
    print(f"   Command: {ping_result.get('command', 'N/A')}")
    print(f"   Reachable: {ping_result.get('reachable', 'N/A')}")
    print(f"   Matches expectation: {ping_result.get('matches_expectation', 'N/A')}")

    if "error" in ping_result:
        print(f"   ERROR: {ping_result['error']}")
    else:
        if ping_result.get('reachable') == False:
            print(f"   ✓ CORRECT: Ping correctly reported as failed")
        else:
            print(f"   ✗ WRONG: Ping should have failed but reported as successful")

        if ping_result.get('matches_expectation'):
            print(f"   ✓ Result matches expected_success=False")

    print("\n" + "=" * 80)
    print("Testing complete!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
