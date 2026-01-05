"""
MonitoringMCP Subgraph Package
Modular LLM-driven monitoring subgraph implementation
"""

# Configuration
from .config import (
    MonitoringSubgraphConfig,
    DEFAULT_CONFIG,
    FAST_CONFIG,
    COMPREHENSIVE_CONFIG,
    DEVELOPMENT_CONFIG
)

# State schemas
from .state_schemas import (
    MonitoringSubgraphState,
    NodeExecutionContext,
    ToolExecutionResult,
    SubgraphExecutionMetrics
)

# Edge conditions
from .edges import (
    route_condition,
    direct_answer_condition,
    tool_selection_condition,
    mcp_execution_condition,
    formatting_condition
)

# Subgraph builder
from .subgraph_builder import (
    build_monitoring_subgraph,
    prepare_subgraph_state,
    create_monitoring_subgraph,
    validate_subgraph_structure
)

# Helper functions
from .helpers import (
    parse_tool_selection,
    execute_single_tool,
    summarize_tool_results,
    validate_query,
    extract_query_metadata,
    format_execution_time,
    format_raw_tool_results_for_ui,
    format_raw_tool_results_for_logs
)

# Node implementations (for advanced usage)
from .nodes.entry_point import entry_point_node
from .nodes.query_analysis import query_analysis_node
from .nodes.llm_router import llm_router_node
from .nodes.direct_answer import direct_answer_node
from .nodes.tool_selection import tool_selection_llm_node
from .nodes.mcp_execute import mcp_execute_node
from .nodes.llm_formatter import llm_formatter_node

__version__ = "1.0.0"
__author__ = "AI Agent Team"
__description__ = "Modular LLM-driven monitoring subgraph for intelligent tool selection and execution"

# Main API - most users will only need these
__all__ = [
    # Core components
    "MonitoringSubgraphConfig",
    "MonitoringSubgraphState", 
    "build_monitoring_subgraph",
    "prepare_subgraph_state",
    "create_monitoring_subgraph",
    
    # Predefined configurations
    "DEFAULT_CONFIG",
    "FAST_CONFIG", 
    "COMPREHENSIVE_CONFIG",
    "DEVELOPMENT_CONFIG",
    
    # Utilities
    "validate_subgraph_structure",
    "format_execution_time"
]

# Advanced API - for customization and debugging
__all_advanced__ = [
    # All edge conditions
    "route_condition",
    "direct_answer_condition", 
    "tool_selection_condition",
    "mcp_execution_condition",
    "formatting_condition",
    
    # All node functions
    "entry_point_node",
    "query_analysis_node",
    "llm_router_node", 
    "direct_answer_node",
    "tool_selection_llm_node",
    "mcp_execute_node",
    "llm_formatter_node",
    
    # Helper functions
    "parse_tool_selection",
    "execute_single_tool", 
    "summarize_tool_results",
    "validate_query",
    "extract_query_metadata",
    "format_execution_time",
    "format_raw_tool_results_for_ui",
    "format_raw_tool_results_for_logs",
    
    # Additional schemas
    "NodeExecutionContext",
    "ToolExecutionResult", 
    "SubgraphExecutionMetrics"
]