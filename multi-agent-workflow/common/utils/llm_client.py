"""
Simple LLM client for multi-agent workflow
Provides basic completion functionality for monitoring and other agents
"""
from typing import Optional, Dict, Any
import os
import asyncio
from langchain_ollama import OllamaLLM

from .logging_setup import setup_logging

logger = setup_logging(__name__)


class LLMClient:
    """Simple LLM client for getting completions from Ollama API"""
    
    def __init__(self, model: str = None, api_key: Optional[str] = None, base_url: Optional[str] = None):
        """Initialize LLM client with model and API configuration"""
        # Use environment variables for Ollama configuration
        self.model = model or os.getenv("MODEL_NAME", "gpt-oss:120b")
        
        # Get API key from environment or parameter (try both OLLAMA_API_KEY and OPENAI_API_KEY)
        self.api_key = api_key or os.getenv("OLLAMA_API_KEY") or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            logger.warning("⚠️ No API key found (checked OLLAMA_API_KEY and OPENAI_API_KEY). LLM functionality will be limited.")
            self.client = None
            return
        
        # Get base URL from environment (original behavior)
        self.base_url = base_url or os.getenv("OLLAMA_BASE_URL", "https://ollama.com")
        
        # Initialize LangChain OllamaLLM (uses /api/generate endpoint)
        try:
            self.client = OllamaLLM(
                model=self.model,
                base_url=self.base_url,
                headers={"Authorization": f"Bearer {self.api_key}"},
                client_kwargs={"timeout": 30.0},
                sync_client_kwargs={"timeout": 30.0},
                async_client_kwargs={"timeout": 30.0},
                top_p=0.9
            )
            logger.info(f"✅ LLM client initialized with model: {self.model}, base_url: {self.base_url}")
        except Exception as e:
            logger.error(f"❌ Failed to initialize LLM client: {e}")
            self.client = None
    
    def is_functional(self) -> bool:
        """Check if the LLM client is functional"""
        return self.client is not None
    
    async def ensure_healthy(self):
        """Ensure the LLM client is healthy and ready for requests"""
        if not self.client:
            logger.warning("⚠️ LLM client not initialized, attempting to reinitialize")
            self._reinitialize_client()
            return
        
        try:
            # Check if event loop is available and running
            loop = asyncio.get_running_loop()
            if loop.is_closed():
                logger.warning("⚠️ Event loop is closed, reinitializing client")
                self._reinitialize_client()
        except RuntimeError:
            # No running loop - this is fine for new requests
            pass
    
    async def get_completion(self, prompt: str, temperature: float = 0.7, max_tokens: int = 2000) -> str:
        """Get completion from Ollama API for the given prompt"""
        if not self.client:
            logger.error("❌ LLM client not available")
            raise RuntimeError("LLM client not initialized - check API key configuration")
        
        try:
            # Check if we have a running event loop
            try:
                loop = asyncio.get_running_loop()
                if loop.is_closed():
                    logger.warning("⚠️ Event loop is closed, recreating LLM client")
                    self._reinitialize_client()
            except RuntimeError:
                # No running loop, which is fine for new requests
                pass
            
            # Use LangChain OllamaLLM's async invoke method
            completion = await self.client.ainvoke(prompt)
            
            logger.debug(f"🧠 LLM completion generated (length: {len(completion)})")
            return completion.strip()
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ Error getting LLM completion: {e}")
            
            # If it's an event loop issue, try to reinitialize and retry once
            if "loop" in error_msg.lower() or "closed" in error_msg.lower():
                logger.info("🔄 Attempting to reinitialize LLM client due to event loop issue")
                try:
                    self._reinitialize_client()
                    completion = await self.client.ainvoke(prompt)
                    logger.debug(f"🧠 LLM completion generated after reinit (length: {len(completion)})")
                    return completion.strip()
                except Exception as retry_error:
                    logger.error(f"❌ Retry failed: {retry_error}")
                    raise RuntimeError(f"LLM completion failed after retry: {str(retry_error)}")
            
            raise RuntimeError(f"LLM completion failed: {str(e)}")
    
    def _reinitialize_client(self):
        """Reinitialize the LLM client (useful for event loop issues)"""
        try:
            logger.info("🔄 Reinitializing LLM client...")
            self.client = OllamaLLM(
                model=self.model,
                base_url=self.base_url,
                headers={"Authorization": f"Bearer {self.api_key}"},
                client_kwargs={"timeout": 30.0},
                sync_client_kwargs={"timeout": 30.0},
                async_client_kwargs={"timeout": 30.0},
                top_p=0.9
            )
            logger.info("✅ LLM client reinitialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to reinitialize LLM client: {e}")
            self.client = None
    
    def get_completion_sync(self, prompt: str, temperature: float = 0.7, max_tokens: int = 2000) -> str:
        """Synchronous wrapper for get_completion"""
        if not self.client:
            logger.error("❌ LLM client not available")
            raise RuntimeError("LLM client not initialized - check API key configuration")
        
        try:
            # Use LangChain OllamaLLM's synchronous invoke method
            completion = self.client.invoke(prompt)
            logger.debug(f"🧠 LLM completion generated (length: {len(completion)})")
            return completion.strip()
            
        except Exception as e:
            logger.error(f"❌ Error getting LLM completion: {e}")
            raise RuntimeError(f"LLM completion failed: {str(e)}")
    
    async def analyze_query(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Analyze a query and return structured analysis"""
        context_str = ""
        if context:
            context_str = f"\nContext: {context}"
        
        analysis_prompt = f"""Analyze this query and provide a structured response:

Query: "{query}"{context_str}

Provide analysis in the following format:
- Intent: What is the user trying to accomplish?
- Category: What category does this fall into?
- Confidence: How confident are you in this analysis (0.0-1.0)?
- Suggested approach: What approach would be best?

Respond in JSON format with keys: intent, category, confidence, approach"""

        try:
            response = await self.get_completion(analysis_prompt)
            # Try to parse as JSON, fallback to structured text if needed
            import json
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                # Fallback to basic analysis
                return {
                    "intent": "unknown",
                    "category": "general",
                    "confidence": 0.5,
                    "approach": "basic_response",
                    "raw_response": response
                }
        except Exception as e:
            logger.error(f"❌ Error in query analysis: {e}")
            return {
                "intent": "unknown",
                "category": "general",
                "confidence": 0.0,
                "approach": "error_handling",
                "error": str(e)
            }
    
    def is_available(self) -> bool:
        """Check if LLM client is available"""
        return self.client is not None
    
    def get_model(self) -> str:
        """Get current model name"""
        return self.model


# Backward compatibility alias
class ReActLLMClient(LLMClient):
    """Alias for backward compatibility with existing code"""
    pass


# Factory function for easy instantiation
def create_llm_client(model: str = "gpt-4", api_key: Optional[str] = None, base_url: Optional[str] = None) -> LLMClient:
    """Create and return a configured LLM client"""
    return LLMClient(model=model, api_key=api_key, base_url=base_url)


__all__ = ["LLMClient", "ReActLLMClient", "create_llm_client"]