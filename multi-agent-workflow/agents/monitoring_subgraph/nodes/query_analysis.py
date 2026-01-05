"""
Query Analysis Node for MonitoringMCP Subgraph
Basic query parsing and preparation for LLM router
"""
from ..state_schemas import MonitoringSubgraphState
from common.utils.logging_setup import setup_logging

logger = setup_logging(__name__)


def query_analysis_node(state: MonitoringSubgraphState) -> MonitoringSubgraphState:
    """Basic query parsing and preparation for LLM router"""
    try:
        query = state["query"]
        
        # Basic query preprocessing
        query_lower = query.lower()
        query_words = query_lower.split()
        
        # Extract basic metadata for LLM router
        analysis_metadata = {
            "query_length": len(query),
            "word_count": len(query_words),
            "has_question_words": any(word in query_lower for word in ["what", "how", "when", "where", "why", "which"]),
            "has_action_words": any(word in query_lower for word in ["show", "list", "get", "fetch", "find", "search"]),
            "has_monitoring_terms": any(word in query_lower for word in ["dashboard", "metric", "alert", "log", "cpu", "memory"]),
            "query_type_hint": "data_request" if any(word in query_lower for word in ["show", "list", "get"]) else "information_request"
        }
        
        # Update existing tool_parameters or create new
        if "tool_parameters" not in state:
            state["tool_parameters"] = {}
        
        state["tool_parameters"]["analysis_metadata"] = analysis_metadata
        
        logger.info(f"✅ Query analysis completed: {analysis_metadata['query_type_hint']}")
        logger.debug(f"Analysis metadata: {analysis_metadata}")
        return state
        
    except Exception as e:
        logger.error(f"❌ Query analysis error: {e}")
        state["errors"] = [f"Query analysis failed: {str(e)}"]
        state["failed_at_node"] = "query_analysis"
        state["error_type"] = "analysis_error"
        return state