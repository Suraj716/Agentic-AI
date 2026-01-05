"""
Edge Condition Functions for MonitoringMCP Subgraph
Contains all conditional routing logic for the graph
"""
from .state_schemas import MonitoringSubgraphState
from common.utils.logging_setup import setup_logging

logger = setup_logging(__name__)


def route_condition(state: MonitoringSubgraphState) -> str:
    """Determine routing based on LLM router decision"""
    if state.get("errors"):
        logger.debug("Route condition: ERROR_END (errors present)")
        return "ERROR_END"
    
    decision = state.get("route_decision", "").lower()
    
    if decision == "direct_answer":
        logger.debug("Route condition: direct_answer")
        return "direct_answer"
    elif decision == "tool_needed":
        logger.debug("Route condition: tool_selection")
        return "tool_selection"
    elif decision == "unsupported":
        logger.debug("Route condition: ERROR_END (unsupported query type)")
        return "ERROR_END"
    else:
        logger.debug(f"Route condition: ERROR_END (invalid decision: '{decision}')")
        return "ERROR_END"


def direct_answer_condition(state: MonitoringSubgraphState) -> str:
    """Check if direct answer was successful"""
    if state.get("errors"):
        logger.debug("Direct answer condition: ERROR_END (errors present)")
        return "ERROR_END"
    
    if state.get("final_response"):
        response_length = len(state["final_response"])
        logger.debug(f"Direct answer condition: SUCCESS_END (response: {response_length} chars)")
        return "SUCCESS_END"
    else:
        logger.debug("Direct answer condition: ERROR_END (no response)")
        return "ERROR_END"


def tool_selection_condition(state: MonitoringSubgraphState) -> str:
    """Check if tool selection was successful"""
    if state.get("errors"):
        logger.debug("Tool selection condition: ERROR_END (errors present)")
        return "ERROR_END"
    
    selected_tools = state.get("selected_tools", [])
    if selected_tools and len(selected_tools) > 0:
        tool_count = len(selected_tools)
        tool_names = [t.get("tool_name", "unknown") for t in selected_tools]
        logger.debug(f"Tool selection condition: mcp_execute ({tool_count} tools: {tool_names})")
        return "mcp_execute"
    else:
        logger.debug("Tool selection condition: ERROR_END (no tools selected)")
        return "ERROR_END"


def mcp_execution_condition(state: MonitoringSubgraphState) -> str:
    """Check if MCP execution was successful"""
    if state.get("errors"):
        logger.debug("MCP execution condition: ERROR_END (errors present)")
        return "ERROR_END"
    
    tool_results = state.get("tool_results", {})
    if tool_results:
        # Check if at least one tool succeeded
        successful_tools = [name for name, result in tool_results.items() if "error" not in result]
        if successful_tools:
            success_count = len(successful_tools)
            total_count = len(tool_results)
            logger.debug(f"MCP execution condition: llm_formatter ({success_count}/{total_count} tools successful)")
            return "llm_formatter"
        else:
            logger.debug("MCP execution condition: ERROR_END (all tools failed)")
            return "ERROR_END"
    else:
        logger.debug("MCP execution condition: ERROR_END (no tool results)")
        return "ERROR_END"


def formatting_condition(state: MonitoringSubgraphState) -> str:
    """Check if LLM formatting was successful"""
    if state.get("errors"):
        logger.debug("Formatting condition: ERROR_END (errors present)")
        return "ERROR_END"
    
    if state.get("final_response"):
        response_length = len(state["final_response"])
        confidence = state.get("response_metadata", {}).get("confidence", 0.0)
        logger.debug(f"Formatting condition: SUCCESS_END (response: {response_length} chars, confidence: {confidence:.2f})")
        return "SUCCESS_END"
    else:
        logger.debug("Formatting condition: ERROR_END (no final response)")
        return "ERROR_END"


def validate_state_for_routing(state: MonitoringSubgraphState, required_fields: list) -> bool:
    """Validate state has required fields before routing"""
    missing_fields = []
    for field in required_fields:
        if field not in state:
            missing_fields.append(field)
    
    if missing_fields:
        logger.error(f"State validation failed - missing fields: {missing_fields}")
        return False
    
    return True


def log_routing_decision(from_node: str, to_node: str, reason: str = "") -> None:
    """Log routing decisions for debugging"""
    if reason:
        logger.info(f"🔀 Routing: {from_node} → {to_node} ({reason})")
    else:
        logger.info(f"🔀 Routing: {from_node} → {to_node}")


def get_error_routing_reason(state: MonitoringSubgraphState) -> str:
    """Get human-readable reason for error routing"""
    errors = state.get("errors", [])
    error_type = state.get("error_type", "unknown")
    failed_node = state.get("failed_at_node", "unknown")
    
    if errors:
        primary_error = errors[0]
        return f"Error in {failed_node}: {primary_error[:100]}"
    else:
        return f"Error type: {error_type} in {failed_node}"


# Advanced routing conditions for complex scenarios

def should_retry_llm_call(state: MonitoringSubgraphState, node_name: str) -> bool:
    """Determine if an LLM call should be retried"""
    config = state.get("config", {})
    enable_retry = config.get("enable_tool_retry", False)
    
    if not enable_retry:
        return False
    
    # Check retry count for this node
    retry_key = f"{node_name}_retry_count"
    retry_count = state.get("tool_parameters", {}).get(retry_key, 0)
    max_retries = config.get("retry_attempts", 1)
    
    return retry_count < max_retries


def should_fallback_to_basic_response(state: MonitoringSubgraphState) -> bool:
    """Determine if should fallback to basic response instead of full error"""
    error_type = state.get("error_type", "")
    config = state.get("config", {})
    
    # Only fallback for timeout errors if configured
    if "timeout" in error_type and config.get("fallback_on_timeout", False):
        return True
    
    return False