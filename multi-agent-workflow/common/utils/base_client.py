"""
Base LLM client for Ollama integration
"""
from typing import Optional, Dict, Any

from .config import get_env
from .logging_setup import setup_logging

logger = setup_logging(__name__)

class BaseLLMClient:
    """Base Ollama client for LLM interactions"""
    def __init__(self):
        self.api_key = get_env("OLLAMA_API_KEY")
        self.base_url = get_env("OLLAMA_BASE_URL", "https://ollama.com")
        self.model = "gpt-oss:120b"  # Default to oss-120b model
        self._llm = None  # Lazy initialization
        
    @property
    def llm(self):
        """Lazy initialization of Ollama LLM"""
        if self._llm is None:
            from langchain_ollama import OllamaLLM
            self._llm = OllamaLLM(
                model=self.model,
                base_url=self.base_url,
                headers={"Authorization": f"Bearer {self.api_key}"},
                client_kwargs={"timeout": 30.0},  # Timeout for both sync and async clients
                sync_client_kwargs={"timeout": 30.0},  # Specific timeout for sync client
                async_client_kwargs={"timeout": 30.0},  # Specific timeout for async client
                top_p=0.9  # Nucleus sampling for balance between creativity and speed
            )
        return self._llm

    def get_system_prompt(self) -> str:
        """Override this method to provide specific system prompt"""
        return "You are a helpful AI assistant."

    def format_context(self, context: Dict[str, Any]) -> str:
        """Format context for the LLM"""
        return str(context)

    async def process_query(self, query: str, context: Optional[Dict[str, Any]] = None) -> dict:
        """Base query processing - to be implemented by specific clients"""
        raise NotImplementedError("Subclasses must implement process_query")