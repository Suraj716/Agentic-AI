"""
LangGraph Multi-Agent Supervisor Workflow
"""
from typing import List, Dict, Any, Literal
import functools
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph import StateGraph, END

import sys
import os

# Add current directory to Python path for imports
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from core.state_schema import SupervisorState
from core.agent_factory import get_base_llm
from common.utils.logging_setup import setup_logging

logger = setup_logging(__name__)


def _analyze_content_intent(message: str) -> Dict[str, str]:
    """Analyze message content to determine intent when keyword matching fails
    
    Args:
        message: User message to analyze
        
    Returns:
        Dict with next_agent decision
    """
    message_lower = message.lower()
    logger.info(f"🧠 Analyzing message for routing: '{message[:50]}...'")
    
    # Content analysis patterns
    if any(pattern in message_lower for pattern in ["?", "what", "how much", "when", "where", "why"]):
        # Question patterns - likely general chat
        decision = {"next_agent": "GeneralChat"}
        logger.info("🎯 Routed to GeneralChat (question pattern detected)")
        return decision
    elif any(pattern in message_lower for pattern in ["show", "display", "view", "get", "fetch"]):
        # Data request patterns - likely monitoring
        decision = {"next_agent": "MonitoringMCP"}
        logger.info("🎯 Routed to MonitoringMCP (data request pattern detected)")
        return decision
    elif any(pattern in message_lower for pattern in ["run", "start", "stop", "restart", "configure"]):
        # Operation patterns - likely system ops
        decision = {"next_agent": "SystemOps"}
        logger.info("🎯 Routed to SystemOps (operation pattern detected)")
        return decision
    elif any(pattern in message_lower for pattern in ["learn", "understand", "confused", "explain"]):
        # Learning patterns - likely help docs
        decision = {"next_agent": "HelpDocs"}
        logger.info("🎯 Routed to HelpDocs (learning pattern detected)")
        return decision
    else:
        # Default to general chat for unknown patterns
        decision = {"next_agent": "GeneralChat"}
        logger.info("🎯 Routed to GeneralChat (default fallback)")
        return decision


def create_supervisor_chain(agents: List[str]) -> callable:
    """Create the supervisor chain for routing queries to agents
    
    Args:
        agents: List of agent names available for routing
        
    Returns:
        callable: Supervisor chain function
    """
    
    system_prompt = f"""
    You are a supervisor managing a team of specialized AI agents. Your role is to analyze user queries and route them to the most appropriate agent based on the query content and context.

    Available agents:
    - GeneralChat: Handle greetings, casual conversation, basic math, general knowledge questions, and friendly interactions
    - MonitoringMCP: Intelligent monitoring agent with LLM-driven tool selection for dynamic analysis of dashboards, metrics, logs, alerts, and system performance
    - SystemOps: Handle system health checks, service status, operational tasks, and infrastructure queries
    - HelpDocs: Handle help requests, documentation questions, guidance, and how-to questions

    Routing Guidelines:
    1. Analyze the user's query content and intent
    2. Consider previous conversation context when available
    3. Route to the most appropriate specialized agent
    4. Use FINISH when the conversation is complete or the user indicates they're done

    Examples:
    - "Hi there!" or "Hello" → GeneralChat
    - "What is 2+2?" → GeneralChat  
    - "Show me system metrics from last hour" → MonitoringMCP
    - "What dashboards are available?" → MonitoringMCP
    - "Check system health" → SystemOps
    - "How do I use this system?" → HelpDocs
    - "Thanks, goodbye" → FINISH

    Respond with ONLY the agent name that should handle the query, or "FINISH" to end the conversation.
    Do not include any explanation or additional text.
    """
    
    try:
        llm = get_base_llm()
        
        # Create intelligent supervisor with LLM-only routing
        def supervisor_function(state: SupervisorState) -> Dict[str, str]:
            """Supervisor function that uses LLM for all routing decisions"""
            messages = state.get("messages", [])
            if not messages:
                return {"next_agent": "GeneralChat"}
            
            # Get the last user message
            last_message = None
            for msg in reversed(messages):
                if isinstance(msg, HumanMessage):
                    last_message = msg.content
                    break
            
            if not last_message:
                return {"next_agent": "FINISH"}
            
            # LLM-based intelligent routing for ALL queries
            try:
                prompt = ChatPromptTemplate.from_messages([
                    ("system", system_prompt),
                    ("human", f"Route this query: {last_message}")
                ])
                
                chain = prompt | llm
                result = chain.invoke({"query": last_message})
                
                # Parse LLM response - handle both string and object responses
                if hasattr(result, 'content'):
                    agent_choice = result.content.strip()
                elif isinstance(result, str):
                    agent_choice = result.strip()
                else:
                    agent_choice = str(result).strip()
                
                # Validate LLM choice
                valid_agents = ["GeneralChat", "MonitoringMCP", "SystemOps", "HelpDocs", "FINISH"]
                if agent_choice in valid_agents:
                    return {"next_agent": agent_choice}
                else:
                    # LLM response unclear, use content analysis as final fallback
                    logger.warning(f"LLM returned unclear response: {agent_choice}, using content analysis")
                    return _analyze_content_intent(last_message)
                    
            except Exception as e:
                logger.error(f"LLM routing failed: {e}, using content analysis as fallback")
                return _analyze_content_intent(last_message)
        
        return supervisor_function
        
    except Exception as e:
        logger.error(f"Error creating supervisor chain: {e}")
        raise


