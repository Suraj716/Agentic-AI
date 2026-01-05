"""
Subgraph Builder for MonitoringMCP Subgraph
Assembles all nodes and edges into a complete LangGraph
"""
from langgraph.graph import StateGraph, END
from .state_schemas import MonitoringSubgraphState
from .config import MonitoringSubgraphConfig
from .edges import (
    route_condition, direct_answer_condition, tool_selection_condition,
    mcp_execution_condition, formatting_condition, log_routing_decision
)
from .nodes.entry_point import entry_point_node
from .nodes.query_analysis import query_analysis_node
from .nodes.llm_router import llm_router_node
from .nodes.direct_answer import direct_answer_node
from .nodes.tool_selection import tool_selection_llm_node
from .nodes.mcp_execute import mcp_execute_node
from .nodes.llm_formatter import llm_formatter_node
from common.utils.logging_setup import setup_logging

logger = setup_logging(__name__)


def build_monitoring_subgraph(llm_client, mcp_client, config: MonitoringSubgraphConfig):
    """Build the MonitoringMCP subgraph with LLM-driven decisions"""
    try:
        logger.info("🏗️ Building MonitoringMCP subgraph...")
        
        # Validate inputs
        if not llm_client:
            raise ValueError("LLM client is required for subgraph")
        if not mcp_client:
            raise ValueError("MCP client is required for subgraph")
        if not isinstance(config, MonitoringSubgraphConfig):
            raise ValueError("Config must be MonitoringSubgraphConfig instance")
        
        # Validate configuration
        config.validate()
        
        # Create the subgraph
        subgraph = StateGraph(MonitoringSubgraphState)
        
        # Add all nodes
        logger.debug("Adding nodes to subgraph...")
        subgraph.add_node("entry_point", entry_point_node)
        subgraph.add_node("query_analysis", query_analysis_node)
        subgraph.add_node("llm_router", llm_router_node)
        subgraph.add_node("direct_answer", direct_answer_node)
        subgraph.add_node("tool_selection", tool_selection_llm_node)
        subgraph.add_node("mcp_execute", mcp_execute_node)
        subgraph.add_node("llm_formatter", llm_formatter_node)
        
        # Set entry point
        subgraph.set_entry_point("entry_point")
        logger.debug("Set entry point: entry_point")
        
        # Add sequential edges
        logger.debug("Adding sequential edges...")
        subgraph.add_edge("entry_point", "query_analysis")
        subgraph.add_edge("query_analysis", "llm_router")
        
        # Add conditional edges from LLM router
        logger.debug("Adding conditional edges from llm_router...")
        subgraph.add_conditional_edges(
            "llm_router",
            lambda state: _log_and_route(route_condition(state), "llm_router", route_condition(state)),
            {
                "direct_answer": "direct_answer",
                "tool_selection": "tool_selection",
                "ERROR_END": END
            }
        )
        
        # Add conditional edges from direct answer
        logger.debug("Adding conditional edges from direct_answer...")
        subgraph.add_conditional_edges(
            "direct_answer",
            lambda state: _log_and_route(direct_answer_condition(state), "direct_answer", direct_answer_condition(state)),
            {
                "SUCCESS_END": END,
                "ERROR_END": END
            }
        )
        
        # Add conditional edges from tool selection
        logger.debug("Adding conditional edges from tool_selection...")
        subgraph.add_conditional_edges(
            "tool_selection",
            lambda state: _log_and_route(tool_selection_condition(state), "tool_selection", tool_selection_condition(state)),
            {
                "mcp_execute": "mcp_execute",
                "ERROR_END": END
            }
        )
        
        # Add conditional edges from MCP execution
        logger.debug("Adding conditional edges from mcp_execute...")
        subgraph.add_conditional_edges(
            "mcp_execute",
            lambda state: _log_and_route(mcp_execution_condition(state), "mcp_execute", mcp_execution_condition(state)),
            {
                "llm_formatter": "llm_formatter",
                "ERROR_END": END
            }
        )
        
        # Add conditional edges from LLM formatter
        logger.debug("Adding conditional edges from llm_formatter...")
        subgraph.add_conditional_edges(
            "llm_formatter",
            lambda state: _log_and_route(formatting_condition(state), "llm_formatter", formatting_condition(state)),
            {
                "SUCCESS_END": END,
                "ERROR_END": END
            }
        )
        
        # Compile the subgraph
        logger.debug("Compiling subgraph...")
        compiled_subgraph = subgraph.compile()
        
        logger.info("✅ MonitoringMCP subgraph built successfully")
        logger.debug(f"Subgraph configuration: {config.to_dict()}")
        
        return compiled_subgraph
        
    except Exception as e:
        logger.error(f"❌ Failed to build monitoring subgraph: {e}")
        raise


