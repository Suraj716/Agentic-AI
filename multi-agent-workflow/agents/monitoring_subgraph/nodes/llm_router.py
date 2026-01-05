"""
LLM Router Node for MonitoringMCP Subgraph
LLM-driven routing decision with lightweight prompt
"""
import asyncio
from ..state_schemas import MonitoringSubgraphState
from ..helpers import truncate_for_logging, estimate_llm_tokens
from common.utils.logging_setup import setup_logging

logger = setup_logging(__name__)


async def llm_router_node(state: MonitoringSubgraphState) -> MonitoringSubgraphState:
    """LLM-driven routing decision with lightweight prompt"""
    try:
        query = state["query"]
        config = state["config"]
        
        logger.info(f"🔀 LLM Router processing query: {query[:50]}...")
        
        # Get LLM client from state
        llm_client = state.get("_llm_client")
        logger.info(f"🔀 LLM client available: {llm_client is not None}")
        
        if not llm_client:
            logger.error("❌ No LLM client in state")
            state["errors"] = ["LLM client not available in state"]
            state["failed_at_node"] = "llm_router"
            state["error_type"] = "llm_unavailable"
            return state
        
        if not llm_client.is_functional():
            logger.error("❌ LLM client not functional")
            state["errors"] = ["LLM client not functional for routing decision"]
            state["failed_at_node"] = "llm_router"
            state["error_type"] = "llm_unavailable"
            return state
        
        logger.info("✅ LLM client is functional, proceeding with routing")
        
        # Ensure LLM client is healthy before making the call
        try:
            await llm_client.ensure_healthy()
        except Exception as e:
            logger.error(f"❌ LLM client health check failed: {e}")
            state["errors"] = ["LLM client health check failed"]
            state["failed_at_node"] = "llm_router"
            state["error_type"] = "llm_unavailable"
            return state
        
        # Create lightweight routing prompt (max 50 tokens)
        router_prompt = f"""Query: "{query}"

Route this query to the appropriate handler:
- direct_answer: For questions that need explanations or guidance
- tool_needed: For requests that need data from monitoring tools
- unsupported: For queries outside monitoring scope

Respond with exactly one word: direct_answer, tool_needed, or unsupported"""

        # Log prompt details
        estimated_tokens = estimate_llm_tokens(router_prompt)
        logger.debug(f"Router prompt (~{estimated_tokens} tokens): {truncate_for_logging(router_prompt)}")
        
        logger.info("🧠 Calling LLM for routing decision...")
        
        # Get LLM decision with timeout
        try:
            decision = await asyncio.wait_for(
                llm_client.get_completion(
                    router_prompt, 
                    temperature=config.get("llm_temperature", 0.7),
                    max_tokens=10
                ),
                timeout=config.get("llm_timeout", 30)
            )
            
            logger.info(f"🧠 LLM router raw response: '{decision}'")
            
            route = decision.strip().lower()
            logger.info(f"🧠 LLM router processed response: '{route}'")
            
            # Validate route decision
            valid_routes = ["direct_answer", "tool_needed", "unsupported"]
            if route not in valid_routes:
                logger.warning(f"❌ Invalid route '{route}', defaulting to 'tool_needed' for data queries")
                route = "tool_needed"  # Default to tool_needed for monitoring queries
            
            state["route_decision"] = route
            state["llm_decisions"]["router"] = route
            
            logger.info(f"✅ LLM router final decision: {route}")
            return state
            
        except asyncio.TimeoutError:
            logger.error(f"❌ LLM router timeout after {config.get('llm_timeout', 30)}s")
            state["errors"] = ["LLM router timeout"]
            state["failed_at_node"] = "llm_router"
            state["error_type"] = "llm_timeout"
            return state
            
    except Exception as e:
        logger.error(f"❌ LLM router error: {e}")
        state["errors"] = [f"LLM routing failed: {str(e)}"]
        state["failed_at_node"] = "llm_router"
        state["error_type"] = "llm_error"
        return state