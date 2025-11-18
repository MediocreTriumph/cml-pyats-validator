# Test Validation Scenarios

Example prompts and expected behaviors for testing the CML PyATS Validator.

## Prerequisites

1. CML server running with example topology loaded
2. Lab started with all devices booted
3. Server authenticated with CML

## Basic Execution Tests

### Test 1: Simple Command Execution

**Prompt:**
```
Execute "show ip interface brief" on R1 in lab <lab-id>
```

**Expected Result:**
- Command executes successfully
- Output is parsed (Cisco IOS device)
- Returns structured interface data
- Shows interface names, IPs, and status

**Validation Points:**
- ✓ Command sent to device
- ✓ Parser applied successfully
- ✓ Data structure returned
- ✓ No errors in output

---

### Test 2: Non-Parsed Command

**Prompt:**
```
Execute "show version" on R1 without parsing
```

**Expected Result:**
- Command executes successfully
- Returns raw text output
- Includes full version information
- Parser not applied (as requested)

**Validation Points:**
- ✓ use_parser=False works
- ✓ Raw output returned
- ✓ Complete text visible

---

## Protocol Validation Tests

### Test 3: OSPF Neighbor Validation

**Prompt:**
```
Validate OSPF neighbors on R1 in lab <lab-id>
```

**Expected Result:**
- Finds 2 OSPF neighbors (R2 and R3)
- Both neighbors in FULL state
- Status: PASS
- Summary shows neighbor count

**Validation Points:**
- ✓ Parser applied to show ip ospf neighbor
- ✓ Neighbor states extracted
- ✓ FULL state validated
- ✓ Pass/fail logic works

---

### Test 4: BGP Validation (Not Configured)

**Prompt:**
```
Check BGP neighbors on R1
```

**Expected Result:**
- Command executes
- No BGP configuration found
- Returns appropriate status
- No false positives

**Validation Points:**
- ✓ Handles unconfigured protocols
- ✓ Clear messaging
- ✓ No crash or error

---

### Test 5: Protocol State Check

**Prompt:**
```
Validate OSPF state on all routers in lab <lab-id>
```

**Expected Result:**
- Checks R1, R2, and R3
- All have OSPF running
- All have correct neighbors
- Overall PASS status

**Validation Points:**
- ✓ Multi-device validation
- ✓ Aggregated results
- ✓ Summary per device

---

## Interface Validation Tests

### Test 6: Interface Status Check

**Prompt:**
```
Check all interfaces on R1 for status
```

**Expected Result:**
- Lists all interfaces (Gi0/0, Gi0/1, Lo0)
- Shows up/up status for active interfaces
- No errors found
- Status: PASS

**Validation Points:**
- ✓ All interfaces discovered
- ✓ Operational status correct
- ✓ Line protocol status correct

---

### Test 7: Interface Error Detection

**Prompt:**
```
Check R1 for interface errors
```

**Expected Result:**
- Checks all interfaces
- Reports error counts
- CRC errors flagged if present
- Clear reporting

**Validation Points:**
- ✓ Error counters extracted
- ✓ High error counts flagged
- ✓ CRC errors highlighted

---

### Test 8: Specific Interface Check

**Prompt:**
```
Validate GigabitEthernet0/0 on R1
```

**Expected Result:**
- Only checks Gi0/0
- Status shown
- Errors checked
- Focused output

**Validation Points:**
- ✓ Single interface filtering works
- ✓ Detailed information provided

---

## Reachability Tests

### Test 9: Basic Ping Test

**Prompt:**
```
Can R1 ping 2.2.2.2? Lab ID is <lab-id>
```

**Expected Result:**
- Ping executes successfully
- 5 packets sent/received
- RTT statistics shown
- Status: PASS (reachable)

**Validation Points:**
- ✓ Ping command formatted correctly
- ✓ Statistics parsed
- ✓ Success rate calculated
- ✓ RTT values extracted

---

### Test 10: Traceroute Test

**Prompt:**
```
Trace route from R1 to 3.3.3.3
```

**Expected Result:**
- Traceroute executes
- Hops identified
- Destination reached
- Path shown

**Validation Points:**
- ✓ Hop information extracted
- ✓ IP addresses captured
- ✓ Destination reached status

---

### Test 11: Expected Failure Test

**Prompt:**
```
Test if R1 can ping 192.168.99.99. I expect this to fail.
```

**Expected Result:**
- Ping fails (as expected)
- 100% packet loss
- Status: PASS (failure expected and occurred)
- Clear messaging

**Validation Points:**
- ✓ expected_success parameter works
- ✓ Validation logic correct
- ✓ Clear pass/fail reasoning

---

## Configuration Management Tests

### Test 12: Get Running Config

**Prompt:**
```
Get the running configuration from R1
```

**Expected Result:**
- Full running-config retrieved
- Clean output (no prompts)
- Line count reported
- Configuration text returned

**Validation Points:**
- ✓ Config retrieved completely
- ✓ Command echo removed
- ✓ Proper text formatting

