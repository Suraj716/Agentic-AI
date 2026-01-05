"""
Enhanced Monitoring MCP Agent - Intelligent LLM-driven tool selection and execution
Dynamically handles any monitoring query using comprehensive MCP tools from Grafana and Prometheus
"""
from typing import Dict, Any, List, Optional
import asyncio
import json
import sys
import os

# Add current directory to Python path for imports
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Add parent directory to access common modules
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from langchain_core.messages import HumanMessage, AIMessage
from core.state_schema import SupervisorState, AgentResponse
from core.agent_factory import create_agent
from common.utils.logging_setup import setup_logging
from tools.monitoring_tools import COMPREHENSIVE_MCP_TOOLS, get_comprehensive_tools_info, suggest_tools_for_monitoring_query
from common.utils.mcp_client import MCPGrafanaClient
from common.utils.llm_client import LLMClient

# Import modularized subgraph components
from .monitoring_subgraph import (
    MonitoringSubgraphConfig,
    MonitoringSubgraphState,
    build_monitoring_subgraph,
    prepare_subgraph_state,
    DEFAULT_CONFIG,
    FAST_CONFIG,
    COMPREHENSIVE_CONFIG,
    DEVELOPMENT_CONFIG
)

logger = setup_logging(__name__)


class IntelligentMonitoringAgent:
    """Intelligent Monitoring Agent with LLM-driven tool selection and execution"""
    
    def __init__(self, config: Optional[MonitoringSubgraphConfig] = None):
        """Initialize with comprehensive MCP tools, LLM client, and subgraph"""
        self.tools = COMPREHENSIVE_MCP_TOOLS
        self.mcp_client = None
        self.llm_client = None
        self.config = config or MonitoringSubgraphConfig()
        self.subgraph = None
        self._initialize_clients()
        self._initialize_subgraph()
    
    def _initialize_clients(self):
        """Initialize MCP and LLM clients for intelligent tool execution"""
        try:
            self.mcp_client = MCPGrafanaClient()
            self.llm_client = LLMClient()
            logger.info("✅ Intelligent MonitoringMCP agent initialized with LLM and MCP capabilities")
        except Exception as e:
            logger.error(f"❌ Failed to initialize clients: {e}")
            self.mcp_client = None
            self.llm_client = None
    
    def _initialize_subgraph(self):
        """Initialize the monitoring subgraph using modularized components"""
        try:
            if self.llm_client and self.llm_client.is_functional() and self.mcp_client:
                self.subgraph = build_monitoring_subgraph(
                    llm_client=self.llm_client,
                    mcp_client=self.mcp_client,
                    config=self.config
                )
                logger.info("✅ MonitoringMCP subgraph initialized successfully")
            else:
                missing = []
                if not self.llm_client:
                    missing.append("LLM client")
                elif not self.llm_client.is_functional():
                    missing.append("functional LLM client (check API key)")
                if not self.mcp_client:
                    missing.append("MCP client")
                logger.warning(f"⚠️ Cannot initialize subgraph - missing: {', '.join(missing)}")
                self.subgraph = None
        except Exception as e:
            logger.error(f"❌ Failed to initialize subgraph: {e}")
            self.subgraph = None
    
    async def _analyze_query_with_llm(self, query: str) -> Dict[str, Any]:
        """Use LLM to analyze the query and determine the best approach"""
        if not self.llm_client:
            logger.error("LLM client not available for query analysis")
            return {
                "intent": "performance_monitoring", 
                "relevant_categories": ["prometheus", "grafana"],
                "approach": "basic_query",
                "parameters": {"timerange": "30m"},
                "suggested_tools": ["query_prometheus", "search_dashboards"],
                "confidence": 0.5,
                "error": "LLM client not initialized - using intelligent query parsing"
            }
            
        tools_info = get_comprehensive_tools_info()
        
        analysis_prompt = f"""Analyze this monitoring query and determine the best approach:

Query: "{query}"

Available MCP Tools Categories:
{chr(10).join([f"- {cat}: {', '.join(tools[:3])}..." for cat, tools in tools_info['tools_by_category'].items()])}

Determine:
1. What is the user's intent? (performance_monitoring, alerting, dashboard_analysis, logs_analysis, etc.)
2. Which specific tool categories are most relevant?
3. What approach should be taken? (real_time_query, historical_analysis, dashboard_review, etc.)
4. Are there any specific parameters needed? (time ranges, metrics, thresholds)

Respond in JSON format:
{{
    "intent": "specific_intent",
    "relevant_categories": ["category1", "category2"],
    "approach": "query_approach", 
    "parameters": {{"timerange": "30m", "metrics": ["cpu", "memory"]}},
    "suggested_tools": ["tool1", "tool2"],
    "confidence": 0.9
}}"""

        try:
            response = await self.llm_client.get_completion(analysis_prompt)
            analysis = json.loads(response)
            logger.info(f"🧠 LLM Analysis: {analysis['intent']} with {analysis['confidence']} confidence")
            return analysis
        except Exception as e:
            logger.error(f"❌ Error in LLM analysis: {e}")
            # Provide intelligent query parsing based on query keywords
            return self._fallback_query_analysis(query)
    
    def _fallback_query_analysis(self, query: str) -> Dict[str, Any]:
        """Intelligent query parsing when LLM is not available"""
        query_lower = query.lower()
        
        # Analyze query for intent
        if any(keyword in query_lower for keyword in ["cpu", "memory", "disk", "utilization", "usage", "performance"]):
            return {
                "intent": "performance_monitoring",
                "relevant_categories": ["prometheus", "grafana"],
                "approach": "metrics_analysis",
                "parameters": {"timerange": "30m", "metrics": self._extract_metrics_from_query(query_lower)},
                "suggested_tools": ["query_prometheus", "search_dashboards"],
                "confidence": 0.7
            }
        elif any(keyword in query_lower for keyword in ["alert", "notification", "alarm", "incident"]):
            return {
                "intent": "alerting",
                "relevant_categories": ["alerting", "grafana"],
                "approach": "alert_analysis",
                "parameters": {"timerange": "1h"},
                "suggested_tools": ["get_alert_rules", "get_contact_points"],
                "confidence": 0.8
            }
        elif any(keyword in query_lower for keyword in ["log", "error", "debug", "trace"]):
            return {
                "intent": "logs_analysis",
                "relevant_categories": ["loki", "grafana"],
                "approach": "log_search",
                "parameters": {"timerange": "1h"},
                "suggested_tools": ["query_loki", "get_loki_labels"],
                "confidence": 0.7
            }
        elif any(keyword in query_lower for keyword in ["dashboard", "panel", "visualization"]):
            return {
                "intent": "dashboard_analysis",
                "relevant_categories": ["grafana"],
                "approach": "dashboard_review",
                "parameters": {},
                "suggested_tools": ["search_dashboards", "get_dashboard_summary"],
                "confidence": 0.8
            }
        else:
            return {
                "intent": "general_monitoring",
                "relevant_categories": ["prometheus", "grafana"],
                "approach": "overview_query",
                "parameters": {"timerange": "30m"},
                "suggested_tools": ["search_dashboards", "query_prometheus"],
                "confidence": 0.6
            }
    
    def _extract_metrics_from_query(self, query_lower: str) -> List[str]:
        """Extract specific metrics mentioned in the query"""
        metrics = []
        if "cpu" in query_lower:
            metrics.append("cpu")
        if any(keyword in query_lower for keyword in ["memory", "ram"]):
            metrics.append("memory")
        if "disk" in query_lower:
            metrics.append("disk")
        if any(keyword in query_lower for keyword in ["network", "bandwidth"]):
            metrics.append("network")
        return metrics if metrics else ["cpu", "memory"]
    
    async def _execute_monitoring_tools(self, analysis: Dict[str, Any], query: str) -> Dict[str, Any]:
        """Execute the appropriate MCP tools based on analysis"""
        results = {
            "success": True,
            "data": {},
            "analysis": analysis,
            "tools_executed": []
        }
        
        try:
            # Get suggested tools from analysis
            suggested_tools = analysis.get('suggested_tools', [])
            relevant_categories = analysis.get('relevant_categories', [])
            
            # If no specific tools suggested, use category-based selection
            if not suggested_tools and relevant_categories:
                tools_info = get_comprehensive_tools_info()
                for category in relevant_categories:
                    if category in tools_info['tools_by_category']:
                        suggested_tools.extend(tools_info['tools_by_category'][category][:2])
            
            # Execute tools dynamically
            for tool_name in suggested_tools[:3]:  # Limit to 3 tools for performance
                try:
                    logger.info(f"🔧 Executing MCP tool: {tool_name}")
                    tool_result = await self._execute_single_tool(tool_name, analysis.get('parameters', {}), analysis['intent'])
                    
                    if tool_result:
                        results['data'][tool_name] = tool_result
                        results['tools_executed'].append(tool_name)
                        logger.info(f"✅ Tool {tool_name} executed successfully")
                        
                except Exception as tool_error:
                    logger.error(f"❌ Error executing tool {tool_name}: {tool_error}")
                    results['data'][tool_name] = {"error": str(tool_error)}
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Error executing monitoring tools: {e}")
            return {
                "success": False,
                "error": str(e),
                "data": None
            }
    
    async def _execute_single_tool(self, tool_name: str, parameters: Dict[str, Any], intent: str) -> Optional[Dict[str, Any]]:
        """Execute a single MCP tool with real integration only"""
        try:
            if not self.mcp_client:
                logger.error(f"❌ MCP client not available for tool: {tool_name}")
                return {
                    "error": "MCP client not initialized - real monitoring data unavailable",
                    "tool": tool_name,
                    "status": "failed",
                    "recommendation": "Configure MCP servers (Grafana/Prometheus) for live data access"
                }
            
            # Execute real MCP tool only
            logger.info(f"🔧 Executing real MCP tool: {tool_name}")
            result = await self._execute_real_mcp_tool(tool_name, parameters)
            
            if result and not result.get('error'):
                logger.info(f"✅ Real MCP tool execution successful: {tool_name}")
                return {
                    "tool": tool_name,
                    "type": "real_mcp_execution",
                    "intent": intent,
                    "query_parameters": parameters,
                    "result": result,
                    "execution_status": "success",
                    "data_source": "live_monitoring_system"
                }
            else:
                error_msg = result.get('error', 'Unknown MCP execution error') if result else 'No response from MCP tool'
                logger.error(f"❌ MCP tool execution failed: {error_msg}")
                return {
                    "error": error_msg,
                    "tool": tool_name,
                    "status": "failed",
                    "recommendation": "Check MCP server connectivity and tool availability"
                }
            
        except Exception as e:
            logger.error(f"❌ Error in MCP tool execution {tool_name}: {e}")
            return {
                "error": str(e),
                "tool": tool_name,
                "status": "failed",
                "recommendation": "Verify MCP server configuration and network connectivity"
            }
    
    async def _execute_prometheus_tool(self, tool_name: str, parameters: Dict[str, Any], intent: str) -> Dict[str, Any]:
        """Execute Prometheus-related tools with pure MCP integration - no fallbacks"""
        try:
            if not self.mcp_client:
                logger.error(f"❌ MCP client not available for Prometheus tool: {tool_name}")
                return {
                    "error": "MCP client not initialized for Prometheus queries",
                    "tool": tool_name,
                    "status": "failed",
                    "recommendation": "Configure Prometheus MCP server connection and ensure it's running",
                    "suggested_action": "Verify Prometheus server is accessible and MCP integration is properly configured"
                }
            
            # Execute real MCP tool only - no simulation fallbacks
            logger.info(f"🔧 Executing real Prometheus MCP tool: {tool_name}")
            real_result = await self._execute_real_mcp_tool(tool_name, parameters)
            
            if real_result and not real_result.get('error'):
                logger.info(f"✅ Real Prometheus MCP tool execution successful: {tool_name}")
                return {
                    "tool": tool_name,
                    "type": "prometheus_query",
                    "intent": intent,
                    "query_parameters": parameters,
                    "result": real_result,
                    "execution_status": "real_mcp_execution",
                    "data_source": "live_prometheus"
                }
            else:
                error_msg = real_result.get('error', 'Unknown Prometheus MCP execution error') if real_result else 'No response from Prometheus MCP tool'
                logger.error(f"❌ Prometheus MCP tool execution failed: {error_msg}")
                return {
                    "error": error_msg,
                    "tool": tool_name,
                    "status": "failed",
                    "recommendation": "Check Prometheus server connectivity and MCP tool availability",
                    "suggested_action": "Verify Prometheus is running and MCP server has proper access credentials"
                }
            
        except Exception as e:
            logger.error(f"❌ Error in Prometheus MCP tool execution {tool_name}: {e}")
            return {
                "error": str(e),
                "tool": tool_name,
                "status": "failed",
                "recommendation": "Verify Prometheus MCP server configuration and network connectivity",
                "suggested_action": "Check logs for detailed error information and ensure Prometheus service is operational"
            }
    
    async def _execute_real_mcp_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Execute actual MCP tool calls with LLM-optimized parameters"""
        try:
            if not self.mcp_client:
                return {"error": "MCP client not available"}
            
            # Use LLM to optimize parameters for the specific tool
            optimized_params = await self._optimize_tool_parameters(tool_name, parameters)
            
            # Map tool names to actual MCP calls with optimized parameters
            if "query_prometheus" in tool_name.lower():
                query = await self._generate_promql_with_llm(optimized_params)
                result = await self.mcp_client.call_tool("query_prometheus", {
                    "query": query,
                    "time": optimized_params.get('time', 'now'),
                    "timeout": optimized_params.get('timeout', '30s'),
                    "step": optimized_params.get('step', '15s')
                })
                return result
                
            elif "search_dashboards" in tool_name.lower():
                search_query = await self._generate_dashboard_search_with_llm(optimized_params)
                result = await self.mcp_client.call_tool("search_dashboards", {
                    "query": search_query,
                    "tag": optimized_params.get('tags', []),
                    "limit": optimized_params.get('limit', 20),
                    "folderIds": optimized_params.get('folderIds', [])
                })
                return result
                
            elif "get_alert_rules" in tool_name.lower():
                result = await self.mcp_client.call_tool("get_alert_rules", {
                    "dashboard_uid": optimized_params.get('dashboard_uid', ''),
                    "panel_id": optimized_params.get('panel_id', ''),
                    "org_id": optimized_params.get('org_id', 1)
                })
                return result
                
            elif "query_loki" in tool_name.lower():
                log_query = await self._generate_loki_query_with_llm(optimized_params)
                result = await self.mcp_client.call_tool("query_loki", {
                    "query": log_query,
                    "limit": optimized_params.get('limit', 1000),
                    "start": optimized_params.get('start', '1h'),
                    "end": optimized_params.get('end', 'now'),
                    "direction": optimized_params.get('direction', 'backward')
                })
                return result
                
            elif "get_dashboard" in tool_name.lower():
                result = await self.mcp_client.call_tool("get_dashboard", {
                    "uid": optimized_params.get('uid', ''),
                    "slug": optimized_params.get('slug', ''),
                    "version": optimized_params.get('version', 0)
                })
                return result
                
            elif "get_datasources" in tool_name.lower():
                result = await self.mcp_client.call_tool("get_datasources", {
                    "org_id": optimized_params.get('org_id', 1)
                })
                return result
                
            else:
                # Generic MCP tool call with optimized parameters
                result = await self.mcp_client.call_tool(tool_name, optimized_params)
                return result
                
        except Exception as e:
            logger.error(f"❌ Real MCP tool execution failed for {tool_name}: {e}")
            return {"error": str(e), "tool": tool_name}
    
    async def _optimize_tool_parameters(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Use LLM to optimize tool parameters for better results"""
        if not self.llm_client:
            logger.warning("LLM client not available for parameter optimization")
            return parameters
        
        optimization_prompt = f"""Optimize the parameters for executing MCP tool '{tool_name}' based on monitoring best practices:

Current Parameters: {json.dumps(parameters, indent=2)}

Tool: {tool_name}

Instructions:
1. For Prometheus queries: Suggest optimal time ranges, step intervals, and query optimizations
2. For Grafana searches: Recommend relevant tags, search terms, and limits
3. For Loki queries: Optimize log query syntax and time windows
4. For dashboard operations: Suggest appropriate filters and options

Return optimized parameters in JSON format with explanations:
{{
    "optimized_parameters": {{
        "param1": "value1",
        "param2": "value2"
    }},
    "optimizations_applied": [
        "explanation1",
        "explanation2"
    ],
    "reasoning": "Brief explanation of optimization strategy"
}}"""

        try:
            response = await self.llm_client.get_completion(optimization_prompt)
            optimization_result = json.loads(response)
            
            optimized_params = optimization_result.get('optimized_parameters', parameters)
            optimizations = optimization_result.get('optimizations_applied', [])
            
            logger.info(f"🧠 LLM optimized parameters for {tool_name}: {optimizations}")
            return optimized_params
            
        except Exception as e:
            logger.error(f"❌ Error in LLM parameter optimization: {e}")
            return parameters
    
    async def _generate_promql_with_llm(self, parameters: Dict[str, Any]) -> str:
        """Use LLM to generate optimized PromQL queries"""
        if not self.llm_client:
            return self._build_promql_query(parameters)
        
        promql_prompt = f"""Generate an optimized PromQL query based on these parameters:

Parameters: {json.dumps(parameters, indent=2)}

Requirements:
1. Create efficient PromQL query for the specified metrics
2. Use appropriate time ranges and aggregation functions
3. Include proper labeling and filtering
4. Optimize for performance and accuracy

Metrics requested: {parameters.get('metrics', ['cpu', 'memory'])}
Time range: {parameters.get('timerange', '30m')}
Intent: {parameters.get('intent', 'performance_monitoring')}

Return only the PromQL query string, optimized for production use."""

        try:
            query = await self.llm_client.get_completion(promql_prompt)
            logger.info(f"🧠 LLM generated PromQL query: {query}")
            return query.strip()
        except Exception as e:
            logger.error(f"❌ Error generating PromQL with LLM: {e}")
            return self._build_promql_query(parameters)
    
    async def _generate_dashboard_search_with_llm(self, parameters: Dict[str, Any]) -> str:
        """Use LLM to generate optimized dashboard search queries"""
        if not self.llm_client:
            return parameters.get('search_query', '')
        
        search_prompt = f"""Generate an optimized Grafana dashboard search query:

Parameters: {json.dumps(parameters, indent=2)}

Intent: {parameters.get('intent', 'general')}
Context: User is looking for monitoring dashboards

Generate search terms that will find relevant dashboards for the user's monitoring needs.
Return only the search query string, optimized to find the most relevant dashboards."""

        try:
            search_query = await self.llm_client.get_completion(search_prompt)
            logger.info(f"🧠 LLM generated dashboard search: {search_query}")
            return search_query.strip()
        except Exception as e:
            logger.error(f"❌ Error generating dashboard search with LLM: {e}")
            return parameters.get('search_query', '')
    
    async def _generate_loki_query_with_llm(self, parameters: Dict[str, Any]) -> str:
        """Use LLM to generate optimized Loki queries"""
        if not self.llm_client:
            return self._build_loki_query(parameters)
        
        loki_prompt = f"""Generate an optimized Loki log query:

Parameters: {json.dumps(parameters, indent=2)}

Requirements:
1. Create efficient LogQL query for log analysis
2. Use appropriate filters and parsers
3. Include relevant log levels and patterns
4. Optimize for the specified intent

Intent: {parameters.get('intent', 'logs_analysis')}
Time range: {parameters.get('timerange', '1h')}

Return only the LogQL query string, optimized for log analysis."""

        try:
            query = await self.llm_client.get_completion(loki_prompt)
            logger.info(f"🧠 LLM generated Loki query: {query}")
            return query.strip()
        except Exception as e:
            logger.error(f"❌ Error generating Loki query with LLM: {e}")
            return self._build_loki_query(parameters)
    
    def _build_promql_query(self, parameters: Dict[str, Any]) -> str:
        """Build dynamic PromQL queries based on intent and metrics"""
        metrics = parameters.get('metrics', ['cpu'])
        timerange = parameters.get('timerange', '30m')
        
        # Build intelligent queries based on metrics
        if 'cpu' in metrics:
            return f'100 - (avg(irate(node_cpu_seconds_total{{mode="idle"}}[5m])) * 100)[{timerange}:]'
        elif 'memory' in metrics:
            return f'(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100[{timerange}:]'
        elif 'disk' in metrics:
            return f'100 - ((node_filesystem_avail_bytes / node_filesystem_size_bytes) * 100)[{timerange}:]'
        else:
            # Generic system metrics
            return f'up{{job=~".*"}}[{timerange}:]'
    
    def _build_loki_query(self, parameters: Dict[str, Any]) -> str:
        """Build dynamic Loki queries based on parameters"""
        intent = parameters.get('intent', 'general')
        timerange = parameters.get('timerange', '1h')
        
        if intent == 'logs_analysis':
            return f'{{job=~".*"}} |= "ERROR" or "WARN" | json | line_format "{{.timestamp}} {{.level}} {{.message}}"'
        else:
            return f'{{job=~".*"}}'
    
    async def _execute_grafana_tool(self, tool_name: str, parameters: Dict[str, Any], intent: str) -> Dict[str, Any]:
        """Execute Grafana-related tools with pure MCP integration - no fallbacks"""
        try:
            if not self.mcp_client:
                logger.error(f"❌ MCP client not available for Grafana tool: {tool_name}")
                return {
                    "error": "MCP client not initialized for Grafana operations",
                    "tool": tool_name,
                    "status": "failed",
                    "recommendation": "Configure Grafana MCP server connection and ensure it's running",
                    "suggested_action": "Verify Grafana server is accessible and MCP integration is properly configured"
                }
            
            # Execute real MCP tool only - no simulation fallbacks
            logger.info(f"🔧 Executing real Grafana MCP tool: {tool_name}")
            real_result = await self._execute_real_mcp_tool(tool_name, parameters)
            
            if real_result and not real_result.get('error'):
                logger.info(f"✅ Real Grafana MCP tool execution successful: {tool_name}")
                return {
                    "tool": tool_name,
                    "type": "grafana_dashboard",
                    "intent": intent,
                    "query_parameters": parameters,
                    "result": real_result,
                    "execution_status": "real_mcp_execution",
                    "data_source": "live_grafana"
                }
            else:
                error_msg = real_result.get('error', 'Unknown Grafana MCP execution error') if real_result else 'No response from Grafana MCP tool'
                logger.error(f"❌ Grafana MCP tool execution failed: {error_msg}")
                return {
                    "error": error_msg,
                    "tool": tool_name,
                    "status": "failed",
                    "recommendation": "Check Grafana server connectivity and MCP tool availability",
                    "suggested_action": "Verify Grafana is running and MCP server has proper access credentials"
                }
            
        except Exception as e:
            logger.error(f"❌ Error in Grafana MCP tool execution {tool_name}: {e}")
            return {
                "error": str(e),
                "tool": tool_name,
                "status": "failed",
                "recommendation": "Verify Grafana MCP server configuration and network connectivity",
                "suggested_action": "Check logs for detailed error information and ensure Grafana service is operational"
            }
    
    async def _execute_alert_tool(self, tool_name: str, parameters: Dict[str, Any], intent: str) -> Dict[str, Any]:
        """Execute alert-related tools with pure MCP integration - no fallbacks"""
        try:
            if not self.mcp_client:
                logger.error(f"❌ MCP client not available for alert tool: {tool_name}")
                return {
                    "error": "MCP client not initialized for alert operations",
                    "tool": tool_name,
                    "status": "failed",
                    "recommendation": "Configure alert management MCP server connection",
                    "suggested_action": "Verify alert management system is accessible via MCP"
                }
            
            # Execute real MCP tool only - no simulation fallbacks
            logger.info(f"🔧 Executing real alert MCP tool: {tool_name}")
            real_result = await self._execute_real_mcp_tool(tool_name, parameters)
            
            if real_result and not real_result.get('error'):
                logger.info(f"✅ Real alert MCP tool execution successful: {tool_name}")
                return {
                    "tool": tool_name,
                    "type": "alert_management",
                    "intent": intent,
                    "query_parameters": parameters,
                    "result": real_result,
                    "execution_status": "real_mcp_execution",
                    "data_source": "live_alert_system"
                }
            else:
                error_msg = real_result.get('error', 'Unknown alert MCP execution error') if real_result else 'No response from alert MCP tool'
                logger.error(f"❌ Alert MCP tool execution failed: {error_msg}")
                return {
                    "error": error_msg,
                    "tool": tool_name,
                    "status": "failed",
                    "recommendation": "Check alert management system connectivity and MCP tool availability",
                    "suggested_action": "Verify alert rules and notification systems are properly configured"
                }
            
        except Exception as e:
            logger.error(f"❌ Error in alert MCP tool execution {tool_name}: {e}")
            return {
                "error": str(e),
                "tool": tool_name,
                "status": "failed",
                "recommendation": "Verify alert management MCP server configuration",
                "suggested_action": "Check alert system logs and ensure proper MCP integration"
            }
    
    async def _execute_log_tool(self, tool_name: str, parameters: Dict[str, Any], intent: str) -> Dict[str, Any]:
        """Execute log-related tools with pure MCP integration - no fallbacks"""
        try:
            if not self.mcp_client:
                logger.error(f"❌ MCP client not available for log tool: {tool_name}")
                return {
                    "error": "MCP client not initialized for log operations",
                    "tool": tool_name,
                    "status": "failed",
                    "recommendation": "Configure Loki/log management MCP server connection",
                    "suggested_action": "Verify log aggregation system is accessible via MCP"
                }
            
            # Execute real MCP tool only - no simulation fallbacks
            logger.info(f"🔧 Executing real log MCP tool: {tool_name}")
            real_result = await self._execute_real_mcp_tool(tool_name, parameters)
            
            if real_result and not real_result.get('error'):
                logger.info(f"✅ Real log MCP tool execution successful: {tool_name}")
                return {
                    "tool": tool_name,
                    "type": "log_analysis",
                    "intent": intent,
                    "query_parameters": parameters,
                    "result": real_result,
                    "execution_status": "real_mcp_execution",
                    "data_source": "live_log_system"
                }
            else:
                error_msg = real_result.get('error', 'Unknown log MCP execution error') if real_result else 'No response from log MCP tool'
                logger.error(f"❌ Log MCP tool execution failed: {error_msg}")
                return {
                    "error": error_msg,
                    "tool": tool_name,
                    "status": "failed",
                    "recommendation": "Check log management system connectivity and MCP tool availability",
                    "suggested_action": "Verify Loki or log aggregation service is properly configured"
                }
            
        except Exception as e:
            logger.error(f"❌ Error in log MCP tool execution {tool_name}: {e}")
            return {
                "error": str(e),
                "tool": tool_name,
                "status": "failed",
                "recommendation": "Verify log management MCP server configuration",
                "suggested_action": "Check log system connectivity and ensure proper MCP integration"
            }
    
    async def _execute_generic_tool(self, tool_name: str, parameters: Dict[str, Any], intent: str) -> Dict[str, Any]:
        """Execute generic monitoring tools with pure MCP integration - no fallbacks"""
        try:
            if not self.mcp_client:
                logger.error(f"❌ MCP client not available for generic tool: {tool_name}")
                return {
                    "error": "MCP client not initialized for generic monitoring operations",
                    "tool": tool_name,
                    "status": "failed",
                    "recommendation": "Configure monitoring MCP server connections",
                    "suggested_action": "Verify monitoring systems are accessible via MCP integration"
                }
            
            # Execute real MCP tool only - no simulation fallbacks
            logger.info(f"🔧 Executing real generic MCP tool: {tool_name}")
            real_result = await self._execute_real_mcp_tool(tool_name, parameters)
            
            if real_result and not real_result.get('error'):
                logger.info(f"✅ Real generic MCP tool execution successful: {tool_name}")
                return {
                    "tool": tool_name,
                    "type": "generic_monitoring",
                    "intent": intent,
                    "query_parameters": parameters,
                    "result": real_result,
                    "execution_status": "real_mcp_execution",
                    "data_source": "live_monitoring_system"
                }
            else:
                error_msg = real_result.get('error', 'Unknown generic MCP execution error') if real_result else 'No response from generic MCP tool'
                logger.error(f"❌ Generic MCP tool execution failed: {error_msg}")
                return {
                    "error": error_msg,
                    "tool": tool_name,
                    "status": "failed",
                    "recommendation": "Check monitoring system connectivity and MCP tool availability",
                    "suggested_action": "Verify monitoring services are properly configured and accessible"
                }
            
        except Exception as e:
            logger.error(f"❌ Error in generic MCP tool execution {tool_name}: {e}")
            return {
                "error": str(e),
                "tool": tool_name,
                "status": "failed",
                "recommendation": "Verify monitoring MCP server configuration",
                "suggested_action": "Check monitoring system logs and ensure proper MCP integration"
            }
    
    async def _generate_intelligent_response(self, analysis: Dict[str, Any], execution_results: Dict[str, Any], original_query: str) -> str:
        """Generate an intelligent response based on analysis and execution results"""
        if not self.llm_client:
            return self._generate_structured_response(analysis, execution_results, original_query)
            
        response_prompt = f"""Generate a comprehensive monitoring response based on the following:

Original Query: "{original_query}"

Analysis Results:
- Intent: {analysis.get('intent', 'unknown')}
- Confidence: {analysis.get('confidence', 0.0)}
- Tools Executed: {execution_results.get('tools_executed', [])}

Execution Results:
{json.dumps(execution_results.get('data', {}), indent=2)}

Instructions:
1. Provide a clear summary of what was found
2. Highlight any important metrics, alerts, or issues
3. Suggest actionable next steps if relevant
4. Be specific about the data sources and tools used
5. If there are errors, explain them clearly and suggest alternatives

Generate a professional monitoring report that directly addresses the user's query."""

        try:
            response = await self.llm_client.get_completion(response_prompt)
            logger.info("🧠 Generated intelligent response using LLM")
            return response
        except Exception as e:
            logger.error(f"❌ Error generating LLM response: {e}")
            return self._generate_structured_response(analysis, execution_results, original_query)
    
    def _generate_structured_response(self, analysis: Dict[str, Any], execution_results: Dict[str, Any], original_query: str) -> str:
        """Generate a structured response when LLM is not available"""
        intent = analysis.get('intent', 'unknown')
        tools_executed = execution_results.get('tools_executed', [])
        data = execution_results.get('data', {})
        
        # Create response based on intent and data
        response_parts = [
            f"📊 **Monitoring Analysis for:** {original_query}",
            "",
            f"🎯 **Intent Detected:** {intent.replace('_', ' ').title()}",
            f"🔧 **Tools Executed:** {', '.join(tools_executed) if tools_executed else 'None'}",
            ""
        ]
        
        # Add specific findings based on intent and data
        if intent == "performance_monitoring" and data:
            response_parts.extend(self._format_performance_data(data))
        elif intent == "alerting" and data:
            response_parts.extend(self._format_alert_data(data))
        elif intent == "logs_analysis" and data:
            response_parts.extend(self._format_log_data(data))
        elif intent == "dashboard_analysis" and data:
            response_parts.extend(self._format_dashboard_data(data))
        else:
            response_parts.extend(self._format_generic_data(data))
        
        response_parts.extend([
            "",
            "**Next Steps:**",
            "- Review detailed metrics in Grafana dashboards",
            "- Set up additional monitoring if needed",
            "- Check for any anomalies or trends",
            "",
            "*This analysis was performed using dynamic MCP tool execution based on your query.*"
        ])
        
        return "\n".join(response_parts)
    
    def _format_performance_data(self, data: Dict[str, Any]) -> List[str]:
        """Format performance monitoring data"""
        formatted = ["**Performance Metrics:**"]
        
        for tool, result in data.items():
            if 'prometheus' in tool.lower() and 'result' in result:
                prometheus_data = result['result'].get('data', {})
                if 'result' in prometheus_data:
                    for metric_data in prometheus_data['result']:
                        metric_name = metric_data.get('metric', {}).get('__name__', 'Unknown')
                        values = metric_data.get('values', [])
                        if values:
                            latest_value = values[-1][1] if len(values[-1]) > 1 else 'N/A'
                            formatted.append(f"• {metric_name}: {latest_value}%")
                            
        return formatted
    
    def _format_alert_data(self, data: Dict[str, Any]) -> List[str]:
        """Format alert data"""
        formatted = ["**Alert Status:**"]
        
        for tool, result in data.items():
            if 'alert' in tool.lower() and 'result' in result:
                alert_result = result['result']
                active_count = alert_result.get('active_alerts', 0)
                formatted.append(f"• Active Alerts: {active_count}")
                
                alerts = alert_result.get('alerts', [])
                for alert in alerts:
                    status_icon = "🔥" if alert['status'] == 'firing' else "✅"
                    formatted.append(f"  {status_icon} {alert['name']} ({alert['severity']})")
                    
        return formatted
    
    def _format_log_data(self, data: Dict[str, Any]) -> List[str]:
        """Format log analysis data"""
        formatted = ["**Log Analysis:**"]
        
        for tool, result in data.items():
            if 'log' in tool.lower() and 'result' in result:
                log_result = result['result']
                formatted.append(f"• Total Log Entries: {log_result.get('log_entries', 0)}")
                formatted.append(f"• Errors: {log_result.get('error_count', 0)}")
                formatted.append(f"• Warnings: {log_result.get('warning_count', 0)}")
                
                recent_errors = log_result.get('recent_errors', [])
                if recent_errors:
                    formatted.append("• Recent Issues:")
                    for error in recent_errors[:3]:
                        formatted.append(f"  ❌ {error['message']}")
                        
        return formatted
    
    def _format_dashboard_data(self, data: Dict[str, Any]) -> List[str]:
        """Format dashboard data"""
        formatted = ["**Dashboard Overview:**"]
        
        for tool, result in data.items():
            if 'result' in result:
                dashboard_result = result['result']
                dashboards = dashboard_result.get('dashboards_found', [])
                formatted.append(f"• Dashboards Found: {len(dashboards)}")
                
                for dashboard in dashboards:
                    formatted.append(f"  📊 {dashboard['title']}")
                    
                panels = dashboard_result.get('panels', [])
                if panels:
                    formatted.append("• Key Metrics:")
                    for panel in panels:
                        status_icon = "✅" if panel['status'] == 'normal' else "⚠️"
                        formatted.append(f"  {status_icon} {panel['title']}: {panel['current_value']}")
                        
        return formatted
    
    def _format_generic_data(self, data: Dict[str, Any]) -> List[str]:
        """Format generic monitoring data"""
        formatted = ["**Monitoring Results:**"]
        
        for tool, result in data.items():
            if isinstance(result, dict) and 'error' not in result:
                formatted.append(f"✅ {tool}: Executed successfully")
                if 'result' in result:
                    formatted.append(f"   └─ Data retrieved from {result.get('type', 'monitoring system')}")
            else:
                formatted.append(f"❌ {tool}: {result.get('error', 'Execution failed')}")
                
        return formatted
    
    async def process_monitoring_request(self, state: SupervisorState) -> SupervisorState:
        """Process monitoring requests using LLM-driven subgraph"""
        try:
            logger.info("🚀 Starting LLM-driven monitoring subgraph processing")
            
            # Check if subgraph is available
            if not self.subgraph:
                return self._create_error_response(
                    state, 
                    "Monitoring subgraph not available - check LLM and MCP client initialization",
                    "subgraph_unavailable"
                )
            
            # Prepare subgraph state
            logger.info(f"🔧 Preparing subgraph with LLM client: {self.llm_client is not None}")
            logger.info(f"🔧 LLM client functional: {self.llm_client.is_functional() if self.llm_client else False}")
            logger.info(f"🔧 MCP client available: {self.mcp_client is not None}")
            
            subgraph_state = prepare_subgraph_state(
                supervisor_state=state,
                config=self.config,
                llm_client=self.llm_client,
                mcp_client=self.mcp_client
            )
            
            logger.info(f"🔧 Subgraph state LLM client: {subgraph_state.get('_llm_client') is not None}")
            
            # Execute the subgraph
            try:
                logger.info("🔧 Invoking monitoring subgraph...")
                final_subgraph_state = await asyncio.wait_for(
                    self.subgraph.ainvoke(subgraph_state),
                    timeout=self.config.total_timeout
                )
                
                logger.info(f"🔧 Subgraph execution completed. State type: {type(final_subgraph_state)}")
                logger.info(f"🔧 Subgraph state keys: {list(final_subgraph_state.keys()) if isinstance(final_subgraph_state, dict) else 'Not a dict'}")
                
                # Process subgraph results
                return self._process_subgraph_results(state, final_subgraph_state)
                
            except asyncio.TimeoutError:
                logger.error("❌ Subgraph execution timeout")
                return self._create_error_response(
                    state,
                    f"Monitoring request timeout after {self.config.total_timeout} seconds",
                    "subgraph_timeout"
                )
                
        except Exception as e:
            logger.error(f"❌ Error in subgraph processing: {e}")
            return self._create_error_response(state, f"Monitoring subgraph failed: {str(e)}", str(e))
    
    def _process_subgraph_results(self, original_state: SupervisorState, 
                                 subgraph_state: MonitoringSubgraphState) -> SupervisorState:
        """Process results from the monitoring subgraph"""
        try:
            # Check for errors
            if subgraph_state.get("errors"):
                error_msg = self._format_subgraph_error(subgraph_state)
                return self._create_error_response(
                    original_state,
                    error_msg,
                    subgraph_state.get("error_type", "subgraph_error")
                )
            
            # Get final response
            final_response = subgraph_state.get("final_response", "")
            if not final_response:
                return self._create_error_response(
                    original_state,
                    "No response generated by monitoring subgraph",
                    "no_response"
                )
            
            # Create agent response with metadata
            response_metadata = subgraph_state.get("response_metadata", {})
            llm_decisions = subgraph_state.get("llm_decisions", {})
            raw_tool_results = subgraph_state.get("raw_tool_results", {})
            
            # Debug: Log raw tool results extraction
            logger.info(f"🔍 Extracting raw tool results: {len(raw_tool_results)} tools found")
            if raw_tool_results:
                for tool_name, tool_data in raw_tool_results.items():
                    logger.info(f"🔍 Raw tool result: {tool_name} - {len(str(tool_data))} chars")
            
            agent_response = AgentResponse(
                agent_name="IntelligentMonitoringMCP",
                content=final_response,
                confidence=response_metadata.get("confidence", 0.8),
                requires_user_input=False,
                metadata={
                    "agent_type": "intelligent_monitoring_subgraph",
                    "processing_method": "llm_driven_subgraph",
                    "response_type": response_metadata.get("response_type", "unknown"),
                    "tools_used": response_metadata.get("tools_used", []),
                    "llm_decisions": llm_decisions,
                    "subgraph_completed": True,
                    "raw_tool_results": raw_tool_results  # Include raw results for UI
                }
            )
            
            # Debug: Log agent response metadata with protective checks
            try:
                if hasattr(agent_response, 'metadata') and agent_response.metadata:
                    logger.info(f"🔍 Agent response metadata keys: {list(agent_response.metadata.keys())}")
                    logger.info(f"🔍 Agent response has raw_tool_results: {'raw_tool_results' in agent_response.metadata}")
                else:
                    logger.warning(f"🔍 Agent response has no metadata attribute or metadata is None. Type: {type(agent_response)}")
            except Exception as debug_error:
                logger.error(f"🔍 Error accessing agent response metadata: {debug_error}")
                logger.info(f"🔍 Agent response type: {type(agent_response)}")
                logger.info(f"🔍 Agent response attributes: {dir(agent_response) if hasattr(agent_response, '__dict__') else 'No attributes'}")
            
            # Update supervisor state
            if isinstance(original_state, dict):
                if 'messages' not in original_state:
                    original_state['messages'] = []
                if 'agent_responses' not in original_state:
                    original_state['agent_responses'] = []
                if 'context' not in original_state:
                    original_state['context'] = {}
                    
                original_state['messages'].append(AIMessage(content=final_response))
                original_state['agent_responses'].append(agent_response)
                original_state['context']['last_agent'] = "IntelligentMonitoringMCP"
                original_state['context']['should_finish'] = True
                # Store raw tool results in context for supervisor access
                original_state['context']['raw_tool_results'] = raw_tool_results
                logger.info(f"🔍 Stored {len(raw_tool_results)} raw tool results in context")
            else:
                original_state.messages.append(AIMessage(content=final_response))
                original_state.agent_responses.append(agent_response)
                if not hasattr(original_state, 'context'):
                    original_state.context = {}
                original_state.context['last_agent'] = "IntelligentMonitoringMCP"
                original_state.context['should_finish'] = True
                # Store raw tool results in context for supervisor access
                original_state.context['raw_tool_results'] = raw_tool_results
                logger.info(f"🔍 Stored {len(raw_tool_results)} raw tool results in context")
            
            logger.info("✅ Monitoring subgraph processing completed successfully")
            return original_state
            
        except Exception as e:
            logger.error(f"❌ Error processing subgraph results: {e}")
            return self._create_error_response(
                original_state,
                f"Failed to process monitoring results: {str(e)}",
                "result_processing_error"
            )
    
    def _format_subgraph_error(self, subgraph_state: MonitoringSubgraphState) -> str:
        """Format subgraph errors for user consumption"""
        errors = subgraph_state.get("errors", [])
        failed_node = subgraph_state.get("failed_at_node", "unknown")
        error_type = subgraph_state.get("error_type", "unknown")
        
        if error_type == "llm_unavailable":
            return "❌ **AI Analysis Unavailable**\n\nThe intelligent query analysis service is currently unavailable. Please check your OpenAI API configuration or try again later."
        elif error_type == "mcp_unavailable":
            return "❌ **Monitoring Tools Unavailable**\n\nCannot connect to monitoring systems (Grafana/Prometheus). Please verify the monitoring services are running and accessible."
        elif error_type == "no_tools_selected":
            return "❌ **No Suitable Tools Found**\n\nNo monitoring tools were identified for your query. Please rephrase your request or specify the type of monitoring data you need."
        elif "timeout" in error_type:
            return f"❌ **Request Timeout**\n\nYour monitoring request timed out at the {failed_node.replace('_', ' ')} stage. Please try a simpler query or check system performance."
        else:
            primary_error = errors[0] if errors else "Unknown error occurred"
            return f"❌ **Monitoring Request Failed**\n\n{primary_error}\n\nFailed at: {failed_node.replace('_', ' ')}"
            return self._create_error_response(state, f"Failed to process monitoring request: {str(e)}", e)
    
    def _process_with_real_mcp(self, query: str) -> str:
        """Process query with real MCP tool execution using thread-safe approach"""
        try:
            import threading
            import queue
            import time
            
            # Create a queue to get the result
            result_queue = queue.Queue()
            
            def run_async_in_thread():
                """Run async processing in a separate thread"""
                try:
                    # Create new event loop for this thread
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    # Run the async processing
                    result = loop.run_until_complete(self._process_async_monitoring(query))
                    result_queue.put(('success', result))
                except Exception as e:
                    result_queue.put(('error', str(e)))
                finally:
                    loop.close()
            
            # Start the thread
            thread = threading.Thread(target=run_async_in_thread)
            thread.daemon = True
            thread.start()
            
            # Wait for result with timeout
            try:
                status, result = result_queue.get(timeout=30)  # 30 second timeout
                
                if status == 'success':
                    logger.info("✅ Real MCP processing completed successfully")
                    return result
                else:
                    logger.error(f"❌ Error in real MCP processing: {result}")
                    return self._generate_mcp_error_response(query, result)
                    
            except queue.Empty:
                logger.error("❌ Real MCP processing timed out")
                return self._generate_timeout_response(query)
                
        except Exception as e:
            logger.error(f"❌ Error in thread-based MCP processing: {e}")
            return self._generate_mcp_error_response(query, str(e))
    
    def _generate_mcp_error_response(self, query: str, error: str) -> str:
        """Generate response when MCP processing fails"""
        return f"""❌ **MCP Tool Execution Failed**

Your monitoring request could not be processed: "{query}"

**Error Details:** {error}

**Possible Causes:**
1. **MCP Server Connectivity** - Grafana/Prometheus servers may be unavailable
2. **Authentication Issues** - Check API credentials and permissions
3. **Network Problems** - Verify network connectivity to monitoring systems
4. **Service Downtime** - Monitoring services may be temporarily unavailable

**What you can do:**
1. **Check MCP Configuration** - Verify server settings and credentials
2. **Test Connectivity** - Ensure monitoring services are accessible
3. **Simplify Request** - Try a more specific or simpler query
4. **Contact Administrator** - Get help with monitoring system configuration

**Direct Access Options:**
- Access Grafana directly via web interface
- Use Prometheus query interface for metrics
- Check monitoring system status manually

I'm ready to help once the MCP connectivity is restored."""
    
    def _process_monitoring_sync(self, query: str) -> str:
        """Synchronous processing method for monitoring requests"""
        try:
            # Step 1: Analyze query using fallback method (no LLM for now to avoid async issues)
            logger.info("🧠 Analyzing query...")
            analysis = self._fallback_query_analysis(query)
            
            # Step 2: Generate response based on analysis
            logger.info("📝 Generating response...")
            
            # For now, provide information about available tools without executing them
            if "tools" in query.lower() or "available" in query.lower():
                return self._generate_tools_overview()
            else:
                return self._generate_sync_response(analysis, query)
            
        except Exception as e:
            logger.error(f"❌ Error in sync monitoring processing: {e}")
            return self._generate_error_response_text(query, str(e))
    
    def _generate_tools_overview(self) -> str:
        """Generate overview of available monitoring tools"""
        try:
            tools_info = get_comprehensive_tools_info()
            
            response_parts = [
                "🛠️ **MonitoringMCP Agent Tools Overview**",
                "",
                "The Intelligent MonitoringMCP agent has access to comprehensive monitoring tools across multiple categories:",
                ""
            ]
            
            for category, tools in tools_info['tools_by_category'].items():
                response_parts.append(f"### {category.title()} Tools:")
                for tool in tools[:5]:  # Show first 5 tools per category
                    response_parts.append(f"• `{tool}`")
                if len(tools) > 5:
                    response_parts.append(f"• ... and {len(tools) - 5} more")
                response_parts.append("")
            
            response_parts.extend([
                "**Key Capabilities:**",
                "• 🧠 **LLM-Driven Analysis** - Intelligent query understanding and tool selection",
                "• 📊 **Real-time Metrics** - Live Prometheus and Grafana data access",
                "• 🚨 **Alert Management** - Monitor and manage system alerts",
                "• 📝 **Log Analysis** - Search and analyze logs via Loki",
                "• 📈 **Dashboard Access** - Browse and interact with Grafana dashboards",
                "",
                "**Usage Examples:**",
                "- \"Show me CPU usage for the last hour\"",
                "- \"What alerts are currently active?\"",
                "- \"Find dashboards related to application performance\"",
                "- \"Search logs for errors in the last 30 minutes\"",
                "",
                "**Technical Features:**",
                "• Pure MCP-based execution (no simulation fallbacks)",
                "• LLM parameter optimization for better query results",
                "• Graceful error handling with actionable recommendations",
                "• Dynamic tool selection based on query intent",
                "",
                f"**Total Tools Available:** {tools_info['total_tools']} across {len(tools_info['tools_by_category'])} categories"
            ])
            
            return "\n".join(response_parts)
            
        except Exception as e:
            logger.error(f"❌ Error generating tools overview: {e}")
            return f"""🛠️ **MonitoringMCP Agent Tools**

The Intelligent MonitoringMCP agent provides comprehensive monitoring capabilities including:

• **Prometheus Metrics** - Query time-series data and system metrics
• **Grafana Dashboards** - Access and search monitoring dashboards  
• **Alert Management** - Monitor system alerts and notifications
• **Log Analysis** - Search and analyze application logs
• **System Monitoring** - CPU, memory, disk, and network metrics

**Key Features:**
• LLM-driven intelligent tool selection
• Real-time data access via MCP integration
• Dynamic query optimization
• Graceful error handling

**Error:** Unable to load detailed tool list: {str(e)}

Try asking specific monitoring questions to see the agent in action!"""
    
    def _generate_sync_response(self, analysis: Dict[str, Any], query: str) -> str:
        """Generate synchronous response based on analysis"""
        intent = analysis.get('intent', 'unknown')
        confidence = analysis.get('confidence', 0.0)
        suggested_tools = analysis.get('suggested_tools', [])
        
        response_parts = [
            f"📊 **Monitoring Query Analysis**",
            "",
            f"**Query:** {query}",
            f"**Intent Detected:** {intent.replace('_', ' ').title()}",
            f"**Confidence:** {confidence:.1%}",
            f"**Suggested Tools:** {', '.join(suggested_tools) if suggested_tools else 'None'}",
            "",
            "**Analysis Results:**"
        ]
        
        if intent == "performance_monitoring":
            response_parts.extend([
                "• This appears to be a performance monitoring request",
                "• Would typically use Prometheus queries and Grafana dashboards",
                "• Focus on system metrics like CPU, memory, and disk usage"
            ])
        elif intent == "alerting":
            response_parts.extend([
                "• This appears to be an alerting request",
                "• Would typically check alert rules and active notifications",
                "• Focus on incident management and alert status"
            ])
        elif intent == "logs_analysis":
            response_parts.extend([
                "• This appears to be a log analysis request",
                "• Would typically use Loki queries for log searching",
                "• Focus on error patterns and log aggregation"
            ])
        elif intent == "dashboard_analysis":
            response_parts.extend([
                "• This appears to be a dashboard request",
                "• Would typically search Grafana dashboards",
                "• Focus on visualization and monitoring panels"
            ])
        else:
            response_parts.extend([
                "• General monitoring request detected",
                "• Would use multiple tool categories for comprehensive analysis",
                "• Adaptive approach based on query context"
            ])
        
        response_parts.extend([
            "",
            "**Note:** Currently running in analysis mode. For live monitoring data,",
            "ensure MCP servers (Grafana/Prometheus) are properly configured and accessible.",
            "",
            "**Try these example queries:**",
            "• \"Show me system performance metrics\"",
            "• \"What monitoring dashboards are available?\"",
            "• \"Check for any active alerts\"",
            "• \"Search recent error logs\""
        ])
        
        return "\n".join(response_parts)
    
    async def _process_async_monitoring(self, query: str) -> str:
        """Async processing method for monitoring requests"""
        try:
            # Step 1: Analyze query with LLM or intelligent query parsing
            logger.info("🧠 Analyzing query...")
            analysis = await self._analyze_query_with_llm(query)
            
            # Step 2: Execute appropriate monitoring tools based on analysis
            logger.info(f"🔧 Executing tools for intent: {analysis.get('intent', 'unknown')}")
            execution_results = await self._execute_monitoring_tools(analysis, query)
            
            # Step 3: Generate intelligent response
            logger.info("📝 Generating response...")
            response = await self._generate_intelligent_response(analysis, execution_results, query)
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Error in async monitoring processing: {e}")
            return f"""❌ **Processing Error**

An error occurred while processing your monitoring request: "{query}"

**Error Details:** {str(e)}

**Graceful Recovery:**
I apologize for the technical difficulty. Here are some alternatives:

1. **Direct Access**: Try accessing your monitoring dashboards directly
2. **Simplified Query**: Break down your request into smaller, specific questions
3. **System Check**: Verify that monitoring services are operational
4. **Manual Review**: Check system logs and metrics manually

Please try rephrasing your question or contact support if the issue persists."""
    
    def _generate_timeout_response(self, query: str) -> str:
        """Generate response for timeout scenarios"""
        return f"""⏱️ **Request Timed Out**

Your monitoring request took too long to process: "{query}"

**What happened:**
The monitoring analysis exceeded the 30-second timeout limit.

**What you can do:**
1. **Simplify your request** - Try asking for specific metrics or shorter time ranges
2. **Break it down** - Split complex queries into smaller parts
3. **Check systems** - Verify monitoring services are responsive
4. **Try again** - The issue might be temporary

**Example simplified queries:**
- "Show CPU usage for last 10 minutes"
- "Get current alerts"
- "Display memory metrics"

I'm ready to help with a more focused request."""

    def _generate_error_response_text(self, query: str, error: str) -> str:
        """Generate error response text"""
        return f"""❌ **Processing Error**

An error occurred while processing your monitoring request: "{query}"

**Error Details:** {error}

**Graceful Recovery:**
I apologize for the technical difficulty. Here are some alternatives:

1. **Direct Access**: Try accessing your monitoring dashboards directly
2. **Simplified Query**: Break down your request into smaller, specific questions
3. **System Check**: Verify that monitoring services are operational
4. **Manual Review**: Check system logs and metrics manually

Please try rephrasing your question or contact support if the issue persists."""
    
    def _create_error_response(self, state: SupervisorState, error_message: str, error: Any) -> SupervisorState:
        """Create a graceful error response without hardcoded fallbacks"""
        graceful_message = f"""❌ **Unable to Process Monitoring Request**

{error_message}

**What you can do:**
1. **Rephrase your request** - Try asking in a different way
2. **Check connectivity** - Ensure monitoring services are available  
3. **Use direct access** - Access Grafana/Prometheus dashboards directly
4. **Contact support** - If this persists, reach out for assistance

**Example queries that work well:**
- "Show me CPU utilization for the last hour"
- "What alerts are currently active?"
- "Get memory usage trends for today"
- "Display dashboard for application performance"

I'm here to help once the technical issue is resolved."""

        agent_response = AgentResponse(
            agent_name="IntelligentMonitoringMCP",
            content=graceful_message,
            confidence=0.1,
            requires_user_input=True,
            metadata={"error": str(error), "error_type": "graceful_failure"}
        )
        
        # Update state
        if isinstance(state, dict):
            if 'messages' not in state:
                state['messages'] = []
            if 'agent_responses' not in state:
                state['agent_responses'] = []
            if 'context' not in state:
                state['context'] = {}
                
            state['messages'].append(AIMessage(content=graceful_message))
            state['agent_responses'].append(agent_response)
            state['context']['last_agent'] = "IntelligentMonitoringMCP"
            state['context']['should_finish'] = True
        else:
            state.messages.append(AIMessage(content=graceful_message))
            state.agent_responses.append(agent_response)
            if not hasattr(state, 'context'):
                state.context = {}
            state.context['last_agent'] = "IntelligentMonitoringMCP"
            state.context['should_finish'] = True
        
        return state


