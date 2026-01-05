"""
Direct Answer Node for MonitoringMCP Subgraph
LLM generates direct response without tool execution
"""
import asyncio
from ..state_schemas import MonitoringSubgraphState
from ..helpers import truncate_for_logging, estimate_llm_tokens
from common.utils.logging_setup import setup_logging

logger = setup_logging(__name__)


async def direct_answer_node(state: MonitoringSubgraphState) -> MonitoringSubgraphState:
    """LLM generates direct response without tool execution"""
    try:
        query = state["query"]
        config = state["config"]
        
        llm_client = state.get("_llm_client")
        if not llm_client or not llm_client.is_functional():
            state["errors"] = ["LLM client not functional for direct answer"]
            state["failed_at_node"] = "direct_answer"
            state["error_type"] = "llm_unavailable"
            return state
        
        # Create direct answer prompt (max 100 tokens)
        direct_prompt = f"""User Query: "{query}"
This is a monitoring question that doesn't require live data.
Provide a helpful direct answer about monitoring concepts, tools, or guidance.
Be concise and practical."""

        # Log prompt details
        estimated_tokens = estimate_llm_tokens(direct_prompt)
        logger.debug(f"Direct answer prompt (~{estimated_tokens} tokens): {truncate_for_logging(direct_prompt)}")
        
        # Generate direct response
        try:
            response = await asyncio.wait_for(
                llm_client.get_completion(
                    direct_prompt,
                    temperature=config.get("llm_temperature", 0.7),
                    max_tokens=config.get("max_llm_tokens", 300)
                ),
                timeout=config.get("llm_timeout", 30)
            )
            
            final_response = response.strip()
            
            # Validate response quality
            if len(final_response) < 10:
                logger.warning("Generated response seems too short, may be low quality")
            
            state["final_response"] = final_response
            state["response_metadata"] = {
                "response_type": "direct_answer",
                "tools_used": [],
                "confidence": 0.8,
                "estimated_tokens": estimate_llm_tokens(final_response)
            }
            state["llm_decisions"]["direct_answer"] = "response_generated"
            
            logger.info(f"✅ Direct answer generated ({len(final_response)} chars)")
            logger.debug(f"Response preview: {truncate_for_logging(final_response)}")
            return state
            
        except asyncio.TimeoutError:
            logger.error(f"❌ Direct answer timeout after {config.get('llm_timeout', 30)}s")
            state["errors"] = ["Direct answer generation timeout"]
            state["failed_at_node"] = "direct_answer"
            state["error_type"] = "llm_timeout"
            return state
            
    except Exception as e:
        logger.error(f"❌ Direct answer error: {e}")
        state["errors"] = [f"Direct answer generation failed: {str(e)}"]
        state["failed_at_node"] = "direct_answer"
        state["error_type"] = "llm_error"
        return state