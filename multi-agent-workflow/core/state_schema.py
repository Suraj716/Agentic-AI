"""
State schema for the LangGraph Multi-Agent Supervisor workflow
"""
from typing_extensions import TypedDict
from typing import List, Dict, Any, Optional
from langchain_core.messages import BaseMessage


class SupervisorState(TypedDict):
    """State for the multi-agent supervisor workflow"""
    # Messages in the conversation
    messages: List[BaseMessage]
    
    # Next agent to route to
    next_agent: Optional[str]
    
    # Additional context
    context: Dict[str, Any]
    
    # Performance tracking
    performance: Dict[str, Any]


class AgentResponse(TypedDict):
    """Response from an individual agent"""
    content: str
    agent_name: str
    confidence: float
    tool_used: Optional[str]
    metadata: Dict[str, Any]