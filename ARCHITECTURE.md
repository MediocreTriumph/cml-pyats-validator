# Architecture Overview

Technical architecture of the CML PyATS Validator MCP server.

## High-Level Architecture

```
┌─────────────┐
│   Claude    │
│  (MCP Client)│
└──────┬──────┘
       │ MCP Protocol
       ▼
┌──────────────────────────┐
│  CML PyATS Validator     │
│  (FastMCP Server)        │
├──────────────────────────┤
│  8 MCP Tools:            │
│  - initialize_client     │
│  - execute_command       │
│  - validate_protocols    │
│  - validate_interfaces   │
│  - validate_reachability │
│  - get_device_config     │
│  - compare_configs       │
│  - run_testbed_validation│
└───┬──────────────┬───────┘
    │              │
    ▼              ▼
┌─────────┐   ┌──────────┐
│  CML    │   │  tmux    │
│  API    │   │  MCP     │
└────┬────┘   └────┬─────┘
     │             │
     ▼             ▼
┌─────────────────────────┐
│  CML Server             │
│  ┌─────────────────┐    │
│  │  Network Devices│    │
│  │  (via console)  │    │
│  └─────────────────┘    │
└─────────────────────────┘
```

## Component Architecture

### 1. FastMCP Server (`server.py`)

**Responsibilities:**
- Expose 8 MCP tools to clients
- Handle tool invocations
- Manage error responses
- Coordinate between components

**Key Design:**
- Stateless tool functions
- Global CML client instance
- Async/await for I/O operations

---

### 2. CML Client (`client.py`)

**Responsibilities:**
- Authenticate with CML API
- Make HTTP requests to CML
- Manage API tokens
- Query lab and device information

**Key Methods:**
```python
authenticate()          # Get API token
get_lab(lab_id)        # Lab details
get_nodes(lab_id)      # All nodes
get_node_by_label()    # Find device
```

**Authentication Flow:**
```
1. Client created with credentials
2. First API call triggers authentication
3. Token stored for subsequent requests
4. Token reused until expiration
```

---

### 3. PyATS Helper (`pyats_helper.py`)

**Responsibilities:**
- Map CML device types to PyATS OS types
- Apply Genie parsers to command output
- Handle parser failures gracefully
- Return structured or raw data

**Device Type Mapping:**
```python
DEVICE_TYPE_MAPPING = {
    "iosv": "ios",
    "csr1000v": "iosxe",
    "nxosv": "nxos",
    # ... etc
}
```

**Parser Application Logic:**
```
1. Detect device OS from node_definition
2. Check if Cisco device
3. If Cisco:
   - Normalize command
   - Look up parser
   - Apply to output
   - Return structured data
4. If not Cisco or no parser:
   - Return raw output
   - Note parser unavailable
```

---

### 4. Tools Package (`tools/`)

Individual modules for each validation capability:

#### **auth.py** - Authentication
- Global client instance management
- Credential storage
- Client initialization

#### **execution.py** - Command Execution
- Console command execution
- Parser application
- Output formatting
- Error handling

#### **protocol_validation.py** - Protocol Validation
- Protocol-specific commands
- Neighbor state validation
- Route verification
- Issue detection

#### **interface_validation.py** - Interface Validation
- Interface status checks
- Error detection
- Health assessment
- Multi-interface support

#### **reachability.py** - Connectivity Testing
- Ping execution and parsing
- Traceroute execution and parsing
- Validation against expectations
- Connectivity matrix testing

#### **config_tools.py** - Configuration Management
- Config retrieval
- Config comparison
- Diff generation
- Backup functionality

#### **testbed.py** - Comprehensive Validation
- Multi-device orchestration
- Multiple validation types
- Result aggregation
- Overall assessment

---

### 5. Utilities (`utils.py`)

Helper functions for:
- Ping output parsing
- Traceroute output parsing
- Configuration comparison
- Interface error extraction
- Session name sanitization

---

## Data Flow

### Typical Command Execution

