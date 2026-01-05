"""
LLM Formatter Node for MonitoringMCP Subgraph
LLM formats results intelligently for user consumption
"""
import asyncio
from ..state_schemas import MonitoringSubgraphState
from ..helpers import summarize_tool_results, truncate_for_logging, estimate_llm_tokens
from common.utils.logging_setup import setup_logging

logger = setup_logging(__name__)


async def llm_formatter_node(state: MonitoringSubgraphState) -> MonitoringSubgraphState:
    """LLM formats results intelligently for user consumption"""
    try:
        query = state["query"]
        tool_results = state["tool_results"]
        config = state["config"]
        
        if not tool_results:
            state["errors"] = ["No tool results to format"]
            state["failed_at_node"] = "llm_formatter"
            state["error_type"] = "no_results"
            return state
        
        # Count successful vs failed tools for context
        successful_tools = [name for name, result in tool_results.items() if "error" not in result]
        failed_tools = [name for name, result in tool_results.items() if "error" in result]
        
        llm_client = state.get("_llm_client")
        if not llm_client or not llm_client.is_functional():
            state["errors"] = ["LLM client not functional for formatting"]
            state["failed_at_node"] = "llm_formatter"
            state["error_type"] = "llm_unavailable"
            return state
        
        # Prepare actual tool results for LLM (not just summary)
        results_for_llm = ""
        for tool_name, result in tool_results.items():
            if "error" not in result:
                # Include actual data for formatting, but truncate if too large
                result_data = result.get("result", "")
                if isinstance(result_data, (dict, list)):
                    result_data = str(result_data)
                
                # Truncate large results to prevent overwhelming the LLM
                if len(result_data) > 2000:
                    result_data = result_data[:2000] + "... [truncated]"
                
                results_for_llm += f"\n{tool_name} results:\n{result_data}\n"
            else:
                results_for_llm += f"\n{tool_name}: Error - {result.get('error', 'Unknown error')}\n"
        
        # Create formatting prompt with actual data
        max_length = config.get('max_response_length', 2000)
        format_prompt = f"""User Query: "{query}"

Tool Results:
{results_for_llm}

Task: Format the above ACTUAL tool results into a clear, helpful response for the user. 
Use ONLY the data provided above. Do NOT invent or add any information not present in the tool results.
Successful tools: {len(successful_tools)}, Failed: {len(failed_tools)}
Max {max_length} characters."""

        # Log prompt details
        estimated_tokens = estimate_llm_tokens(format_prompt)
        logger.debug(f"Formatting prompt (~{estimated_tokens} tokens): {truncate_for_logging(format_prompt)}")
        
        # Generate formatted response
        try:
            formatted_response = await asyncio.wait_for(
                llm_client.get_completion(
                    format_prompt,
                    temperature=config.get("llm_temperature", 0.7),
                    max_tokens=config.get("max_llm_tokens", 400)
                ),
                timeout=config.get("llm_timeout", 30)
            )
            
            state["final_response"] = formatted_response.strip()
            state["response_metadata"] = {
                "response_type": "formatted_tool_results",
                "tools_used": list(tool_results.keys()),
                "successful_tools": len(successful_tools),
                "failed_tools": len(failed_tools),
                "confidence": 0.9
            }
            state["llm_decisions"]["formatter"] = "formatted_successfully"
            
            logger.info("✅ LLM formatting completed successfully")
            return state
            
        except asyncio.TimeoutError:
            state["errors"] = ["Response formatting timeout"]
            state["failed_at_node"] = "llm_formatter"
            state["error_type"] = "llm_timeout"
            return state
            
    except Exception as e:
        logger.error(f"❌ LLM formatting error: {e}")
        state["errors"] = [f"Response formatting failed: {str(e)}"]
        state["failed_at_node"] = "llm_formatter"
        state["error_type"] = "formatting_error"
        return state