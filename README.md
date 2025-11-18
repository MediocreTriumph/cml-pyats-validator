# CML PyATS Validator

A lean MCP (Model Context Protocol) server for network device validation using PyATS parsers with tmux console access. Designed to complement CML lab-builder tools by providing validation and testing capabilities.

## Overview

This server enables Claude and other MCP clients to:
- Execute commands on CML network devices
- Parse output using PyATS/Genie parsers (Cisco devices)
- Validate routing protocols (OSPF, BGP, EIGRP, etc.)
- Check interface status and errors
- Test network reachability (ping/traceroute)
- Compare device configurations
- Run comprehensive testbed health checks

## Architecture

**Console Access**: Uses tmux MCP tools for persistent console sessions with CML devices  
**Parsing**: Applies PyATS/Genie parsers to command output for structured data  
**Multi-Vendor**: Cisco devices get parsed output; others return raw text for LLM interpretation

## Features

### 8 Core Tools

1. **initialize_cml_client** - Authenticate with CML server
2. **execute_device_command** - Run commands with optional parsing
3. **validate_routing_protocols** - Check OSPF, BGP, EIGRP, STP, etc.
4. **validate_device_interfaces** - Verify interface status and errors
5. **test_network_reachability** - Ping and traceroute testing
6. **get_configuration** - Retrieve running/startup configs
7. **compare_configurations** - Diff two configurations
8. **run_full_validation** - Comprehensive testbed health check

### Supported Protocols

- **Routing**: OSPF, BGP, EIGRP, RIP
- **L2**: STP, VTP
- **FHRP**: HSRP, VRRP

### Supported Devices

- **Full parsing**: Cisco IOS, IOS-XE, NX-OS, IOS-XR, ASA
- **Raw output**: Palo Alto, FortiGate, Juniper, Linux, etc.

## Installation

### Prerequisites

- Python 3.12 or higher
- Cisco Modeling Labs (CML) 2.9+
- tmux MCP server available in your environment
- Network connectivity to CML server

### Install from PyPI (when published)

```bash
pip install cml-pyats-validator
```

### Install from Source

```bash
# Clone the repository
git clone <repository-url>
cd cml-pyats-validator

# Install with uv
uv sync

# Or with pip
pip install -e .
```

## Configuration

### Environment Variables

Create a `.env` file in your project directory:

```bash
# CML Server Configuration
CML_URL=https://your-cml-server
CML_USERNAME=your-username
CML_PASSWORD=your-password
CML_VERIFY_SSL=true

# Device Credentials (for console/SSH access)
DEVICE_USERNAME=cisco
DEVICE_PASSWORD=cisco
DEVICE_ENABLE_PASSWORD=cisco

# Optional: Tmux Configuration
TMUX_SESSION_PREFIX=cml_validator
```

### Claude Desktop Configuration

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "cml-pyats-validator": {
      "command": "uvx",
      "args": ["cml-pyats-validator"],
      "env": {
        "CML_URL": "https://your-cml-server",
        "CML_USERNAME": "your-username",
        "CML_PASSWORD": "your-password",
        "DEVICE_USERNAME": "cisco",
        "DEVICE_PASSWORD": "cisco",
        "DEVICE_ENABLE_PASSWORD": "cisco"
      }
    }
  }
}
```

For development installations:

```json
{
  "mcpServers": {
    "cml-pyats-validator": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/cml-pyats-validator",
        "run",
        "cml-pyats-validator"
      ],
      "env": {
        "CML_URL": "https://your-cml-server",
        "CML_USERNAME": "admin",
        "CML_PASSWORD": "password"
      }
    }
  }
}
```

## Usage Examples

### Basic Command Execution

```
Execute "show ip interface brief" on R1 in lab abc123
```

Claude will:
1. Connect to device via tmux console
2. Execute the command
3. Parse output with Genie (if Cisco device)
4. Return structured data or raw output

### Protocol Validation

```
Validate OSPF neighbors on R1 in lab abc123
```

Returns:
- Neighbor status (FULL, INIT, etc.)
- Interface associations
- Issues found
- Pass/fail status

### Interface Health Check

```
Check all interfaces on R1 for errors
```

Returns:
- Interface operational status
- Error counts (CRC, frame, overrun)
- Issues requiring attention
- Overall health assessment

### Reachability Testing

```
Can R1 ping 10.1.1.2? The lab ID is abc123
```

Returns:
- Success/failure status
- Packet loss percentage
- RTT statistics
- Validation against expected result

### Configuration Management

```
Get the running config from R1 and compare it to the startup config
```

Returns:
- Both configurations
- Unified diff showing changes
- Number of additions/deletions

### Comprehensive Validation

```
Run a full health check on lab abc123
```

Performs:
- Interface status checks on all devices
- Protocol neighbor validation
- Error detection
- Connectivity tests
- Aggregated pass/fail report

## Integration with tmux MCP

This server requires tmux MCP tools for console access. The integration works as follows:

1. **Session Creation**: Creates persistent tmux sessions per device
2. **Command Execution**: Sends commands via `tmux send-keys`
3. **Output Capture**: Retrieves output via `tmux capture-pane`
4. **Parser Application**: Applies Genie parsers to captured text

### Example Flow

```
User: "Execute 'show version' on R1"
  ↓