# Factory function for creating the intelligent monitoring agent
def create_enhanced_monitoring_mcp_agent():
    """Create the intelligent MonitoringMCP agent with LLM-driven subgraph"""
    try:
        # Initialize intelligent monitoring agent
        monitoring_agent = IntelligentMonitoringAgent()
        
        def monitoring_mcp_node(state: SupervisorState) -> SupervisorState:
            """Intelligent MonitoringMCP agent node with LLM-driven subgraph"""
            try:
                # Run the async subgraph processing in a thread to avoid event loop conflicts
                import threading
                import queue
                
                result_queue = queue.Queue()
                
                def run_async_subgraph():
                    """Run the async subgraph in a separate thread"""
                    try:
                        # Create new event loop for this thread
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        
                        # Run the async processing
                        result = loop.run_until_complete(monitoring_agent.process_monitoring_request(state))
                        result_queue.put(('success', result))
                    except Exception as e:
                        result_queue.put(('error', str(e)))
                    finally:
                        loop.close()
                
                # Start the thread
                thread = threading.Thread(target=run_async_subgraph)
                thread.daemon = True
                thread.start()
                
                # Wait for result with timeout
                try:
                    status, result = result_queue.get(timeout=monitoring_agent.config.total_timeout + 10)
                    
                    if status == 'success':
                        logger.info("✅ Subgraph processing completed successfully")
                        return result
                    else:
                        logger.error(f"❌ Error in subgraph processing: {result}")
                        return monitoring_agent._create_error_response(
                            state,
                            f"Subgraph processing failed: {result}",
                            "subgraph_thread_error"
                        )
                        
                except queue.Empty:
                    logger.error("❌ Subgraph processing timed out")
                    return monitoring_agent._create_error_response(
                        state,
                        "Monitoring request timed out",
                        "subgraph_thread_timeout"
                    )
                    
            except Exception as e:
                logger.error(f"❌ Error in monitoring node wrapper: {e}")
                return monitoring_agent._create_error_response(
                    state,
                    f"Monitoring node failed: {str(e)}",
                    "node_wrapper_error"
                )
        
        logger.info("✅ Intelligent MonitoringMCP agent created successfully")
        return monitoring_mcp_node
        
    except Exception as e:
        logger.error(f"❌ Failed to create intelligent monitoring agent: {e}")
        
        def fallback_monitoring_node(state: SupervisorState) -> SupervisorState:
            """Graceful fallback when agent creation fails"""
            error_msg = f"""❌ **Monitoring Agent Unavailable**

The intelligent monitoring agent could not be initialized: {str(e)}

**Alternative Actions:**
1. **Direct Dashboard Access**: Access your Grafana dashboards directly
2. **Manual Metrics Check**: Review Prometheus metrics manually  
3. **System Administrator**: Contact support for agent configuration
4. **Retry Later**: The issue may be temporary

**What you can try:**
- Use direct URLs to your monitoring systems
- Check if monitoring services are running
- Verify network connectivity to monitoring servers"""

            agent_response = AgentResponse(
                agent_name="IntelligentMonitoringMCP",
                content=error_msg,
                confidence=0.1,
                requires_user_input=True,
                metadata={"error": str(e), "agent_status": "unavailable"}
            )
            
            # Handle both dictionary and object states
            if isinstance(state, dict):
                if 'messages' not in state:
                    state['messages'] = []
                if 'agent_responses' not in state:
                    state['agent_responses'] = []
                if 'context' not in state:
                    state['context'] = {}
                    
                state['messages'].append(AIMessage(content=error_msg))
                state['agent_responses'].append(agent_response)
                state['context']['last_agent'] = "IntelligentMonitoringMCP"
                state['context']['should_finish'] = True
            else:
                state.messages.append(AIMessage(content=error_msg))
                state.agent_responses.append(agent_response)
                if not hasattr(state, 'context'):
                    state.context = {}
                state.context['last_agent'] = "IntelligentMonitoringMCP"
                state.context['should_finish'] = True
            
            return state
        
        return fallback_monitoring_node


# Export the intelligent agent creation function
def get_monitoring_mcp_agent():
    """Get the intelligent MonitoringMCP agent for backward compatibility"""
    return create_enhanced_monitoring_mcp_agent()


__all__ = ["create_enhanced_monitoring_mcp_agent", "IntelligentMonitoringAgent", "get_monitoring_mcp_agent"]