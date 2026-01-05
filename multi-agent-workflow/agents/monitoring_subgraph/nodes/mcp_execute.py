"""
MCP Execute Node for MonitoringMCP Subgraph
Execute selected MCP tools with proper error handling
"""
import asyncio
from datetime import datetime
from ..state_schemas import MonitoringSubgraphState
from ..helpers import execute_single_tool, format_execution_time, format_raw_tool_results_for_logs
from common.utils.logging_setup import setup_logging

logger = setup_logging(__name__)


async def mcp_execute_node(state: MonitoringSubgraphState) -> MonitoringSubgraphState:
    """Execute selected MCP tools with proper error handling"""
    try:
        selected_tools = state["selected_tools"]
        config = state["config"]
        
        mcp_client = state.get("_mcp_client")
        if not mcp_client:
            state["errors"] = ["MCP client not available"]
            state["failed_at_node"] = "mcp_execute"
            state["error_type"] = "mcp_unavailable"
            return state
        
        if not selected_tools:
            state["errors"] = ["No tools selected for execution"]
            state["failed_at_node"] = "mcp_execute"
            state["error_type"] = "no_tools_selected"
            return state
        
        # Execute tools in parallel with timeout
        tool_results = {}
        raw_tool_results = {}  # Store raw results for debugging/UI
        execution_errors = []
        
        try:
            # Limit parallel execution based on config
            max_parallel = config.get("max_parallel_tools", 3)
            tools_to_execute = selected_tools[:max_parallel]
            
            logger.info(f"🔧 Executing {len(tools_to_execute)} tools in parallel")
            for t in tools_to_execute:
                name = t.get("tool_name")
                params = t.get("parameters", {})
                if name in ["execute_query", "execute_range_query"]:
                    logger.info(
                        "📤 Execution plan → %s query='%s' %s", name, params.get("query"),
                        f"range start={params.get('start')} end={params.get('end')} step={params.get('step')}" if name == "execute_range_query" else f"time={params.get('time','<none>')}"
                    )
                else:
                    logger.info("📤 Execution plan → %s params=%s", name, params)
            
            # Execute tools with timeout
            execution_tasks = []

            async def _fallback_wrapper(tool_info):
                """Execute static Python wrapper if MCP tool not available.

                Tries direct callable, then common LangChain tool invocation patterns.
                Provides richer error detail listing available attributes when missing.
                """
                import importlib, json as _json, inspect
                tool_name = tool_info.get("tool_name")
                params = tool_info.get("parameters", {})
                try:
                    monitoring_module = importlib.import_module("tools.monitoring_tools")
                except Exception as ex:
                    return {"error": f"monitoring_tools import failed: {ex}"}
                fn = getattr(monitoring_module, tool_name, None)
                if fn is None:
                    # Provide a hint of what is actually exported
                    exported = [a for a in dir(monitoring_module) if not a.startswith('_')]
                    return {"error": f"Fallback wrapper not found for {tool_name}", "available_exports": exported[:50]}
                try:
                    # LangChain @tool may return a Tool instance with .invoke or .run
                    if callable(fn):
                        raw = fn(**params) if params else fn()
                    elif hasattr(fn, 'run') and callable(getattr(fn, 'run')):
                        raw = fn.run(**params) if params else fn.run()
                    elif hasattr(fn, 'invoke') and callable(getattr(fn, 'invoke')):
                        raw = fn.invoke(params) if params else fn.invoke({})
                    else:
                        return {"error": f"Export for {tool_name} not directly callable", "type": str(type(fn))}
                    parsed = raw
                    if isinstance(raw, str):
                        try:
                            parsed = _json.loads(raw)
                        except Exception:
                            parsed = {"raw": raw}
                    return {"result": parsed, "tool": tool_name, "parameters": params}
                except Exception as ex:
                    # Include function signature if possible for debugging
                    sig = None
                    try:
                        sig = str(inspect.signature(fn))
                    except Exception:
                        sig = "<unavailable>"
                    return {"error": f"Wrapper execution failed: {ex}", "signature": sig}

            for tool_info in tools_to_execute:
                # Prefer MCP execution when attribute exists; else fallback
                if hasattr(mcp_client, tool_info.get("tool_name")):
                    task = execute_single_tool(mcp_client, tool_info, config.get("mcp_timeout", 45))
                else:
                    logger.debug(f"🔁 Falling back to local wrapper for tool {tool_info.get('tool_name')}")
                    task = _fallback_wrapper(tool_info)
                execution_tasks.append(task)
            
            # Wait for all tools with total timeout
            start_time = asyncio.get_event_loop().time()
            results = await asyncio.wait_for(
                asyncio.gather(*execution_tasks, return_exceptions=True),
                timeout=config.get("total_timeout", 90)
            )
            execution_time = asyncio.get_event_loop().time() - start_time
            
            # Process results
            successful_tools = []
            failed_tools = []
            
            for i, result in enumerate(results):
                tool_info = tools_to_execute[i]
                tool_name = tool_info["tool_name"]
                
                if isinstance(result, Exception):
                    error_msg = f"Tool {tool_name} failed: {str(result)}"
                    execution_errors.append(error_msg)
                    failed_tools.append(tool_name)
                    tool_results[tool_name] = {"error": str(result)}
                    raw_tool_results[tool_name] = {
                        "error": str(result),
                        "timestamp": datetime.now().isoformat(),
                        "parameters": tool_info.get("parameters", {})
                    }
                    logger.error(f"❌ {tool_name} exception", exc_info=True)
                else:
                    # Store raw result first (complete unprocessed data)
                    raw_tool_results[tool_name] = {
                        "result": result,
                        "timestamp": datetime.now().isoformat(),
                        "execution_time": execution_time
                    }
                    
                    if "error" in result:
                        execution_errors.append(f"Tool {tool_name}: {result['error']}")
                        failed_tools.append(tool_name)
                        raw_tool_results[tool_name]["error"] = result["error"]
                        raw_tool_results[tool_name]["parameters"] = tool_info.get("parameters", {})
                        logger.warning(
                            "❌ %s returned error: %s | params=%s", tool_name, result['error'], tool_info.get("parameters", {})
                        )
                    else:
                        successful_tools.append(tool_name)
                        logger.info(f"✅ {tool_name}: Success")
                    
                    tool_results[tool_name] = result
            
            # Check if any tools succeeded
            if not successful_tools:
                error_summary = f"All {len(tools_to_execute)} tools failed"
                state["errors"] = [error_summary] + execution_errors[:3]  # Limit error list
                state["failed_at_node"] = "mcp_execute"
                state["error_type"] = "all_tools_failed"
                logger.error(f"❌ {error_summary}")
                return state
            
            state["tool_results"] = tool_results
            state["raw_tool_results"] = raw_tool_results  # Store raw results for UI/debugging
            
            # Log execution summary
            success_rate = len(successful_tools) / len(tools_to_execute) * 100
            logger.info(f"✅ MCP execution completed in {format_execution_time(execution_time)}")
            logger.info(f"📊 Success rate: {success_rate:.1f}% ({len(successful_tools)}/{len(tools_to_execute)})")
            
            # Log detailed raw results for debugging
            logger.debug("🔍 Raw MCP Tool Results:")
            logger.debug(format_raw_tool_results_for_logs(raw_tool_results))
            
            if execution_errors:
                logger.warning(f"⚠️ Some tools failed: {failed_tools}")
                # Store non-critical errors for debugging but don't fail the node
                state["tool_parameters"]["execution_warnings"] = execution_errors[:5]
            
            return state
            
        except asyncio.TimeoutError:
            timeout_duration = config.get("total_timeout", 90)
            logger.error(f"❌ MCP execution timeout after {timeout_duration}s")
            state["errors"] = [f"MCP execution timeout after {timeout_duration} seconds"]
            state["failed_at_node"] = "mcp_execute"
            state["error_type"] = "mcp_timeout"
            return state
            
    except Exception as e:
        logger.error(f"❌ MCP execution error: {e}")
        state["errors"] = [f"MCP execution failed: {str(e)}"]
        state["failed_at_node"] = "mcp_execute"
        state["error_type"] = "mcp_execution_error"
        return state