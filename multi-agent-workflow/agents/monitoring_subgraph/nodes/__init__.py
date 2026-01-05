"""
Base node functionality for MonitoringMCP Subgraph
Contains common node patterns and base classes
"""
import asyncio
import time
from typing import Dict, Any, Optional
from ..state_schemas import MonitoringSubgraphState
from ..helpers import create_error_context, format_execution_time
from common.utils.logging_setup import setup_logging

logger = setup_logging(__name__)


class BaseNode:
    """Base class for all subgraph nodes"""
    
    def __init__(self, node_name: str):
        self.node_name = node_name
    
    def execute(self, state: MonitoringSubgraphState) -> MonitoringSubgraphState:
        """Execute the node with timing and error handling"""
        start_time = time.time()
        
        try:
            logger.info(f"🔄 Executing {self.node_name} node")
            result = self._execute_impl(state)
            
            execution_time = time.time() - start_time
            logger.info(f"✅ {self.node_name} completed in {format_execution_time(execution_time)}")
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"❌ {self.node_name} failed after {format_execution_time(execution_time)}: {e}")
            
            # Add error to state
            if "errors" not in state:
                state["errors"] = []
            
            state["errors"].append(str(e))
            state["failed_at_node"] = self.node_name
            state["error_type"] = type(e).__name__.lower()
            
            return state
    
    def _execute_impl(self, state: MonitoringSubgraphState) -> MonitoringSubgraphState:
        """Implementation to be overridden by subclasses"""
        raise NotImplementedError("Subclasses must implement _execute_impl")


class AsyncBaseNode(BaseNode):
    """Base class for async nodes"""
    
    async def execute_async(self, state: MonitoringSubgraphState) -> MonitoringSubgraphState:
        """Execute the async node with timing and error handling"""
        start_time = time.time()
        
        try:
            logger.info(f"🔄 Executing async {self.node_name} node")
            result = await self._execute_async_impl(state)
            
            execution_time = time.time() - start_time
            logger.info(f"✅ {self.node_name} completed in {format_execution_time(execution_time)}")
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"❌ {self.node_name} failed after {format_execution_time(execution_time)}: {e}")
            
            # Add error to state
            if "errors" not in state:
                state["errors"] = []
            
            state["errors"].append(str(e))
            state["failed_at_node"] = self.node_name
            state["error_type"] = type(e).__name__.lower()
            
            return state
    
    async def _execute_async_impl(self, state: MonitoringSubgraphState) -> MonitoringSubgraphState:
        """Async implementation to be overridden by subclasses"""
        raise NotImplementedError("Subclasses must implement _execute_async_impl")


def validate_state_structure(state: MonitoringSubgraphState, required_fields: list) -> bool:
    """Validate that state has required fields"""
    try:
        for field in required_fields:
            if field not in state:
                logger.error(f"Missing required field in state: {field}")
                return False
        return True
    except Exception as e:
        logger.error(f"Error validating state structure: {e}")
        return False


def safe_get_config_value(state: MonitoringSubgraphState, key: str, default: Any) -> Any:
    """Safely get configuration value with fallback"""
    try:
        return state.get("config", {}).get(key, default)
    except Exception:
        return default


def update_llm_decisions(state: MonitoringSubgraphState, node_name: str, decision: str) -> None:
    """Update LLM decisions tracking in state"""
    if "llm_decisions" not in state:
        state["llm_decisions"] = {}
    state["llm_decisions"][node_name] = decision