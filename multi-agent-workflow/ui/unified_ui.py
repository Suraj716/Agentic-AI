"""
Unified Multi-Agent Workflow UI
Single page with all functionality combined
"""
import streamlit as st
import requests
import json
import time
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional

# Configuration
FASTAPI_BASE_URL = "http://127.0.0.1:8080"
SUPERVISOR_ENDPOINT = f"{FASTAPI_BASE_URL}/query"
SUPERVISOR_HEALTH = f"{FASTAPI_BASE_URL}/health"
SUPERVISOR_CAPABILITIES = f"{FASTAPI_BASE_URL}/agents"

# Page configuration
st.set_page_config(
    page_title="Multi-Agent Workflow System",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = str(uuid.uuid4())
if "current_topics" not in st.session_state:
    st.session_state.current_topics = []

def check_api_status() -> bool:
    """Check if FastAPI backend is running"""
    try:
        response = requests.get(f"{FASTAPI_BASE_URL}/", timeout=5)
        return response.status_code == 200
    except:
        return False

def check_supervisor_status() -> bool:
    """Check if supervisor is initialized"""
    try:
        response = requests.get(SUPERVISOR_HEALTH, timeout=5)
        return response.status_code == 200
    except:
        return False

def get_supervisor_capabilities() -> Optional[Dict[str, Any]]:
    """Get available agents from supervisor"""
    try:
        response = requests.get(SUPERVISOR_CAPABILITIES, timeout=5)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None

def query_supervisor_agent(query: str) -> Optional[Dict[str, Any]]:
    """Query the multi-agent supervisor"""
    try:
        payload = {
            "query": query,
            "user_id": st.session_state.conversation_id
        }
        
        response = requests.post(
            SUPERVISOR_ENDPOINT,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=60
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"API Error: {response.status_code}")
            return None
            
    except Exception as e:
        st.error(f"Request failed: {str(e)}")
        return None

def start_new_conversation():
    """Start a new conversation"""
    st.session_state.conversation_id = str(uuid.uuid4())
    st.session_state.chat_history = []
    st.session_state.current_topics = []
    st.rerun()

def main():
    """Main application"""
    
    # Header
    st.title("🤖 Multi-Agent Workflow System")
    st.markdown("Unified interface for intelligent multi-agent conversations with real MCP integration")
    
    # Sidebar
    with st.sidebar:
        st.header("🔧 System Control")
        
        # System Status
        st.subheader("📊 System Status")
        api_status = check_api_status()
        supervisor_status = check_supervisor_status()
        
        if api_status:
            st.success("✅ Backend Connected")
        else:
            st.error("❌ Backend Offline")
            st.warning("Please ensure FastAPI server is running on port 8080")
        
        if supervisor_status:
            st.success("✅ Multi-Agent System Online")
        else:
            st.warning("⚠️ Multi-Agent System Offline")
        
        st.markdown("---")
        
        # Available Agents
        if supervisor_status:
            agents_info = get_supervisor_capabilities()
            if agents_info:
                st.subheader("🤖 Available Agents")
                for agent in agents_info.get("agents", []):
                    agent_name = agent.get("name", "Unknown")
                    with st.expander(f"🤖 {agent_name}"):
                        st.write(agent.get("description", "No description available"))
        
        st.markdown("---")
        
        # Conversation Management
        st.subheader("💭 Conversation")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 New Chat", use_container_width=True):
                start_new_conversation()
        
        with col2:
            if st.button("📋 Clear", use_container_width=True):
                st.session_state.chat_history = []
                st.rerun()
        
        # Current Topics
        if st.session_state.current_topics:
            st.subheader("📝 Current Topics")
            for topic in st.session_state.current_topics[-5:]:
                st.markdown(f"• {topic}")
        
        st.markdown("---")
        
        # UI Settings
        st.subheader("⚙️ Settings")
        show_timestamps = st.checkbox("Show timestamps", value=True)
        show_agent_info = st.checkbox("Show agent routing", value=True)
        show_raw_data = st.checkbox("Show raw MCP data", value=True)
        
        st.markdown("---")
        
        # Quick Examples
        st.subheader("💡 Quick Examples")
        
        examples = [
            "Show me all dashboards",
            "List system metrics", 
            "What is the current system status?",
            "How do I configure monitoring?",
            "Hello, how are you?"
        ]
        
        selected_example = st.selectbox(
            "Try an example:",
            [""] + examples,
            index=0
        )

    # Main chat interface
    st.subheader("💬 Chat Interface")
    
    # Display conversation history
    if not st.session_state.chat_history:
        st.info("👋 Welcome! Start a conversation by typing a message below or select an example from the sidebar.")
    else:
        for message in st.session_state.chat_history:
            if message["role"] == "user":
                with st.chat_message("user"):
                    st.write(message["content"])
                    if show_timestamps and "timestamp" in message:
                        st.caption(f"⏰ {message['timestamp']}")
            else:
                with st.chat_message("assistant"):
                    st.write(message["content"])
                    
                    if show_agent_info and "agent" in message:
                        st.caption(f"🤖 Handled by: {message['agent']}")
                    
                    if show_timestamps and "timestamp" in message:
                        st.caption(f"⏰ {message['timestamp']}")
                    
                    # Show raw data if available and enabled
                    if (show_raw_data and 
                        message.get("raw_data") and 
                        message.get("agent") in ["MonitoringMCP", "IntelligentMonitoringMCP"]):
                        with st.expander("🔍 Raw MCP Tool Results", expanded=False):
                            raw_data = message["raw_data"]
                            
                            if isinstance(raw_data, dict) and raw_data:
                                # Display summary first
                                st.subheader("📊 Tool Results Summary")
                                
                                for tool_name, tool_data in raw_data.items():
                                    if tool_data.get("status") == "success":
                                        st.success(f"✅ **{tool_name}** - {tool_data.get('summary', 'Success')}")
                                        col1, col2, col3 = st.columns(3)
                                        with col1:
                                            st.metric("Data Size", f"{tool_data.get('data_size', 0)} chars")
                                        with col2:
                                            st.metric("Type", tool_data.get('data_type', 'unknown'))
                                        with col3:
                                            st.metric("Exec Time", f"{tool_data.get('execution_time', 0):.2f}s")
                                        
                                        # Show raw data with proper formatting
                                        with st.expander(f"📋 Raw Data for {tool_name}", expanded=False):
                                            raw_result = tool_data.get('raw_data', {})
                                            if isinstance(raw_result, (dict, list)):
                                                st.json(raw_result)
                                            else:
                                                st.code(str(raw_result), language="text")
                                    else:
                                        st.error(f"❌ **{tool_name}** - {tool_data.get('error', 'Unknown error')}")
                            else:
                                # Fallback for non-formatted raw data
                                st.json(raw_data)

    # Chat input
    user_input = st.chat_input("Type your message here...")
    
    # Handle example selection
    if selected_example:
        user_input = selected_example
        st.rerun()
    
    # Process user input
    if user_input:
        # Add user message
        user_msg = {
            "role": "user",
            "content": user_input,
            "timestamp": datetime.now().strftime("%H:%M:%S")
        }
        st.session_state.chat_history.append(user_msg)
        
        # Display user message
        with st.chat_message("user"):
            st.write(user_input)
            if show_timestamps:
                st.caption(f"⏰ {user_msg['timestamp']}")
        
        # Get AI response
        with st.chat_message("assistant"):
            with st.spinner("🤔 Processing..."):
                if supervisor_status:
                    response_data = query_supervisor_agent(user_input)
                else:
                    st.error("❌ Multi-agent system is not available")
                    response_data = None
                
                if response_data:
                    # Display response
                    st.write(response_data.get("response", "No response received"))
                    
                    agent_used = response_data.get("agent_used", "Unknown")
                    if show_agent_info:
                        st.caption(f"🤖 Handled by: {agent_used}")
                    
                    # Show raw data immediately if available and enabled
                    if (show_raw_data and 
                        response_data.get("raw_data") and 
                        agent_used in ["MonitoringMCP", "IntelligentMonitoringMCP"]):
                        with st.expander("🔍 Raw MCP Tool Results", expanded=False):
                            raw_data = response_data["raw_data"]
                            
                            if isinstance(raw_data, dict) and raw_data:
                                # Display summary first
                                st.subheader("📊 Tool Results Summary")
                                
                                for tool_name, tool_data in raw_data.items():
                                    if tool_data.get("status") == "success":
                                        st.success(f"✅ **{tool_name}** - {tool_data.get('summary', 'Success')}")
                                        col1, col2, col3 = st.columns(3)
                                        with col1:
                                            st.metric("Data Size", f"{tool_data.get('data_size', 0)} chars")
                                        with col2:
                                            st.metric("Type", tool_data.get('data_type', 'unknown'))
                                        with col3:
                                            st.metric("Exec Time", f"{tool_data.get('execution_time', 0):.2f}s")
                                        
                                        # Show raw data with proper formatting
                                        with st.expander(f"📋 Raw Data for {tool_name}", expanded=False):
                                            raw_result = tool_data.get('raw_data', {})
                                            if isinstance(raw_result, (dict, list)):
                                                st.json(raw_result)
                                            else:
                                                st.code(str(raw_result), language="text")
                                    else:
                                        st.error(f"❌ **{tool_name}** - {tool_data.get('error', 'Unknown error')}")
                            else:
                                # Fallback for non-formatted raw data
                                st.json(raw_data)
                    
                    # Add assistant message to history
                    assistant_msg = {
                        "role": "assistant",
                        "content": response_data.get("response", "No response received"),
                        "agent": agent_used,
                        "timestamp": datetime.now().strftime("%H:%M:%S"),
                        "raw_data": response_data.get("raw_data")
                    }
                    st.session_state.chat_history.append(assistant_msg)
                    
                    # Update topics if available
                    if "conversation_summary" in response_data:
                        summary = response_data["conversation_summary"]
                        if "recent_topics" in summary:
                            st.session_state.current_topics = summary["recent_topics"]
                
                else:
                    # Add error message
                    error_msg = {
                        "role": "assistant",
                        "content": "Sorry, I couldn't process your request. Please try again.",
                        "agent": "Error",
                        "timestamp": datetime.now().strftime("%H:%M:%S")
                    }
                    st.session_state.chat_history.append(error_msg)
        
        st.rerun()

    # Footer
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("🔗 **Backend API**: http://localhost:8080")
    with col2:
        st.markdown("📊 **Health Check**: http://localhost:8080/health")
    with col3:
        st.markdown("🤖 **Agents**: http://localhost:8080/agents")

if __name__ == "__main__":
    main()