```
1. User Prompt → Claude
   "Execute show version on R1"

2. Claude → MCP Tool Call
   execute_device_command(
     lab_id="abc123",
     device_name="R1",
     command="show version",
     use_parser=True
   )

3. Tool → CML Client
   - Get lab details
   - Find node by label "R1"
   - Get node definition (e.g., "iosv")

4. Tool → PyATS Helper
   - Detect OS type: "ios"
   - Is Cisco? Yes

5. Tool → tmux (future)
   - Create session for device
   - Send command
   - Capture output

6. PyATS Helper → Parser
   - Normalize: "show version"
   - Find: ShowVersion parser
   - Parse output → structured data

7. Tool → Claude
   - Return parsed data
   - Include metadata

8. Claude → User
   - Present results
   - Answer question
```

---

## Parser Integration Design

### Parser Lookup Strategy

```python
from genie.libs.parser.utils import get_parser

# 1. Create device object
device = Device(name="R1", os="ios")

# 2. Get parser for command
parser_class = get_parser(command, device)

# 3. Instantiate parser
parser = parser_class(device="R1")

# 4. Parse output
result = parser.parse(output=raw_text)
```

### Graceful Degradation

```
Try:
  Apply parser → Success → Return structured
Except ParserNotFound:
  Return raw output + note
Except ParsingError:
  Return raw output + note
```

---

## Console Access Strategy

### Current State (Placeholder)

Console access is **not yet implemented**. Current code:
- Gets device information from CML API
- Returns structure showing what would be done
- Notes that tmux integration is required

### Future Implementation

Will integrate with tmux MCP tools:

```python
async def _execute_via_tmux(lab_id, device_name, command):
    # 1. Create session name
    session = f"cml_{lab_id}_{device_name}"
    
    # 2. Create or attach to session
    await tmux_create_session(session)
    
    # 3. Get console connection from CML
    node = await client.get_node_by_label(lab_id, device_name)
    console_url = node['console_url']
    
    # 4. Establish console connection in tmux
    await tmux_send_keys(session, f"telnet {console_url}")
    
    # 5. Wait for prompt
    await wait_for_prompt(session)
    
    # 6. Send command
    await tmux_send_keys(session, command)
    
    # 7. Capture output
    output = await tmux_capture_pane(session)
    
    return output
```

---

## Error Handling Strategy

### Layered Error Handling

```
1. Tool Level:
   - Catch all exceptions
   - Return error dict
   - Log details
   
2. Client Level:
   - HTTP errors
   - Authentication failures
   - API errors

3. Parser Level:
   - Parser not found
   - Parsing errors
   - Format errors

4. Validation Level:
   - Missing data
   - Unexpected states
   - Validation failures
```

### Error Response Format

```python
{
    "status": "error",
    "error": "Descriptive message",
    "context": {
        "device": "R1",
        "command": "show version"
    }
}
```

---

## Validation Logic Architecture

### Protocol Validation Flow

```
1. Map protocol → command
   OSPF → "show ip ospf neighbor"

2. Execute command
   Use execute_command tool

3. Check if parsed
   If yes: Extract neighbor data
   If no: Return raw for LLM

4. Validate states
   OSPF: Check for FULL
   BGP: Check for Established

5. Compare to expected
   If expected_state provided

6. Generate issues list
   Any neighbor not in correct state

7. Determine pass/fail
   Issues found = fail

8. Create summary
   Human-readable result
```

### Interface Validation Flow

```
1. Execute show interfaces
   Target specific or all

2. Parse output
   Extract interface list

3. Check status
   Operational: up/down
   Protocol: up/down

4. Check errors
   CRC, frame, overrun, etc.

5. Identify issues
   Down when should be up
   High error counts
   CRC errors present

6. Aggregate results
   Per-interface status
   Overall health

7. Return structured data
   With pass/fail status
```

---

## Performance Considerations

### Optimization Strategies

1. **Connection Reuse**
   - Single CML client instance
   - Token caching
   - HTTP connection pooling

2. **Parallel Execution**
   - Async operations
   - Concurrent device queries
   - Parallel validation checks

3. **Selective Parsing**
   - Only parse when requested
   - Cache parser lookups
   - Skip parser for known raw commands

4. **Output Truncation**
   - Limit captured output
   - Summarize large configs
   - Stream large responses

