"""
Entry Point Node for MonitoringMCP Subgraph
Validates request and extracts query from supervisor state
"""
from ..state_schemas import MonitoringSubgraphState
from ..helpers import validate_query, extract_query_metadata
from common.utils.logging_setup import setup_logging

logger = setup_logging(__name__)


def entry_point_node(state: MonitoringSubgraphState) -> MonitoringSubgraphState:
    """Entry point: Validate request and extract query"""
    try:
        # Extract query from original supervisor state
        original_state = state["original_state"]
        
        if isinstance(original_state, dict):
            messages = original_state.get("messages", [])
        else:
            messages = getattr(original_state, "messages", [])
        
        if not messages:
            state["errors"] = ["No messages found in request"]
            state["failed_at_node"] = "entry_point"
            state["error_type"] = "invalid_request"
            return state
        
        # Extract query from last message
        last_message = messages[-1]
        if hasattr(last_message, 'content'):
            query = last_message.content
        else:
            query = str(last_message)
        
        # Validate query
        if not validate_query(query):
            state["errors"] = ["Invalid or empty query received"]
            state["failed_at_node"] = "entry_point"
            state["error_type"] = "invalid_query"
            return state
        
        # Update state with validated query and metadata
        state["query"] = query.strip()
        state["llm_decisions"] = {}
        state["errors"] = []
        state["selected_tools"] = []
        state["tool_results"] = {}
        
        # Add query metadata for analysis
        query_metadata = extract_query_metadata(query.strip())
        if "tool_parameters" not in state:
            state["tool_parameters"] = {}
        state["tool_parameters"]["query_metadata"] = query_metadata
        
        logger.info(f"✅ Entry point validated query: {query[:100]}...")
        logger.debug(f"Query metadata: {query_metadata}")
        return state
        
    except Exception as e:
        logger.error(f"❌ Entry point error: {e}")
        state["errors"] = [f"Entry point validation failed: {str(e)}"]
        state["failed_at_node"] = "entry_point"
        state["error_type"] = "validation_error"
        return state