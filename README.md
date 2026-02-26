# CML PyATS Validator

A lean MCP (Model Context Protocol) server for network device validation using PyATS parsers with SSH console access. Designed to complement CML lab-builder tools by providing validation and testing capabilities.

## Overview

This server enables Claude and other MCP clients to:
- Execute commands on CML network devices via SSH console
- Parse output using PyATS/Genie parsers (Cisco devices)
- Validate routing protocols (OSPF, BGP, EIGRP, etc.)
- Check interface status and errors
- Test network reachability (ping/traceroute)
- Compare device configurations
- Run comprehensive testbed health checks

## Architecture

**Console Access**: SSHes directly to the CML console server using per-device console keys obtained from the CML API. No external tools required.
**Parsing**: Applies PyATS/Genie parsers to command output for structured data
**Multi-Vendor**: Cisco devices get parsed output; others return raw text for LLM interpretation
**Transport**: Supports `stdio` (Claude Desktop) and `streamable-http` (Docker/remote) modes

## Features

### 8 Core Tools

1. **initialize_cml_client** - Authenticate with CML server
2. **execute_device_command** - Run commands with optional PyATS parsing
3. **validate_routing_protocols** - Check OSPF, BGP, EIGRP, STP, etc.
4. **validate_device_interfaces** - Verify interface status and errors
5. **test_network_reachability** - Ping and traceroute testing with actual success-rate detection
6. **get_configuration** - Retrieve running/startup configs
7. **compare_configurations** - Diff two configurations
8. **run_full_validation** - Comprehensive testbed health check

### Supported Protocols

- **Routing**: OSPF, BGP, EIGRP, RIP
- **L2**: STP, VTP
- **FHRP**: HSRP, VRRP

### Supported Devices

- **Full parsing**: Cisco IOS, IOS-XE, NX-OS, IOS-XR
- **ASA-aware**: Cisco ASA uses platform-correct commands (`show interface`, `show ospf neighbor`, etc.)
- **Raw output**: Palo Alto, FortiGate, Juniper, Linux, etc.

## Installation

### Prerequisites

- Python 3.10 or higher
- Cisco Modeling Labs (CML) 2.9+
- Network connectivity to CML server

### Install from Source

```bash
# Clone the repository
git clone https://github.com/MediocreTriumph/cml-pyats-validator
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

# Device Credentials (for console access)
DEVICE_USERNAME=cisco
DEVICE_PASSWORD=cisco
DEVICE_ENABLE_PASSWORD=cisco

# Transport (stdio or streamable-http)
TRANSPORT=stdio
HOST=0.0.0.0
PORT=9001
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

### HTTP / Streamable-HTTP Mode

The server supports `streamable-http` transport for use with remote MCP clients or Docker deployments. Configure via CLI flags or environment variables:

```bash
# CLI flags
cml-pyats-validator --transport streamable-http --host 0.0.0.0 --port 9001

# Environment variables (useful for Docker)
TRANSPORT=streamable-http HOST=0.0.0.0 PORT=9001 cml-pyats-validator
```

## Docker

A pre-built `Dockerfile` runs the server in `streamable-http` mode on port 9001. It forces `linux/amd64` so that PyATS/Unicon wheels (x86-only) work correctly even on Apple Silicon Macs via Rosetta.

### Build

```bash
docker build -t cml-pyats-validator .
```

### Run

```bash
docker run -d \
  -p 9001:9001 \
  -e CML_URL=https://your-cml-server \
  -e CML_USERNAME=admin \
  -e CML_PASSWORD=password \
  -e CML_VERIFY_SSL=false \
  -e DEVICE_USERNAME=cisco \
  -e DEVICE_PASSWORD=cisco \
  -e DEVICE_ENABLE_PASSWORD=cisco \
  cml-pyats-validator
```

The MCP endpoint will be available at `http://localhost:9001/mcp`.

### Connect Claude Desktop to Docker

