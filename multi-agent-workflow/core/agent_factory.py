"""
Agent factory for creating Multi-Agent workflow components
"""
from typing import List, Optional
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
# from langchain.agents import create_openai_functions_agent, AgentExecutor

try:
    # preferred / older public import
    from langchain.agents import create_openai_functions_agent, AgentExecutor
except Exception:
    # fallback to module-level paths used by newer/changed langchain releases
    try:
        # create_openai_functions_agent lives here in many releases
        from langchain.agents.openai_functions_agent.base import create_openai_functions_agent
    except Exception:
        create_openai_functions_agent = None  # keep defined for clearer errors later

    try:
        # AgentExecutor often lives here
        from langchain.agents.agent import AgentExecutor
    except Exception:
        AgentExecutor = None



from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

import sys
import os

# Add current directory to Python path for imports  
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from common.utils.base_client import BaseLLMClient
from common.utils.logging_setup import setup_logging

logger = setup_logging(__name__)


def create_agent(
    system_prompt: str,
    tools: Optional[List[BaseTool]] = None,
    name: str = "Agent",
    llm: Optional[BaseChatModel] = None
) -> AgentExecutor:
    """Create a LangGraph-compatible agent
    
    Args:
        system_prompt: System prompt for the agent
        tools: List of tools available to the agent (optional)
        name: Name of the agent
        llm: Language model to use (optional, will use default if not provided)
        
    Returns:
        AgentExecutor: Configured agent executor
    """
    
    # Use default LLM if not provided
    if llm is None:
        llm = get_base_llm()
    
    # Default to empty tools list if not provided
    if tools is None:
        tools = []
    
    # Create the prompt template
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="messages"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])
    
    # Create the agent
    if tools:
        # For Ollama, we need a simple tool executor instead of OpenAI functions
        agent_executor = ToolBasedAgentExecutor(llm, prompt, tools, name)
    else:
        # For agents without tools, create a simple executor
        agent_executor = SimpleAgentExecutor(llm, prompt, name)
    
    return agent_executor


class ToolBasedAgentExecutor:
    """Simple tool-based agent executor compatible with Ollama"""
    
    def __init__(self, llm: BaseChatModel, prompt: ChatPromptTemplate, tools: List[BaseTool], agent_name: str):
        self.llm = llm
        self.prompt = prompt
        self.tools = {tool.name: tool for tool in tools}
        self.agent_name = agent_name
    
    async def ainvoke(self, state: dict) -> dict:
        """Async invoke for compatibility with LangGraph"""
        return self.invoke(state)
    
    def invoke(self, state: dict) -> dict:
        """Invoke the agent with tools"""
        try:
            messages = state.get("messages", [])
            
            if not messages:
                return state
                
            last_message = messages[-1].content if hasattr(messages[-1], 'content') else ""
            
            # Check if we should use tools based on the message content
            tool_used = False
            tool_response = None
            
            # Try to use appropriate tools if available
            for tool_name, tool in self.tools.items():
                if tool_name in ["get_system_metrics", "list_available_dashboards", 
                               "get_dashboard_data", "get_alerts_and_notifications"]:
                    # Let the tool decide if it's relevant
                    try:
                        tool_response = tool.invoke({"input": last_message})
                        if tool_response:
                            tool_used = True
                            break
                    except Exception as tool_error:
                        logger.warning(f"Tool {tool_name} failed: {tool_error}")
                        continue
            
            if tool_used and tool_response:
                # Format response with tool data
                response_content = f"Here's the information you requested:\n\n{tool_response}"
                response = AIMessage(content=response_content)
            else:
                # Use LLM for general response
                formatted_prompt = self.prompt.format_messages(
                    messages=messages,
                    agent_scratchpad=[]
                )
                llm_response = self.llm.invoke(formatted_prompt)
                
                # Ensure response is properly formatted as AIMessage
                if isinstance(llm_response, AIMessage):
                    response = llm_response
                elif hasattr(llm_response, 'content'):
                    response = AIMessage(content=llm_response.content)
                else:
                    response = AIMessage(content=str(llm_response))
            
            return {
                **state,
                "messages": messages + [response],
                "context": {
                    **state.get("context", {}),
                    "last_agent": self.agent_name
                }
            }
            
        except Exception as e:
            logger.error(f"Error in {self.agent_name}: {e}")
            error_response = AIMessage(
                content=f"I encountered an error while processing your request: {str(e)}"
            )
            return {
                **state,
                "messages": state.get("messages", []) + [error_response],
                "context": {
                    **state.get("context", {}),
                    "last_agent": self.agent_name,
                    "error": str(e)
                }
            }


class SimpleAgentExecutor:
    """Simple agent executor for agents without tools"""
    
    def __init__(self, llm: BaseChatModel, prompt: ChatPromptTemplate, agent_name: str):
        self.llm = llm
        self.prompt = prompt
        self.agent_name = agent_name
    
    async def ainvoke(self, state: dict) -> dict:
        """Async invoke for compatibility with LangGraph"""
        return self.invoke(state)
    
    def invoke(self, state: dict) -> dict:
        """Invoke the agent"""
        try:
            messages = state.get("messages", [])
            
            # Format the prompt with messages
            formatted_prompt = self.prompt.format_messages(
                messages=messages,
                agent_scratchpad=[]
            )
            
            # Get response from LLM
            llm_response = self.llm.invoke(formatted_prompt)
            
            # Ensure response is properly formatted as AIMessage
            if isinstance(llm_response, AIMessage):
                response = llm_response
            elif hasattr(llm_response, 'content'):
                response = AIMessage(content=llm_response.content)
            else:
                response = AIMessage(content=str(llm_response))
            
            # Update state with response
            updated_messages = messages + [response]
            
            return {
                **state,
                "messages": updated_messages,
                "context": {
                    **state.get("context", {}),
                    "last_agent": self.agent_name
                }
            }
            
        except Exception as e:
            logger.error(f"Error in {self.agent_name}: {e}")
            error_response = AIMessage(
                content=f"I encountered an error while processing your request: {str(e)}"
            )
            return {
                **state,
                "messages": state.get("messages", []) + [error_response],
                "context": {
                    **state.get("context", {}),
                    "last_agent": self.agent_name,
                    "error": str(e)
                }
            }


def get_base_llm() -> BaseChatModel:
    """Get the base LLM instance"""
    try:
        client = BaseLLMClient()
        return client.llm
    except Exception as e:
        logger.error(f"Error creating LLM client: {e}")
        raise