"""
Multi-Agent Workflow Supervisor
"""
from typing import Dict, Any, List, Optional
import json
from datetime import datetime

import sys
import os

# Add current directory to Python path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from langchain_core.messages import HumanMessage, AIMessage
from core.supervisor_workflow import SupervisorWorkflow
from core.state_schema import SupervisorState
from agents.general_chat import get_general_chat_agent
from agents.monitoring_mcp import get_monitoring_mcp_agent
from agents.system_ops import get_system_ops_agent
from agents.help_docs import get_help_docs_agent
from common.utils.logging_setup import setup_logging

logger = setup_logging(__name__)


class MultiAgentSupervisor:
    """Main supervisor that orchestrates multiple specialized agents using LangGraph workflow"""
    
    def __init__(self):
        self.supervisor_workflow = SupervisorWorkflow()
        self.compiled_workflow = None
        self.is_initialized = False
        
    async def initialize(self):
        """Initialize the supervisor agent and workflow"""
        try:
            logger.info("Initializing Multi-Agent Supervisor...")
            
            # Initialize supervisor workflow
            self.supervisor_workflow.initialize()
            
            # Create agent nodes
            agent_nodes = {
                "GeneralChat": get_general_chat_agent(),
                "MonitoringMCP": get_monitoring_mcp_agent(),
                "SystemOps": get_system_ops_agent(),
                "HelpDocs": get_help_docs_agent()
            }
            
            # Build and compile workflow graph
            self.compiled_workflow = self.supervisor_workflow.build_workflow_graph(agent_nodes)
            
            self.is_initialized = True
            logger.info("Multi-Agent Supervisor initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing Multi-Agent Supervisor: {e}")
            raise
    
    async def process_query(self, query: str, conversation_history: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """Process a user query using the supervisor workflow
        
        Args:
            query: User query to process
            conversation_history: Previous conversation messages
            
        Returns:
            Dict with response and metadata
        """
        try:
            if not self.is_initialized:
                await self.initialize()
            
            # Prepare initial state
            messages = []
            
            # Add conversation history if provided
            if conversation_history:
                for msg in conversation_history:
                    if msg.get("role") == "user":
                        messages.append(HumanMessage(content=msg.get("content", "")))
                    elif msg.get("role") == "assistant":
                        messages.append(AIMessage(content=msg.get("content", "")))
            
            # Add current query
            messages.append(HumanMessage(content=query))
            
            # Create initial state
            initial_state: SupervisorState = {
                "messages": messages,
                "next_agent": None,
                "context": {
                    "query_type": "user_query",
                    "timestamp": str(datetime.now())
                },
                "performance": {
                    "start_time": str(datetime.now()),
                    "agent_calls": 0
                }
            }
            
            # Run workflow with increased recursion limit
            config = {"recursion_limit": 50}
            result = self.compiled_workflow.invoke(initial_state, config=config)
            
            # Log the full workflow result for debugging
            logger.info(f"🔍 Full workflow result keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
            
            # Extract response
            response_messages = result.get("messages", [])
            if response_messages:
                # Get the latest AI message
                ai_messages = [msg for msg in response_messages if isinstance(msg, AIMessage)]
                if ai_messages:
                    response_content = ai_messages[-1].content
                else:
                    response_content = "I'm sorry, I couldn't process your request."
            else:
                response_content = "I'm sorry, I couldn't process your request."
            
            # Extract raw data if available (for MCP responses)
            raw_data = result.get("context", {}).get("raw_mcp_data", None)
            
            # Check for raw tool results in context (preferred method)
            raw_tool_results = result.get("context", {}).get("raw_tool_results", {})
            if raw_tool_results:
                from agents.monitoring_subgraph.helpers import format_raw_tool_results_for_ui
                raw_data = format_raw_tool_results_for_ui(raw_tool_results)
                logger.info(f"🔍 Found raw tool results in context: {len(raw_tool_results)} tools")
            
            # Fallback: Check for raw tool results in agent responses (legacy method)
            if not raw_data:
                agent_responses = result.get("agent_responses", [])
                if agent_responses:
                    for agent_response in agent_responses:
                        if hasattr(agent_response, 'metadata') and agent_response.metadata:
                            raw_tool_results = agent_response.metadata.get("raw_tool_results", {})
                            if raw_tool_results:
                                # Format raw tool results for UI display
                                from agents.monitoring_subgraph.helpers import format_raw_tool_results_for_ui
                                raw_data = format_raw_tool_results_for_ui(raw_tool_results)
                                logger.info(f"🔍 Found raw tool results from {agent_response.agent_name}: {len(raw_tool_results)} tools")
                                break
            
            # Log raw data availability for debugging
            if raw_data:
                logger.info(f"📊 Raw data included in response: {type(raw_data).__name__} with {len(raw_data) if isinstance(raw_data, dict) else 'N/A'} entries")
            else:
                logger.debug("📊 No raw data available for this response")
            
            # Prepare response
            response = {
                "response": response_content,
                "agent_used": result.get("context", {}).get("last_agent", "Unknown"),
                "conversation_type": result.get("context", {}).get("conversation_type", "general"),
                "status": "success",
                "raw_data": raw_data  # Include raw MCP data if available
            }
            
            logger.info(f"Query processed successfully by {response['agent_used']} agent")
            return response
            
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return {
                "response": "I apologize, but I encountered an error while processing your request. Please try again.",
                "agent_used": "Error",
                "conversation_type": "error",
                "status": "error",
                "error": str(e)
            }
    
    def get_agent_capabilities(self) -> Dict[str, Any]:
        """Get information about agent capabilities
        
        Returns:
            Dict with agent capabilities information
        """
        return {
            "agents": {
                "GeneralChat": {
                    "description": "Handles greetings, casual conversation, basic math, and general knowledge",
                    "capabilities": ["greetings", "casual_chat", "basic_math", "general_knowledge"]
                },
                "MonitoringMCP": {
                    "description": "Handles dashboard queries, metrics analysis, and monitoring data",
                    "capabilities": ["dashboard_data", "system_metrics", "monitoring_analysis", "alerts"]
                },
                "SystemOps": {
                    "description": "Handles system health checks, service status, and operational tasks",
                    "capabilities": ["system_health", "service_status", "operational_tasks", "troubleshooting"]
                },
                "HelpDocs": {
                    "description": "Handles help requests, documentation, and guidance",
                    "capabilities": ["help_documentation", "usage_guidance", "tutorials", "feature_explanations"]
                }
            },
            "routing": {
                "method": "LangGraph Supervisor",
                "description": "Intelligent routing based on query content and conversation context"
            }
        }
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check on the supervisor agent
        
        Returns:
            Dict with health check results
        """
        try:
            health_status = {
                "supervisor_agent": "healthy" if self.is_initialized else "not_initialized",
                "workflow": "healthy" if self.compiled_workflow else "not_compiled",
                "agents": {
                    "GeneralChat": "available",
                    "MonitoringMCP": "available", 
                    "SystemOps": "available",
                    "HelpDocs": "available"
                },
                "overall_status": "healthy" if self.is_initialized and self.compiled_workflow else "unhealthy"
            }
            
            return health_status
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "supervisor_agent": "error",
                "workflow": "error",
                "agents": {},
                "overall_status": "unhealthy",
                "error": str(e)
            }


# Global supervisor agent instance
_multi_agent_supervisor = None


def get_multi_agent_supervisor() -> MultiAgentSupervisor:
    """Get the global multi-agent supervisor instance"""
    global _multi_agent_supervisor
    if _multi_agent_supervisor is None:
        _multi_agent_supervisor = MultiAgentSupervisor()
    return _multi_agent_supervisor


def initialize_multi_agent_supervisor():
    """Initialize the global multi-agent supervisor"""
    supervisor = get_multi_agent_supervisor()
    if not supervisor.is_initialized:
        supervisor.initialize()
    return supervisor