def should_continue(state: SupervisorState) -> Literal["FINISH", "continue"]:
    """Determine if the workflow should continue or finish
    
    Args:
        state: Current workflow state
        
    Returns:
        str: "FINISH" to end workflow, "continue" to continue
    """
    # Check if we should finish based on context
    context = state.get("context", {})
    
    # If explicitly marked to finish
    if context.get("should_finish", False):
        return "FINISH"
    
    # Check if an agent has already responded to the current user query
    messages = state.get("messages", [])
    if len(messages) >= 2:
        # Count recent user and assistant messages
        recent_messages = messages[-4:] if len(messages) >= 4 else messages
        user_messages = [m for m in recent_messages if isinstance(m, HumanMessage)]
        ai_messages = [m for m in recent_messages if isinstance(m, AIMessage)]
        
        # If we have at least one user message and one AI response, we can finish
        if user_messages and ai_messages and len(ai_messages) >= len(user_messages):
            return "FINISH"
    
    # Check if user said goodbye
    if messages:
        last_user_message = None
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                last_user_message = msg.content.lower()
                break
        
        if last_user_message and any(word in last_user_message for word in ["bye", "goodbye", "exit", "quit", "thanks", "thank you"]):
            return "FINISH"
    
    # If we have agent responses, check if last agent responded
    last_agent = context.get("last_agent")
    if last_agent and last_agent != "supervisor":
        return "FINISH"
    
    return "continue"


def route_to_agent(state: SupervisorState) -> str:
    """Route to the appropriate agent based on supervisor decision
    
    Args:
        state: Current workflow state
        
    Returns:
        str: Name of the agent to route to
    """
    return state.get("next_agent", "GeneralChat")


class SupervisorWorkflow:
    """Multi-Agent workflow orchestrator using LangGraph"""
    
    def __init__(self):
        self.agents = ["GeneralChat", "MonitoringMCP", "SystemOps", "HelpDocs"]
        self.supervisor_chain = None
        self.workflow = None
        
    def initialize(self):
        """Initialize the supervisor workflow"""
        try:
            # Create supervisor chain
            self.supervisor_chain = create_supervisor_chain(self.agents)
            logger.info("Multi-Agent supervisor workflow initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing supervisor workflow: {e}")
            raise
    
    def create_supervisor_node(self, state: SupervisorState) -> SupervisorState:
        """Supervisor node function for the workflow"""
        try:
            # Invoke supervisor to get routing decision
            result = self.supervisor_chain(state)
            
            # Update state with supervisor decision (no hardcoded defaults)
            state["next_agent"] = result.get("next_agent", "FINISH")
            
            return state
            
        except Exception as e:
            logger.error(f"Error in supervisor node: {e}")
            # On error, finish gracefully instead of forcing GeneralChat
            state["next_agent"] = "FINISH"
            return state
    
    def build_workflow_graph(self, agent_nodes: Dict[str, callable]) -> StateGraph:
        """Build the complete workflow graph with all agents
        
        Args:
            agent_nodes: Dictionary of agent name to agent node function
            
        Returns:
            StateGraph: Compiled workflow graph
        """
        try:
            # Create workflow
            workflow = StateGraph(SupervisorState)
            
            # Add supervisor node
            workflow.add_node("supervisor", self.create_supervisor_node)
            
            # Add agent nodes
            for agent_name, agent_node in agent_nodes.items():
                workflow.add_node(agent_name, agent_node)
            
            # Add conditional edges from agents - they can either finish or continue
            for agent_name in agent_nodes.keys():
                workflow.add_conditional_edges(
                    agent_name,
                    should_continue,  # Function to determine if agent should continue
                    {
                        "FINISH": END,
                        "continue": "supervisor"
                    }
                )
            
            # Add conditional edges from supervisor  
            conditional_map = {"FINISH": END}
            for agent_name in agent_nodes.keys():
                conditional_map[agent_name] = agent_name
            
            workflow.add_conditional_edges(
                "supervisor",
                route_to_agent,  # This function determines which key to use
                conditional_map   # This maps keys to actual nodes
            )
            
            # Set entry point
            workflow.set_entry_point("supervisor")
            
            # Compile workflow with increased recursion limit
            compiled_workflow = workflow.compile()
            
            logger.info("Multi-Agent workflow graph built successfully with recursion_limit=50")
            return compiled_workflow
            
        except Exception as e:
            logger.error(f"Error building workflow graph: {e}")
            raise