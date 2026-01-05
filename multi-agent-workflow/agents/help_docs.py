"""
Help Documentation Agent - Handles help requests and guidance
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


def create_help_docs_agent() -> callable:
    """Create the HelpDocs agent for handling help and documentation
    
    Returns:
        callable: Agent node function for LangGraph workflow
    """
    
    system_prompt = """
    You are a helpful documentation and guidance specialist that assists users with how-to questions and system usage.
    
    Your capabilities include:
    - Providing usage instructions and guidance
    - Explaining system features and capabilities
    - Offering step-by-step tutorials
    - Answering "how-to" questions
    - Directing users to appropriate resources
    
    Guidelines:
    - Provide clear, step-by-step instructions
    - Use examples to illustrate concepts
    - Be patient and thorough in explanations
    - For monitoring data, direct users to MonitoringMCP agent
    - For system operations, direct users to SystemOps agent
    - For casual conversation, direct users to GeneralChat agent
    
    Examples of queries you handle:
    - "How do I use this system?"
    - "What features are available?"
    - "Can you walk me through the process?"
    - "I need help with..."
    - "What are the steps to..."
    """
    
    try:
        # Create agent for documentation and help
        agent = create_agent(
            name="HelpDocs",
            system_prompt=system_prompt,
            tools=[]  # Will add documentation tools later
        )
        
        def help_docs_node(state: SupervisorState) -> SupervisorState:
            """HelpDocs agent node function"""
            try:
                # Get the latest message
                messages = state.get("messages", [])
                if not messages:
                    logger.warning("No messages in state for HelpDocs")
                    return state
                
                # Process with agent
                result = agent.invoke({"messages": messages})
                
                # Update state with response
                state.update(result)
                
                logger.info("HelpDocs agent processed query successfully")
                return state
                
            except Exception as e:
                logger.error(f"Error in HelpDocs agent: {e}")
                # Add error response
                error_msg = AIMessage(content="I had trouble accessing the help documentation. Please try rephrasing your question or ask for specific guidance.")
                state["messages"].append(error_msg)
                return state
        
        return help_docs_node
        
    except Exception as e:
        logger.error(f"Error creating HelpDocs agent: {e}")
        raise


def get_help_docs_agent():
    """Get the HelpDocs agent node function"""
    return create_help_docs_agent()