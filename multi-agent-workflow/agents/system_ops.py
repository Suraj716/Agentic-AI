"""
System Operations Agent - Handles system health and operational tasks
"""
from typing import Dict, Any, List
import json

import sys
import os

# Add current directory to Python path for imports
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from langchain_core.messages import HumanMessage, AIMessage
from core.state_schema import SupervisorState, AgentResponse
from core.agent_factory import create_agent
from common.utils.logging_setup import setup_logging

logger = setup_logging(__name__)


def create_system_ops_agent() -> callable:
    """Create the SystemOps agent for handling system operations
    
    Returns:
        callable: Agent node function for LangGraph workflow
    """
    
    system_prompt = """
    You are a system operations specialist that handles system health checks, service status, and operational tasks.
    
    Your capabilities include:
    - System health status checks
    - Service availability monitoring
    - Operational task guidance
    - Infrastructure status reporting
    - System troubleshooting assistance
    
    Guidelines:
    - Provide clear, actionable information about system status
    - Use technical language appropriate for operations teams
    - Offer troubleshooting steps when relevant
    - For monitoring data visualization, suggest using MonitoringMCP agent
    - For general help, guide users to HelpDocs agent
    
    Examples of queries you handle:
    - "Check system health"
    - "What is the status of services?"
    - "Are there any system alerts?"
    - "How do I restart service X?"
    - "System troubleshooting steps"
    """
    
    try:
        # Create agent with basic operational tools
        agent = create_agent(
            name="SystemOps",
            system_prompt=system_prompt,
            tools=[]  # Will add operational tools later
        )
        
        def system_ops_node(state: SupervisorState) -> SupervisorState:
            """SystemOps agent node function"""
            try:
                # Get the latest message
                messages = state.get("messages", [])
                if not messages:
                    logger.warning("No messages in state for SystemOps")
                    return state
                
                # Process with agent
                result = agent.invoke({"messages": messages})
                
                # Update state with response
                state.update(result)
                
                logger.info("SystemOps agent processed query successfully")
                return state
                
            except Exception as e:
                logger.error(f"Error in SystemOps agent: {e}")
                # Add error response
                error_msg = AIMessage(content="I encountered an error while checking system operations. Please try your request again.")
                state["messages"].append(error_msg)
                return state
        
        return system_ops_node
        
    except Exception as e:
        logger.error(f"Error creating SystemOps agent: {e}")
        raise


def get_system_ops_agent():
    """Get the SystemOps agent node function"""
    return create_system_ops_agent()