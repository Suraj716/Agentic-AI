"""
Configuration module for MonitoringMCP Subgraph
Contains all configuration classes and default settings
"""
from typing import Dict, Any


class MonitoringSubgraphConfig:
    """Configuration class for MonitoringMCP subgraph with sensible defaults"""
    
    def __init__(self, **kwargs):
        # LLM Configuration
        self.llm_model = kwargs.get("llm_model", "gpt-4")
        self.llm_temperature = kwargs.get("llm_temperature", 0.7)
        self.max_llm_tokens = kwargs.get("max_llm_tokens", 400)
        
        # Timeout Configuration
        self.llm_timeout = kwargs.get("llm_timeout", 30)  # seconds
        self.mcp_timeout = kwargs.get("mcp_timeout", 45)  # seconds
        self.total_timeout = kwargs.get("total_timeout", 90)  # seconds
        
        # Tool Execution Configuration
        self.max_parallel_tools = kwargs.get("max_parallel_tools", 3)
        self.enable_tool_retry = kwargs.get("enable_tool_retry", False)
        self.retry_attempts = kwargs.get("retry_attempts", 1)
        
        # Response Configuration  
        self.max_response_length = kwargs.get("max_response_length", 2000)
        self.include_debug_info = kwargs.get("include_debug_info", False)
        
        # Error Handling Configuration
        self.fail_fast = kwargs.get("fail_fast", True)
        self.log_errors = kwargs.get("log_errors", True)

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary for state storage"""
        return {
            "llm_model": self.llm_model,
            "llm_temperature": self.llm_temperature,
            "max_llm_tokens": self.max_llm_tokens,
            "llm_timeout": self.llm_timeout,
            "mcp_timeout": self.mcp_timeout,
            "total_timeout": self.total_timeout,
            "max_parallel_tools": self.max_parallel_tools,
            "enable_tool_retry": self.enable_tool_retry,
            "retry_attempts": self.retry_attempts,
            "max_response_length": self.max_response_length,
            "include_debug_info": self.include_debug_info,
            "fail_fast": self.fail_fast,
            "log_errors": self.log_errors
        }

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'MonitoringSubgraphConfig':
        """Create config instance from dictionary"""
        return cls(**config_dict)

    def validate(self) -> bool:
        """Validate configuration values"""
        try:
            assert self.llm_timeout > 0, "LLM timeout must be positive"
            assert self.mcp_timeout > 0, "MCP timeout must be positive"
            assert self.total_timeout > 0, "Total timeout must be positive"
            assert self.max_parallel_tools > 0, "Max parallel tools must be positive"
            assert self.max_llm_tokens > 0, "Max LLM tokens must be positive"
            assert 0 <= self.llm_temperature <= 2, "LLM temperature must be between 0 and 2"
            return True
        except AssertionError as e:
            raise ValueError(f"Invalid configuration: {e}")


# Default configurations for different use cases
DEFAULT_CONFIG = MonitoringSubgraphConfig()

FAST_CONFIG = MonitoringSubgraphConfig(
    llm_timeout=15,
    mcp_timeout=20,
    total_timeout=45,
    max_llm_tokens=200
)

COMPREHENSIVE_CONFIG = MonitoringSubgraphConfig(
    llm_timeout=60,
    mcp_timeout=120,
    total_timeout=300,
    max_parallel_tools=5,
    max_llm_tokens=800,
    include_debug_info=True
)

DEVELOPMENT_CONFIG = MonitoringSubgraphConfig(
    llm_timeout=10,
    mcp_timeout=15,
    total_timeout=30,
    include_debug_info=True,
    log_errors=True
)