# Multi-Agent Workflow with Enhanced MCP Integration

A comprehensive multi-agent workflow system using LangGraph for intelligent query routing and specialized agent coordination with extensive MCP server integration.

## Architecture

### Core Components

- **SupervisorWorkflow**: LangGraph-based workflow orchestrator that intelligently routes queries to specialized agents
- **MultiAgentSupervisor**: Main coordinator class that manages the workflow and agent interactions
- **State Schema**: TypedDict definitions for workflow state management
- **Enhanced MCP Integration**: Comprehensive tool access from Grafana and Prometheus MCP servers

### Specialized Agents

1. **GeneralChat Agent** (`agents/general_chat.py`)
   - Handles greetings, casual conversation, basic math, and general knowledge
   - No specialized tools required
   - Provides friendly, conversational responses

2. **Enhanced MonitoringMCP Agent** (`agents/monitoring_mcp.py`)
   - **🔧 60+ specialized MCP tools** from Grafana and Prometheus servers
   - **📊 10+ tool categories**: Dashboard, Prometheus, Loki, Alerting, Incident, OnCall, Sift, Pyroscope, Admin, Navigation
   - **Dual MCP server integration**: Real Grafana MCP + Prometheus MCP connectivity
   - **Advanced capabilities**: Error pattern detection, performance profiling, incident management
   - **Intelligent tool selection**: Context-aware tool suggestions based on query intent

3. **SystemOps Agent** (`agents/system_ops.py`)
   - System health checks, service status, operational tasks
   - Infrastructure monitoring and troubleshooting guidance
   - Designed for operations teams

4. **HelpDocs Agent** (`agents/help_docs.py`)
   - Help requests, documentation, tutorials, and guidance
   - Step-by-step instructions and feature explanations
   - User support and onboarding assistance

### Enhanced MCP Features

#### Comprehensive Tool Categories

- **📊 Dashboard Management** (7 tools): Search, view, modify dashboards with context efficiency
- **📈 Prometheus Integration** (8 tools): Direct and Grafana-mediated PromQL queries
- **📋 Loki Log Analysis** (4 tools): LogQL queries, pattern detection, log statistics
- **🚨 Alerting System** (5 tools): Alert rules, contact points, alert group management
- **🎯 Incident Management** (4 tools): Create, track, update incidents
- **👥 OnCall Coordination** (7 tools): Schedules, shifts, team management
- **🔍 Sift Investigations** (5 tools): Advanced error pattern and performance analysis
- **⚡ Pyroscope Profiling** (4 tools): Performance profiling and optimization
- **🛠 Administration** (4 tools): Team/user management, deeplinks, assertions
- **📡 Direct Prometheus** (5 tools): Native Prometheus server access

#### Intelligent Tool Selection

- **Context-aware suggestions**: Automatic tool recommendation based on query content
- **Efficiency optimization**: Prioritizes low-context tools for exploration
- **Multi-server coordination**: Seamless integration between Grafana and Prometheus MCP servers
- **Performance categorization**: Tools marked by context impact (low/medium/high)

### Workflow Features

- **Intelligent Routing**: LLM-based query analysis with enhanced MCP tool context
- **Context Awareness**: Maintains conversation history and comprehensive tool usage tracking
- **Error Handling**: Graceful degradation with detailed MCP server status
- **Real Integration**: 60+ live MCP tools instead of mock responses
- **Enhanced Logging**: Comprehensive MCP response tracking and raw data display

## Enhanced Usage Examples

### Basic MCP Operations

```python
from multi_agent_workflow import get_multi_agent_supervisor, initialize_multi_agent_supervisor

# Initialize the enhanced supervisor
supervisor = initialize_multi_agent_supervisor()

# Dashboard operations
result = supervisor.process_query("Search for system dashboards")

# Prometheus queries  
result = supervisor.process_query("Execute PromQL: up")

# Log analysis
result = supervisor.process_query("Find error patterns in application logs")

# OnCall management
result = supervisor.process_query("Who is currently on-call for the platform team?")

# Incident management
result = supervisor.process_query("Create an incident for database connectivity issue")
```

### Advanced MCP Capabilities

```python
# Advanced analytics with Sift
result = supervisor.process_query("Detect slow requests in the last hour")

# Performance profiling
result = supervisor.process_query("Show me CPU profiling data")

# Alert management
result = supervisor.process_query("List all firing alerts")

# Direct Prometheus access
result = supervisor.process_query("Show me all Prometheus targets")
```

## Integration Architecture

The enhanced multi-agent workflow integrates with:

- **🔧 Grafana MCP Server**: 40+ tools for comprehensive Grafana ecosystem access
- **📊 Prometheus MCP Server**: 5+ tools for direct Prometheus monitoring
- **🎯 AgenticMCP Client**: Intelligent MCP client with conversation memory
- **📈 Common Utils**: Shared logging, configuration, and LLM clients
- **🔄 LangGraph**: Advanced workflow orchestration and state management

## Enhanced File Structure

```
multi-agent-workflow/
├── agents/
│   ├── monitoring_mcp.py       # 🔧 Enhanced with 60+ MCP tools
│   ├── enhanced_monitoring_mcp.py  # 📊 Alternative implementation
│   ├── general_chat.py         # Conversational agent
│   ├── system_ops.py           # Operations agent  
│   └── help_docs.py            # Documentation agent
├── core/
│   ├── supervisor_workflow.py  # 🔄 Enhanced LangGraph workflow
│   ├── state_schema.py         # Enhanced state management
│   └── agent_factory.py        # Agent creation utilities
├── ui/
│   ├── unified_ui.py           # 🎯 Single comprehensive interface
│   └── README.md               # UI documentation
└── tools/
    └── monitoring_tools.py     # Legacy tools (deprecated)
```
3. **Context Awareness**: Considers conversation history and recent topics

### Example Routing

- `"Hello there!"` → **GeneralChat**
- `"What metrics are available?"` → **MonitoringMCP**
- `"Check system health"` → **SystemOps**
- `"How do I use this?"` → **HelpDocs**

## Key Features

### Real Monitoring Integration

Unlike mock implementations, this workflow:
- Connects to actual Grafana dashboards
- Queries real Prometheus metrics
- Provides live monitoring insights
- Handles real API errors gracefully

### Conversation Memory

- Maintains conversation context across interactions
- Tracks agent performance and routing decisions
- Provides conversation summaries and topic extraction

### Error Resilience

- Graceful fallback when agents fail
- Timeout protection for long-running operations
- Clear error messages for troubleshooting

## Dependencies

- `langgraph`: Workflow orchestration
- `langchain-core`: LLM integration and message handling
- `common.utils`: Shared utilities from parent project
- `mcp-agent`: Real monitoring client integration

## Configuration

The workflow automatically inherits configuration from:
- Environment variables (`.env` files)
- Common utilities configuration
- MCP agent settings for monitoring integration

## Development

### Adding New Agents

1. Create agent file in `agents/` directory
2. Implement agent creation function following the pattern
3. Add agent to supervisor workflow in `supervisor_main.py`
4. Update routing logic in `core/supervisor_workflow.py`

### Extending Functionality

- Add new tools in `tools/` directory
- Extend state schema for additional context
- Enhance routing logic for better query understanding

## Migration from supervisor_agent

This structure replaces the `supervisor_agent/` directory with:
- Cleaner separation of concerns
- Better naming (MultiAgentSupervisor vs SupervisorAgent)
- Isolated package structure
- Enhanced documentation and organization

The functionality remains the same but with improved maintainability and clarity.