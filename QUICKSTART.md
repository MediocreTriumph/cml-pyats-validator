# Quick Start Guide

Get up and running with CML PyATS Validator in 5 minutes.

## 1. Prerequisites Check

Ensure you have:
- [ ] Python 3.12 or higher installed
- [ ] Access to a CML server
- [ ] CML username and password
- [ ] tmux MCP server available (for console access)

## 2. Installation

```bash
# Option A: Install from PyPI (when published)
pip install cml-pyats-validator

# Option B: Install from source
git clone <repository-url>
cd cml-pyats-validator
uv sync
```

## 3. Configuration

Create `.env` file:

```bash
cp .env.example .env
# Edit .env with your CML credentials
```

Or configure Claude Desktop:

```json
{
  "mcpServers": {
    "cml-pyats-validator": {
      "command": "uvx",
      "args": ["cml-pyats-validator"],
      "env": {
        "CML_URL": "https://your-cml-server",
        "CML_USERNAME": "admin",
        "CML_PASSWORD": "password"
      }
    }
  }
}
```

## 4. Test Connection

Restart Claude Desktop, then try:

```
Initialize connection to CML server at https://your-cml-server with username admin
```

Expected response:
```json
{
  "status": "success",
  "message": "Successfully authenticated with CML server",
  "authenticated": true
}
```

## 5. Run Your First Validation

### Example 1: Execute a Command

```
Execute "show ip interface brief" on router R1 in lab <lab-id>
```

### Example 2: Validate OSPF

```
Check OSPF neighbors on R1 in lab <lab-id>
```

### Example 3: Full Health Check

```
Run a complete validation on all devices in lab <lab-id>
```

## 6. Common Workflows

### Troubleshooting OSPF

```
User: "OSPF neighbors aren't forming between R1 and R2"

Claude will:
1. Check interface status on both routers
2. Validate OSPF configuration
3. Test connectivity between routers
4. Identify configuration mismatches
5. Suggest fixes
```

### Verifying BGP Configuration

```
User: "I configured BGP. Is it working?"

Claude will:
1. Validate BGP neighbors are established
2. Check route advertisements
3. Verify peering configuration
4. Report any issues
```

### Pre-Deployment Validation

```
User: "Validate my lab is ready for the assignment"

Claude will:
1. Check all interfaces are up
2. Validate routing protocols
3. Test connectivity matrix
4. Check for errors
5. Provide go/no-go assessment
```

## Next Steps

- Read the [full README](README.md) for detailed documentation
- Review [usage examples](#usage-examples) for more scenarios
- Check [troubleshooting guide](#troubleshooting) if you hit issues
- Explore [PyATS parser integration](#pyats-parser-integration) to understand parsing

## Quick Reference

### Essential Tools

| Tool | Purpose | Example |
|------|---------|---------|
| `initialize_cml_client` | Connect to CML | "Connect to CML at https://..." |
| `execute_device_command` | Run any command | "Execute 'show version' on R1" |
| `validate_routing_protocols` | Check protocols | "Validate OSPF on R1" |
| `validate_device_interfaces` | Check interfaces | "Check interfaces on R1" |
| `test_network_reachability` | Test connectivity | "Can R1 ping 10.1.1.2?" |
| `get_configuration` | Get configs | "Get running config from R1" |
| `compare_configurations` | Compare configs | "Compare R1's configs" |
| `run_full_validation` | Full health check | "Validate entire lab" |

### Supported Protocols

- OSPF, BGP, EIGRP, RIP (routing)
- STP, VTP (Layer 2)
- HSRP, VRRP (redundancy)

### Supported Devices

- ✅ Full parsing: Cisco IOS, IOS-XE, NX-OS, IOS-XR, ASA
- ⚠️ Raw output: Palo Alto, FortiGate, Juniper, Linux

## Tips for Success

1. **Start Simple**: Begin with basic commands before complex validations
2. **Use Lab IDs**: Always provide the lab ID for context
3. **Be Specific**: Specify device names exactly as they appear in CML
4. **Check Status**: Use full validation to get overall health before troubleshooting
5. **Read Summaries**: Tool responses include human-readable summaries

## Getting Help

- Check logs in Claude Desktop for detailed errors
- Verify CML credentials are correct
- Ensure devices are started in CML
- Review the troubleshooting section in README
- Open GitHub issue if problem persists
