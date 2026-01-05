"""
Helper functions for MonitoringMCP Subgraph
Contains utility functions used across different nodes
"""
import asyncio
from typing import Dict, Any, List
from common.utils.logging_setup import setup_logging

logger = setup_logging(__name__)


def parse_tool_selection(selection: str) -> List[Dict[str, Any]]:
    """Parse LLM tool selection into structured format"""
    tools = []
    try:
        lines = selection.strip().split('\n')
        for line in lines:
            if ':' in line:
                tool_name, params_str = line.split(':', 1)
                tool_name = tool_name.strip()
                
                # Parse parameters
                params = {}
                if params_str.strip():
                    param_pairs = params_str.split(',')
                    for pair in param_pairs:
                        if '=' in pair:
                            key, value = pair.split('=', 1)
                            params[key.strip()] = value.strip()
                
                tools.append({
                    "tool_name": tool_name,
                    "parameters": params
                })
    except Exception as e:
        logger.error(f"Failed to parse tool selection: {e}")
    
    return tools


async def execute_single_tool(mcp_client, tool_info: Dict[str, Any], timeout: int) -> Dict[str, Any]:
    """Execute a single MCP tool with timeout"""
    tool_name = tool_info["tool_name"]
    parameters = tool_info["parameters"]
    
    try:
        # Map tool names to MCP client methods
        if hasattr(mcp_client, tool_name):
            tool_method = getattr(mcp_client, tool_name)
            result = await asyncio.wait_for(tool_method(**parameters), timeout=timeout)
            return {"result": result, "tool": tool_name, "parameters": parameters}
        else:
            return {"error": f"Tool {tool_name} not available in MCP client"}
    except Exception as e:
        return {"error": f"Tool execution failed: {str(e)}"}


def summarize_tool_results(tool_results: Dict[str, Any]) -> str:
    """Summarize tool results for LLM formatting"""
    summary_parts = []
    for tool_name, result in tool_results.items():
        if "error" in result:
            summary_parts.append(f"{tool_name}: Error")
        else:
            data_size = len(str(result.get("result", "")))
            summary_parts.append(f"{tool_name}: {data_size} chars of data")
    
    return "; ".join(summary_parts)


def validate_query(query: str) -> bool:
    """Validate if query is suitable for processing"""
    if not query or not query.strip():
        return False
    
    # Check for minimum length
    if len(query.strip()) < 3:
        return False
    
    # Check for potentially harmful patterns
    harmful_patterns = ['__', 'exec', 'eval', 'import os', 'subprocess']
    query_lower = query.lower()
    if any(pattern in query_lower for pattern in harmful_patterns):
        return False
    
    return True


def extract_query_metadata(query: str) -> Dict[str, Any]:
    """Extract basic metadata from query for analysis"""
    query_lower = query.lower()
    query_words = query_lower.split()
    
    return {
        "query_length": len(query),
        "word_count": len(query_words),
        "has_question_words": any(word in query_lower for word in ["what", "how", "when", "where", "why", "which"]),
        "has_action_words": any(word in query_lower for word in ["show", "list", "get", "fetch", "find", "search"]),
        "has_monitoring_terms": any(word in query_lower for word in ["dashboard", "metric", "alert", "log", "cpu", "memory"]),
        "query_type_hint": "data_request" if any(word in query_lower for word in ["show", "list", "get"]) else "information_request",
        "complexity": "simple" if len(query_words) <= 5 else "complex" if len(query_words) <= 15 else "very_complex"
    }


def create_error_context(error: Exception, node_name: str, state: Dict[str, Any]) -> Dict[str, Any]:
    """Create standardized error context for debugging"""
    return {
        "error_type": type(error).__name__,
        "error_message": str(error),
        "failed_node": node_name,
        "query": state.get("query", "unknown"),
        "route_decision": state.get("route_decision", "unknown"),
        "llm_decisions": state.get("llm_decisions", {}),
        "config": state.get("config", {})
    }


