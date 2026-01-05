"""
State schemas for MonitoringMCP Subgraph
Contains all TypedDict definitions for state management
"""
from typing_extensions import TypedDict
from typing import Dict, Any, List, Optional
from core.state_schema import SupervisorState


class MonitoringSubgraphState(TypedDict):
    """State schema for the MonitoringMCP subgraph with LLM-driven decisions"""
    # Core request data
    query: str
    original_state: SupervisorState  # Reference to original supervisor state
    
    # LLM decision tracking
    route_decision: str  # "direct_answer", "tool_needed", "unsupported"
    llm_decisions: Dict[str, str]  # Track all LLM choices for debugging
    
    # Tool execution data
    selected_tools: List[Dict[str, Any]]  # Tools selected by LLM
    tool_parameters: Dict[str, Any]  # Parameters for tool execution
    tool_results: Dict[str, Any]  # Results from MCP tool execution
    raw_tool_results: Dict[str, Any]  # Raw unprocessed results from MCP tools for debugging/UI
    
    # Response data
    final_response: str  # Final formatted response
    response_metadata: Dict[str, Any]  # Response metadata and confidence
    
    # Error handling
    errors: List[str]  # List of errors encountered
    failed_at_node: Optional[str]  # Which node caused failure
    error_type: Optional[str]  # Type of error for categorization
    
    # Configuration
    config: Dict[str, Any]  # Runtime configuration for LLM, timeouts, etc.
    
    # Private client references for nodes (not user-visible)
    _llm_client: Any  # LLM client instance for nodes
    _mcp_client: Any  # MCP client instance for nodes


class NodeExecutionContext(TypedDict):
    """Context passed to each node for execution"""
    llm_client: Any  # LLM client instance
    mcp_client: Any  # MCP client instance
    config: Dict[str, Any]  # Configuration dictionary
    logger: Any  # Logger instance


class ToolExecutionResult(TypedDict):
    """Result from a single tool execution"""
    tool_name: str
    success: bool
    result: Optional[Dict[str, Any]]
    error: Optional[str]
    execution_time: float
    parameters: Dict[str, Any]


class SubgraphExecutionMetrics(TypedDict):
    """Metrics collected during subgraph execution"""
    total_execution_time: float
    node_execution_times: Dict[str, float]
    llm_calls_made: int
    llm_tokens_used: int
    tools_executed: int
    successful_tools: int
    failed_tools: int
    route_taken: str
    final_node: str