---

### Test 13: Compare Configs

**Prompt:**
```
Compare R1's running config to its startup config
```

**Expected Result:**
- Both configs retrieved
- Diff generated
- Changes highlighted
- Summary shows change count

**Validation Points:**
- ✓ Both configs fetched
- ✓ Diff is accurate
- ✓ Additions/deletions counted
- ✓ Context lines shown

---

### Test 14: Config Comparison

**Prompt:**
```
Compare these two configurations: [provides config1 and config2]
```

**Expected Result:**
- Unified diff generated
- Line-by-line comparison
- Change statistics
- Clear formatting

**Validation Points:**
- ✓ Direct comparison works
- ✓ Whitespace handling
- ✓ Context appropriate

---

## Comprehensive Validation Tests

### Test 15: Full Health Check

**Prompt:**
```
Run a full validation on lab <lab-id>
```

**Expected Result:**
- All devices checked
- Interfaces validated
- Protocols verified
- Errors checked
- Overall pass/fail
- Detailed summary

**Validation Points:**
- ✓ All checks execute
- ✓ Results aggregated
- ✓ Issues highlighted
- ✓ Summary clear

---

### Test 16: Selective Validation

**Prompt:**
```
Run interface and protocol checks on R1 and R2 only
```

**Expected Result:**
- Only R1 and R2 tested
- Only specified checks run
- Targeted results
- Efficient execution

**Validation Points:**
- ✓ Device filtering works
- ✓ Check filtering works
- ✓ Correct scope

---

### Test 17: Issue Detection

**Prompt:**
```
Validate the lab and identify any problems
```

**Expected Result:**
- Comprehensive scan
- Issues listed clearly
- Severity indicated
- Remediation hints

**Validation Points:**
- ✓ Issues detected
- ✓ Clear descriptions
- ✓ Actionable information

---

## Educational Scenarios

### Scenario 1: OSPF Troubleshooting

**Setup:** Intentionally misconfigure OSPF on R2 (wrong area)

**Prompt:**
```
OSPF neighbors aren't forming between R1 and R2. Help me troubleshoot.
```

**Expected Behavior:**
1. Claude validates OSPF on both routers
2. Discovers area mismatch
3. Checks interface status (both up)
4. Tests connectivity (works)
5. Identifies configuration issue
6. Suggests fix

---

### Scenario 2: Interface Down

**Setup:** Shutdown GigabitEthernet0/0 on R2

**Prompt:**
```
R1 can't reach R2's loopback. What's wrong?
```

**Expected Behavior:**
1. Tests reachability (fails)
2. Checks interfaces on both routers
3. Discovers Gi0/0 down on R2
4. Suggests bringing interface up
5. Verifies after fix

---

### Scenario 3: Lab Readiness

**Prompt:**
```
Is my lab ready for the OSPF assignment?
```

**Expected Behavior:**
1. Runs full validation
2. Checks all OSPF neighbors
3. Verifies all interfaces up
4. Tests full mesh connectivity
5. Provides go/no-go decision
6. Lists any remaining issues

---

## Error Handling Tests

### Test 18: Invalid Lab ID

**Prompt:**
```
Execute "show version" on R1 in lab invalid-id
```

**Expected Result:**
- Clear error message
- Lab not found indicated
- No crash
- Helpful guidance

---

### Test 19: Device Not Found

**Prompt:**
```
Check OSPF on RouterX in lab <lab-id>
```

**Expected Result:**
- Device not found error
- Lists available devices
- Clear messaging
- Suggestions provided

---

### Test 20: Device Not Started

**Prompt:**
```
Execute command on R1 when R1 is stopped
```

**Expected Result:**
- Cannot connect error
- Device state indicated
- Suggests starting device
- Graceful handling

---

## Performance Tests

### Test 21: Multiple Devices

**Prompt:**
```
Check interfaces on all devices in the lab
```

**Expected Result:**
- All devices processed
- Results aggregated
- Reasonable execution time
- Progress visible

---

### Test 22: Large Output

**Prompt:**
```
Get the full running config from all routers
```

**Expected Result:**
- All configs retrieved
- No truncation
- Proper formatting
- Complete data

---

## Success Criteria

For each test, verify:
- ✅ Tool executes without crashing
- ✅ Results are accurate
- ✅ Error handling is graceful
- ✅ Output is understandable
- ✅ Performance is acceptable
- ✅ Educational value is clear

## Test Execution Checklist

Before running tests:
- [ ] CML server accessible
- [ ] Example topology imported
- [ ] Lab started and converged
- [ ] Server authenticated
- [ ] Claude Desktop restarted

During testing:
- [ ] Note any unexpected behaviors
- [ ] Check logs for errors
- [ ] Verify parser application
- [ ] Test edge cases
- [ ] Document issues found

After testing:
- [ ] Review all results
- [ ] Identify improvements needed
- [ ] Update documentation
- [ ] Plan next iterations