Server: Get device info from CML API
  ↓
Server: Create/attach tmux session "cml_abc123_R1"
  ↓
Server: Send command via tmux
  ↓
Server: Capture output from tmux
  ↓
Server: Apply Genie ShowVersion parser
  ↓
Server: Return structured version data
```

## PyATS Parser Integration

### How It Works

1. **Device Detection**: Identifies device OS from CML node definition
2. **Parser Lookup**: Searches for appropriate Genie parser
3. **Text Parsing**: Applies parser to raw command output
4. **Structured Output**: Returns parsed data or raw text if no parser

### Cisco Device Types Supported

- `iosv` → ios
- `iosvl2` → ios
- `csr1000v` → iosxe
- `nxosv` → nxos
- `asav` → asa
- `iosxrv` → iosxr

### Common Parsers Available

- `show version`
- `show ip interface brief`
- `show interfaces`
- `show ip route`
- `show ip ospf neighbor`
- `show ip bgp summary`
- `show ip eigrp neighbors`
- `show spanning-tree`
- `show vlan`
- `show cdp neighbors`
- And 100+ more...

### Graceful Degradation

When no parser is available:
- Returns raw text output
- Includes note explaining parser unavailable
- Claude can still interpret results
- Works for all device types

## Educational Use Cases

### Network Troubleshooting Practice

```
I have a lab where OSPF isn't forming neighbors. Can you help me troubleshoot?
```

Claude uses validation tools to:
- Check interface status
- Verify OSPF configuration
- Test connectivity
- Identify mismatches (area, timers, etc.)

### Configuration Verification

```
I just configured BGP. Can you verify it's working correctly?
```

Claude performs:
- BGP neighbor validation
- Route advertisement checks
- Configuration review
- Best practice recommendations

### Lab Assessment

```
Is my lab configured correctly according to the topology diagram?
```

Claude runs:
- Full testbed validation
- Protocol checks on all routers
- Interface status verification
- Connectivity matrix testing

## Architecture Details

### Project Structure

```
cml-pyats-validator/
├── src/
│   └── cml_pyats_validator/
│       ├── __init__.py
│       ├── server.py           # FastMCP server
│       ├── client.py            # CML API client
│       ├── pyats_helper.py      # Parser integration
│       ├── utils.py             # Helper functions
│       └── tools/
│           ├── __init__.py
│           ├── auth.py
│           ├── execution.py
│           ├── protocol_validation.py
│           ├── interface_validation.py
│           ├── reachability.py
│           ├── config_tools.py
│           └── testbed.py
├── pyproject.toml
├── README.md
└── .env.example
```

### Key Components

**CMLClient**: Handles CML API authentication and requests  
**PyATSHelper**: Maps device types to parsers, applies parsing  
**Tools**: Individual MCP tools with specific validation logic  
**Utils**: Text parsing for ping, traceroute, configs, etc.

## Limitations & Future Work

### Current Limitations

1. **Tmux Integration**: Console access via tmux not fully implemented
2. **IP Discovery**: Connectivity testing requires manual IP input
3. **Limited Non-Cisco**: No parsing for Palo Alto, FortiGate, etc.
4. **State Management**: Sessions not persistent across server restarts

### Future Enhancements

- [ ] Complete tmux console integration
- [ ] Automatic device IP discovery
- [ ] Support for SSH connections (when configured)
- [ ] Configuration deployment capabilities
- [ ] Lab snapshot/restore functionality
- [ ] Performance metrics collection
- [ ] Custom validation rule engine
- [ ] Multi-vendor parser support

## Troubleshooting

### Authentication Fails

```
Error: CML authentication failed: 401 Unauthorized
```

**Solution**: Check CML_URL, CML_USERNAME, CML_PASSWORD in env

### Parser Not Available

```
Note: PyATS parser not available for 'show ip route' on ios
```

**Solution**: This is normal - not all commands have parsers. Raw output is returned.

### Device Not Found

```
Error: Device 'R1' not found in lab
```

**Solution**: Verify device label matches exactly (case-sensitive)

### Console Access Issues

```
Error: Tmux console integration is not yet implemented
```

**Solution**: This is expected - tmux integration is a placeholder for future implementation

## Development

### Running Tests

```bash
# Install dev dependencies
uv sync --all-extras

# Run tests (when test suite is created)
pytest tests/
```

### Adding New Tools

1. Create tool function in appropriate module under `tools/`
2. Import in `tools/__init__.py`
3. Register in `server.py` with `@mcp.tool()` decorator
4. Update README with usage examples

### Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

For issues and questions:
- GitHub Issues: [repository-url]/issues
- Documentation: [repository-url]/docs

## Related Projects

- **cml-lab-builder**: MCP server for creating CML topologies
- **tmux-mcp**: MCP server for tmux session management
- **PyATS**: Cisco's Python automation framework
- **Genie**: PyATS parser library

## Acknowledgments

- Built with FastMCP 2.0
- Uses PyATS/Genie for parsing
- Inspired by xorrkaz/cml-mcp
- Designed for network engineering education