```json
{
  "mcpServers": {
    "cml-pyats-validator": {
      "url": "http://localhost:9001/mcp"
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
1. Fetch device info and console key from CML API
2. SSH to CML console server and connect to device console
3. Execute the command
4. Parse output with Genie (if Cisco device)
5. Return structured data or raw output

### Protocol Validation

```
Validate OSPF neighbors on R1 in lab abc123
```

Returns:
- Neighbor status (FULL, INIT, etc.)
- Interface associations
- Issues found
- Pass/fail status

The tool automatically detects device type (IOS vs ASA) and uses the correct commands:
- IOS: `show ip ospf neighbor`
- ASA: `show ospf neighbor`

### Interface Health Check

```
Check all interfaces on R1 for errors
```

Returns:
- Interface operational status
- Error counts (CRC, frame, overrun)
- Issues requiring attention
- Overall health assessment

Device-type-aware command selection:
- IOS/IOS-XE/NX-OS: `show interfaces`
- ASA: `show interface`

### Reachability Testing

```
Can R1 ping 10.1.1.2? The lab ID is abc123
```

Returns:
- Success/failure status (from actual `Success rate is X percent` parsing)
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

## Console Access

The server SSHes directly to the CML console server using per-device console keys:

1. **Node lookup**: Finds device by label via `GET /api/v0/labs/{lab_id}/nodes`
2. **Console key**: Fetches key via `GET /api/v0/labs/{lab_id}/nodes/{node_id}/keys/console?line=0`
3. **SSH session**: Opens SSH to CML host using the console key as the username
4. **Command execution**: Sends command and captures output via `pexpect`
5. **Parser application**: Applies Genie parsers to captured text

## PyATS Parser Integration

### How It Works

1. **Device Detection**: Identifies device OS from CML node definition
2. **Parser Lookup**: Searches for appropriate Genie parser
3. **Text Parsing**: Applies parser to raw command output
4. **Structured Output**: Returns parsed data or raw text if no parser

### Cisco Device Types Supported

| CML Node Definition | Genie OS |
|---------------------|----------|
| `iosv`              | `ios`    |
| `iosvl2`            | `ios`    |
| `csr1000v`          | `iosxe`  |
| `nxosv`             | `nxos`   |
| `asav`              | `asa`    |
| `iosxrv`            | `iosxr`  |

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
│       ├── server.py               # FastMCP server, transport config
│       ├── client.py               # CML API client
│       ├── console_executor.py     # SSH console access via pexpect
│       ├── pyats_helper.py         # Parser integration
│       ├── utils.py                # Helper functions
│       └── tools/
│           ├── __init__.py
│           ├── auth.py
│           ├── execution.py
│           ├── protocol_validation.py  # IOS + ASA protocol commands
│           ├── interface_validation.py # IOS + ASA interface commands
│           ├── reachability.py         # Ping success-rate parsing
│           ├── config_tools.py
│           └── testbed.py
├── Dockerfile                      # x86_64, streamable-http on port 9001
├── entrypoint.sh
├── pyproject.toml
├── uv.lock
├── README.md
└── .env.example
```

### Key Components

**CMLClient**: Handles CML API authentication, node lookup, and console key retrieval
**console_executor**: SSH + pexpect session management for device console access
**PyATSHelper**: Maps device types to parsers, applies parsing
**Tools**: Individual MCP tools with device-type-aware validation logic
**Utils**: Text parsing for ping, traceroute, configs, etc.

## Troubleshooting

### Authentication Fails

```
Error: CML authentication failed: 401 Unauthorized
```

**Solution**: Check `CML_URL`, `CML_USERNAME`, `CML_PASSWORD` in your environment.

### Parser Not Available

```
Note: PyATS parser not available for 'show ip route' on ios
```

**Solution**: Normal behavior — not all commands have parsers. Raw output is returned and can be interpreted by Claude.

### Device Not Found

```
Error: Device 'R1' not found in lab
```

**Solution**: Verify the device label matches exactly (case-sensitive).

### Console Key Error

```
Error: Failed to get console key for device 'R1'
```

**Solution**: Ensure the lab is running and the node is started in CML. Console keys are only available for running nodes.

### PyATS on Apple Silicon

PyATS/Unicon only ships x86_64 wheels. On Apple Silicon Macs, use the Docker image (which runs under Rosetta) or a Linux x86 VM.

## Development

### Running Tests

```bash
# Install dev dependencies
uv sync --all-extras

# Run tests
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

## Related Projects

- **cml-lab-builder**: MCP server for creating CML topologies
- **PyATS**: Cisco's Python automation framework
- **Genie**: PyATS parser library

## Acknowledgments

- Built with [FastMCP](https://github.com/jlowin/fastmcp) 2.0
- Uses PyATS/Genie for parsing
- Inspired by xorrkaz/cml-mcp
- Designed for network engineering education