def prepare_subgraph_state(supervisor_state, config: MonitoringSubgraphConfig, 
                          llm_client, mcp_client) -> MonitoringSubgraphState:
    """Prepare the initial state for the monitoring subgraph"""
    try:
        logger.debug("Preparing subgraph state...")
        
        # Validate inputs
        if not supervisor_state:
            raise ValueError("Supervisor state is required")
        if not isinstance(config, MonitoringSubgraphConfig):
            raise ValueError("Config must be MonitoringSubgraphConfig instance")
        
        # Create initial subgraph state
        initial_state = MonitoringSubgraphState(
            query="",  # Will be filled by entry_point_node
            original_state=supervisor_state,
            route_decision="",
            llm_decisions={},
            selected_tools=[],
            tool_parameters={},
            tool_results={},
            raw_tool_results={},  # Initialize raw results storage
            final_response="",
            response_metadata={},
            errors=[],
            failed_at_node=None,
            error_type=None,
            config=config.to_dict(),
            _llm_client=llm_client,  # Private reference for nodes
            _mcp_client=mcp_client   # Private reference for nodes
        )
        
        logger.debug("✅ Subgraph state prepared successfully")
        return initial_state
        
    except Exception as e:
        logger.error(f"❌ Failed to prepare subgraph state: {e}")
        raise


def _log_and_route(decision: str, from_node: str, to_node: str) -> str:
    """Helper function to log routing decisions"""
    log_routing_decision(from_node, to_node)
    return decision


def validate_subgraph_structure(compiled_subgraph) -> bool:
    """Validate the compiled subgraph structure"""
    try:
        # Basic validation - check if subgraph is compiled
        if not compiled_subgraph:
            logger.error("Subgraph is None or empty")
            return False
        
        # Check if it has the invoke method
        if not hasattr(compiled_subgraph, 'invoke') and not hasattr(compiled_subgraph, 'ainvoke'):
            logger.error("Subgraph missing invoke methods")
            return False
        
        logger.debug("✅ Subgraph structure validation passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Subgraph validation failed: {e}")
        return False


def get_subgraph_info(compiled_subgraph) -> dict:
    """Get information about the compiled subgraph"""
    try:
        info = {
            "type": str(type(compiled_subgraph)),
            "has_invoke": hasattr(compiled_subgraph, 'invoke'),
            "has_ainvoke": hasattr(compiled_subgraph, 'ainvoke'),
            "is_compiled": True  # If we got here, it's compiled
        }
        
        return info
        
    except Exception as e:
        logger.error(f"Failed to get subgraph info: {e}")
        return {"error": str(e)}


# Factory function for easy subgraph creation
def create_monitoring_subgraph(llm_client, mcp_client, config_dict: dict = None):
    """Factory function to create a monitoring subgraph with optional config"""
    try:
        # Create config from dict if provided
        if config_dict:
            config = MonitoringSubgraphConfig.from_dict(config_dict)
        else:
            config = MonitoringSubgraphConfig()
        
        # Build and return the subgraph
        return build_monitoring_subgraph(llm_client, mcp_client, config)
        
    except Exception as e:
        logger.error(f"❌ Failed to create monitoring subgraph: {e}")
        raise