---

## Security Considerations

### Credential Management

- Environment variables for secrets
- No hardcoded credentials
- Token storage in memory only
- SSL/TLS for CML communication

### Input Validation

- Lab ID validation
- Device name sanitization
- Command injection prevention
- Path traversal protection

### Access Control

- Relies on CML authentication
- No additional auth layer
- User permissions from CML
- Read-only by default

---

## Extensibility Points

### Adding New Tools

```python
# 1. Create tool function
async def new_validation(lab_id, device_name):
    # Implementation
    pass

# 2. Add to tools/__init__.py
from .new_module import new_validation

# 3. Register in server.py
@mcp.tool()
async def validate_something(...):
    return await new_validation(...)
```

### Adding Protocol Support

```python
# In protocol_validation.py
PROTOCOL_COMMANDS["new_protocol"] = {
    "neighbors": "show new-protocol neighbors",
    "routes": "show ip route new-protocol"
}

# Add validation logic in _validate_parsed_protocol_data()
```

### Adding Parser Support

```python
# PyATS parsers are external
# Just need to update device mapping
DEVICE_TYPE_MAPPING["new_device"] = "device_os"
```

---

## Testing Strategy

### Unit Tests
- Individual tool functions
- Parser application
- Utility functions
- Error handling

### Integration Tests
- CML API interactions
- Tool orchestration
- Multi-device scenarios
- End-to-end flows

### Validation Tests
- Protocol detection
- State validation
- Issue identification
- Summary generation

---

## Deployment Models

### Development
```bash
uv run cml-pyats-validator
```

### Production
```bash
uvx cml-pyats-validator
```

### Docker (Future)
```bash
docker run -e CML_URL=... cml-pyats-validator
```

---

## Future Enhancements

### Phase 1: Core Functionality
- ✅ MCP server structure
- ✅ CML API integration
- ✅ PyATS parser integration
- ⏳ tmux console integration

### Phase 2: Advanced Features
- ⏳ Configuration deployment
- ⏳ Lab snapshot/restore
- ⏳ Performance metrics
- ⏳ Custom validation rules

### Phase 3: Multi-Vendor
- ⏳ Palo Alto parser support
- ⏳ FortiGate integration
- ⏳ Juniper support
- ⏳ Generic device handling

### Phase 4: Enterprise
- ⏳ RBAC integration
- ⏳ Audit logging
- ⏳ Compliance checking
- ⏳ Report generation

---

## Dependencies

### Core Dependencies
- **fastmcp**: MCP server framework
- **httpx**: Async HTTP client
- **pydantic**: Data validation
- **python-dotenv**: Environment config

### PyATS Dependencies
- **pyats**: Core framework
- **genie**: Parser library

### Optional Dependencies
- **tmux**: Console access (via MCP)
- **pytest**: Testing
- **black**: Code formatting
- **mypy**: Type checking

---

## Logging Strategy

### Log Levels
- **DEBUG**: Detailed execution flow
- **INFO**: Tool invocations, results
- **WARNING**: Parsing failures, retries
- **ERROR**: Exceptions, failures

### Log Format
```
2025-11-17 20:00:00 - cml_pyats_validator - INFO - Validating OSPF on R1
```

### Log Locations
- Development: stdout
- Production: configured file
- Claude Desktop: MCP logs

---

## Monitoring & Observability

### Metrics to Track
- Tool invocation counts
- Success/failure rates
- Parser hit/miss ratios
- Average execution times
- Error rates by type

### Health Checks
- CML API connectivity
- Authentication status
- Parser availability
- Memory usage

---

## Summary

The CML PyATS Validator follows a modular, layered architecture:

1. **Presentation Layer**: FastMCP tools
2. **Business Logic**: Validation modules
3. **Integration Layer**: CML client, PyATS helper
4. **Data Access**: CML API, console (future)

Key architectural principles:
- **Separation of Concerns**: Each module has clear responsibility
- **Fail Fast**: Errors caught early and reported clearly
- **Graceful Degradation**: Works without parsers
- **Extensibility**: Easy to add new validations
- **Educational Focus**: Clear, helpful output