def format_execution_time(seconds: float) -> str:
    """Format execution time for logging"""
    if seconds < 1:
        return f"{seconds*1000:.1f}ms"
    elif seconds < 60:
        return f"{seconds:.2f}s"
    else:
        minutes = int(seconds // 60)
        remaining_seconds = seconds % 60
        return f"{minutes}m {remaining_seconds:.1f}s"


def truncate_for_logging(text: str, max_length: int = 200) -> str:
    """Truncate text for logging purposes"""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."


def sanitize_config_for_logging(config: Dict[str, Any]) -> Dict[str, Any]:
    """Remove sensitive information from config for logging"""
    safe_config = config.copy()
    
    # Remove any potential sensitive keys
    sensitive_keys = ['api_key', 'password', 'token', 'secret', 'credentials']
    for key in list(safe_config.keys()):
        if any(sensitive in key.lower() for sensitive in sensitive_keys):
            safe_config[key] = "***REDACTED***"
    
    return safe_config


def estimate_llm_tokens(text: str) -> int:
    """Rough estimate of token count for a text"""
    # Very rough approximation: ~4 characters per token
    return len(text) // 4


def validate_tool_parameters(tool_name: str, parameters: Dict[str, Any]) -> bool:
    """Validate tool parameters before execution"""
    try:
        # Basic validation - ensure no harmful patterns
        for key, value in parameters.items():
            if not isinstance(key, str) or not isinstance(value, (str, int, float, bool)):
                return False
            
            # Check for potentially harmful values
            if isinstance(value, str):
                value_lower = value.lower()
                if any(pattern in value_lower for pattern in ['__', 'exec', 'eval', 'import']):
                    return False
        
        return True
    except Exception:
        return False


def format_raw_tool_results_for_ui(raw_results: Dict[str, Any]) -> Dict[str, Any]:
    """Format raw MCP tool results for UI display"""
    if not raw_results:
        return {}
    
    formatted_results = {}
    
    for tool_name, result in raw_results.items():
        if "error" in result:
            formatted_results[tool_name] = {
                "status": "error",
                "error": result["error"],
                "timestamp": result.get("timestamp", "unknown"),
                "execution_time": result.get("execution_time", 0)
            }
        else:
            # Extract key metrics for display
            raw_data = result.get("result", result)
            
            formatted_results[tool_name] = {
                "status": "success",
                "raw_data": raw_data,
                "data_size": len(str(raw_data)),
                "data_type": type(raw_data).__name__,
                "timestamp": result.get("timestamp", "unknown"),
                "execution_time": result.get("execution_time", 0),
                "summary": _generate_data_summary(raw_data)
            }
    
    return formatted_results


def format_raw_tool_results_for_logs(raw_results: Dict[str, Any]) -> str:
    """Format raw MCP tool results for detailed logging"""
    if not raw_results:
        return "No raw tool results available"
    
    log_parts = []
    
    for tool_name, result in raw_results.items():
        if "error" in result:
            log_parts.append(f"❌ {tool_name}: ERROR - {result['error']}")
        else:
            raw_data = result.get("result", result)
            data_size = len(str(raw_data))
            data_type = type(raw_data).__name__
            
            # Create a truncated preview for logs
            if isinstance(raw_data, dict):
                preview = f"Dict with {len(raw_data)} keys"
                if raw_data:
                    first_key = next(iter(raw_data.keys()))
                    preview += f" (first: {first_key})"
            elif isinstance(raw_data, list):
                preview = f"List with {len(raw_data)} items"
                if raw_data:
                    preview += f" (first: {type(raw_data[0]).__name__})"
            elif isinstance(raw_data, str):
                preview = raw_data[:100] + "..." if len(raw_data) > 100 else raw_data
            else:
                preview = str(raw_data)[:100]
            
            log_parts.append(f"✅ {tool_name}: {data_type} ({data_size} chars) - {preview}")
    
    return "\n".join(log_parts)


def _generate_data_summary(data: Any) -> str:
    """Generate a human-readable summary of the data"""
    if isinstance(data, dict):
        if not data:
            return "Empty dictionary"
        
        key_count = len(data)
        sample_keys = list(data.keys())[:3]
        summary = f"Dictionary with {key_count} keys"
        
        if sample_keys:
            summary += f" (includes: {', '.join(str(k) for k in sample_keys)}"
            if key_count > 3:
                summary += f" and {key_count - 3} more"
            summary += ")"
        
        return summary
        
    elif isinstance(data, list):
        if not data:
            return "Empty list"
        
        item_count = len(data)
        first_item_type = type(data[0]).__name__ if data else "unknown"
        
        return f"List with {item_count} {first_item_type} items"
        
    elif isinstance(data, str):
        length = len(data)
        if length > 100:
            return f"String ({length} characters): {data[:50]}..."
        return f"String ({length} characters): {data}"
        
    else:
        return f"{type(data).__name__}: {str(data)[:50]}"