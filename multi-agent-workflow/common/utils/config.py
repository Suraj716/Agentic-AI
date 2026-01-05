"""
Configuration utilities for all agents
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_env(key: str, default: str = None) -> str:
    """Get environment variable with optional default"""
    value = os.getenv(key, default)
    if value is None:
        raise ValueError(f"Environment variable {key} is required")
    return value

def get_env_int(key: str, default: int = None) -> int:
    """Get environment variable as integer"""
    value = os.getenv(key)
    if value is None and default is not None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValueError(f"Environment variable {key} must be an integer")

def get_env_bool(key: str, default: bool = False) -> bool:
    """Get environment variable as boolean"""
    value = os.getenv(key)
    if value is None:
        return default
    return value.lower() in ('true', '1', 'yes', 'y', 't')


def get_env_optional(key: str, default: str = None) -> str:
    """Get environment variable with optional default (can be None)"""
    return os.getenv(key, default)


class MCPConfig:
    """Configuration for MCP (Model Context Protocol) connections"""
    
    # Grafana MCP Configuration
    GRAFANA_URL = get_env("GRAFANA_URL", "http://localhost:3000")
    GRAFANA_API_KEY = get_env("GRAFANA_API_KEY", "")
    
    # Prometheus Configuration (if separate from Grafana)
    PROMETHEUS_URL = get_env("PROMETHEUS_URL", "http://localhost:9090")
    
    # SSL Configuration
    SSL_VERIFY = get_env_bool("SSL_VERIFY", False)  # Default to False for self-signed certs
    SSL_CERT_PATH = get_env_optional("SSL_CERT_PATH", None)
    SSL_KEY_PATH = get_env_optional("SSL_KEY_PATH", None)
    SSL_CA_PATH = get_env_optional("SSL_CA_PATH", None)
    
    # MCP Server Configuration
    MCP_SERVER_HOST = get_env("MCP_SERVER_HOST", "localhost")
    MCP_SERVER_PORT = get_env_int("MCP_SERVER_PORT", 8089)
    
    # Connection settings
    MCP_TIMEOUT = get_env_int("MCP_TIMEOUT", 30)