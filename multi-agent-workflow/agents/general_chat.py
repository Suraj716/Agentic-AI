"""
General Chat Agent - Handles casual conversation and general knowledge
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


def create_general_chat_agent() -> callable:
    """Create the GeneralChat agent for handling casual conversation
    
    Returns:
        callable: Agent node function for LangGraph workflow
    """
    
    system_prompt = """
    You are a friendly AI assistant that handles general conversation, greetings, basic questions, and casual interactions.
    
    Your capabilities include:
    - Responding to greetings and casual conversation
    - Answering general knowledge questions
    - Performing basic math calculations
    - Providing friendly, helpful responses
    - Maintaining a conversational tone
    
    Guidelines:
    - Be warm, friendly, and professional
    - Keep responses concise but helpful
    - If asked about monitoring, system operations, or help documentation, acknowledge but suggest the user ask more specifically
    - For complex technical queries, guide users to be more specific about what they need
    
    Examples of queries you handle:
    - "Hello", "Hi there", "Good morning"
    - "What is 2+2?", "Calculate 15% of 200"
    - "What's the weather like?" (you can't check but can acknowledge)
    - "Tell me a joke"
    - General knowledge questions
    """
    
    try:
        # Create agent without specialized tools (just LLM)
        agent = create_agent(
            name="GeneralChat",
            system_prompt=system_prompt,
            tools=[]  # No specialized tools needed
        )
        
        def general_chat_node(state: SupervisorState) -> SupervisorState:
            """GeneralChat agent node function"""
            try:
                # Get the latest message
                messages = state.get("messages", [])
                if not messages:
                    logger.warning("No messages in state for GeneralChat")
                    return state
                
                # Process with agent
                result = agent.invoke({"messages": messages})
                
                # Update state with response
                state.update(result)
                
                logger.info("GeneralChat agent processed query successfully")
                return state
                
            except Exception as e:
                logger.error(f"Error in GeneralChat agent: {e}")
                # Add error response
                error_msg = AIMessage(content="I apologize, but I encountered an error. Please try asking your question again.")
                state["messages"].append(error_msg)
                return state
        
        return general_chat_node
        
    except Exception as e:
        logger.error(f"Error creating GeneralChat agent: {e}")
        raise


def get_general_chat_agent():
    """Get the GeneralChat agent node function"""
    return create_general_chat_agent()