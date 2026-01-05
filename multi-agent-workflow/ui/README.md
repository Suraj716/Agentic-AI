# Multi-Agent Workflow UI Components

This directory contains the unified user interface for the Multi-Agent Workflow system.

## Unified UI

### unified_ui.py - Comprehensive Single-Page Interface
- **Purpose**: Complete interface combining all functionality in one streamlined application
- **Features**: 
  - **Chat Interface**: Enhanced conversational interaction with memory
  - **System Monitoring**: Real-time status of backend and agent systems
  - **Agent Capabilities**: Display of available agents and their specializations
  - **Conversation Management**: Session handling, topics, and history
  - **Settings Control**: Configuration options and preferences
  - **Raw MCP Data Display**: Detailed MCP response inspection with timestamps
  - **Follow-up Suggestions**: Contextual next action recommendations
  - **Quick Examples**: Pre-built queries for common use cases
- **Port**: 8501
- **Launch**: `./launch_unified.ps1`

## Quick Start

### Prerequisites
1. **Backend Running**: Ensure FastAPI backend is running on port 8080
2. **Virtual Environment**: Activate your Python virtual environment
3. **Dependencies**: Install requirements: `pip install -r requirements.txt`

### Launch the Unified UI
```powershell
./launch_unified.ps1
```
Then open: http://localhost:8501

#### Option 2: Enhanced Chat UI  
```powershell
./launch_chat.ps1
```
Then open: http://localhost:8502

#### Option 3: Manual Launch
```powershell
streamlit run streamlit_ui.py --server.port 8501
```

## Configuration

### Environment Variables
UI components use these configurations from `.env`:
- `STREAMLIT_PORT`: Main UI port (default: 8501)
- `CHAT_UI_PORT`: Chat UI port (default: 8502)  
- `UI_TIMEOUT`: Request timeout in seconds (default: 120)

### Backend Endpoints
UIs connect to these FastAPI endpoints:
- `http://localhost:8080/health` - Backend health check
- `http://localhost:8080/health` - Supervisor health check
- `http://localhost:8080/query` - Multi-agent queries
- `http://localhost:8080/agents` - Agent capabilities
- `http://localhost:8080/query` - Legacy queries (fallback)

## Features

### Multi-Agent Integration
- **Intelligent Routing**: Queries automatically routed to appropriate agents
- **Agent Information**: Display which agent handled each query
- **Capability Discovery**: Show available agents and their capabilities
- **Fallback Support**: Graceful degradation to legacy mode if supervisor unavailable

### Conversation Features
- **Memory**: Maintains conversation context across interactions
- **Topics**: Tracks current conversation topics
- **History**: Persistent chat history within session
- **Follow-ups**: AI-generated contextual follow-up questions

### System Monitoring
- **Health Checks**: Real-time backend and supervisor status
- **Error Handling**: Clear error messages and troubleshooting guidance
- **Timeout Protection**: Request timeouts prevent UI freezing
- **Status Indicators**: Visual status indicators for all system components

## Usage Examples

### Monitoring Queries
- "What dashboards are available?"
- "Show me system metrics"
- "Find network monitoring dashboards"
- "What Prometheus metrics exist?"

### General Conversation
- "Hello! What can you help me with?"
- "How do I use this system?"
- "What are the available features?"

### System Operations
- "Check system health"
- "What's the status of services?"
- "Are there any alerts?"

## Troubleshooting

### Backend Offline
If you see "Backend Offline":
1. Ensure FastAPI server is running: `python ./mcp-agent/agent/main_agentic.py`
2. Check port 8080 is not blocked
3. Verify network connectivity

### Supervisor Unavailable
If supervisor is offline:
- UI automatically falls back to legacy mode
- Limited to basic query processing
- Some advanced routing features unavailable

### Slow Responses
If queries are slow:
- Check network connectivity to monitoring systems
- Verify Grafana/Prometheus endpoints are accessible
- Consider reducing query complexity

### UI Not Loading
If Streamlit UI doesn't load:
1. Check Python virtual environment is activated
2. Verify Streamlit is installed: `pip install streamlit`
3. Ensure port is not in use by another application
4. Try a different port: `streamlit run ui/unified_ui.py --server.port 8503`

## Development

### Customizing the Unified UI
- Modify color themes in Streamlit configuration
- Adjust timeout values for your environment
- Add custom query examples
- Extend agent capability displays
- Customize raw data display formats

### Testing the UI
```powershell
# Test unified UI
streamlit run ui/unified_ui.py --server.port 8501

# Test with specific port
./launch_unified.ps1 -Port 8503

# Test with custom host
./launch_unified.ps1 -Host "0.0.0.0" -Port 8501
```

## Integration

### With Multi-Agent Workflow
The unified UI integrates seamlessly with:
- **MultiAgentSupervisor**: Main workflow orchestrator
- **Agent Routing**: Intelligent query routing
- **Conversation Memory**: Persistent conversation context
- **Real MCP Integration**: Live monitoring data with raw response display
- **Enhanced Logging**: Detailed workflow execution visibility

### With Backend Services
- **FastAPI Backend**: RESTful API integration
- **Grafana Integration**: Real dashboard data
- **Prometheus Integration**: Live metrics
- **Error Handling**: Graceful fallback mechanisms
- **Raw Data Access**: Complete MCP response inspection

## Files Overview

| File | Purpose | Port | Features |
|------|---------|------|----------|
| `unified_ui.py` | Comprehensive single-page interface | 8501 | All features in one UI |
| `launch_unified.ps1` | Launch script for unified UI | - | Status checks, easy startup |
| `__init__.py` | UI package definition | - | Module exports |
| `README.md` | Documentation | - | Usage and setup guide |

## Support

For issues or questions:
1. Check system status in UI sidebar
2. Review logs for error messages  
3. Verify backend connectivity
4. Consult main project documentation
5. Check configuration in `.env` file