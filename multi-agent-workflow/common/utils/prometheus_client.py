"""
Prometheus Client for direct Prometheus API access
"""
import asyncio
import httpx
from typing import Dict, Any, List, Optional
from datetime import datetime

from .logging_setup import setup_logging
from .config import MCPConfig

logger = setup_logging(__name__)


class PrometheusClient:
    """Client for direct Prometheus API access"""
    
    def __init__(self, prometheus_url: str = None):
        self.prometheus_url = prometheus_url or MCPConfig.PROMETHEUS_URL
        self.connected = False
        
    async def connect(self) -> bool:
        """Test connection to Prometheus"""
        try:
            if not self.prometheus_url:
                logger.warning("Prometheus URL not configured")
                return False
                
            logger.info("Testing Prometheus connectivity...")
            
            # Prometheus typically doesn't need SSL verification (HTTP endpoint)
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.prometheus_url}/api/v1/query", 
                                          params={"query": "up"})
                
                if response.status_code == 200:
                    logger.info("✅ Prometheus connection successful")
                    self.connected = True
                    return True
                else:
                    logger.warning(f"⚠️ Prometheus returned status {response.status_code}")
                    return False
                    
        except Exception as e:
            logger.warning(f"❌ Prometheus connection failed: {e}")
            return False
    
    async def query(self, query: str, time: str = None) -> Dict[str, Any]:
        """Execute a Prometheus query"""
        try:
            if not self.connected:
                await self.connect()
            
            if not self.connected:
                raise ConnectionError(
                    f"Cannot connect to Prometheus at {self.prometheus_url}. "
                    f"Please check: 1) Prometheus server is running, "
                    f"2) URL is correct, 3) Network connectivity"
                )
            
            params = {"query": query}
            if time:
                params["time"] = time
                
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.prometheus_url}/api/v1/query", 
                                          params=params)
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"Prometheus query executed: {query}")
                    return result
                else:
                    raise ConnectionError(
                        f"Prometheus API returned status {response.status_code} for query '{query}'. "
                        f"Please check query syntax and Prometheus server status."
                    )
                    
        except ConnectionError:
            raise
        except Exception as e:
            logger.error(f"Error executing Prometheus query: {e}")
            raise RuntimeError(f"Failed to execute Prometheus query '{query}': {e}")
    
    async def query_range(self, query: str, start: str, end: str, step: str) -> Dict[str, Any]:
        """Execute a Prometheus range query"""
        try:
            if not self.connected:
                await self.connect()
            
            if not self.connected:
                raise ConnectionError(
                    f"Cannot connect to Prometheus at {self.prometheus_url}. "
                    f"Please check Prometheus server accessibility."
                )
            
            params = {
                "query": query,
                "start": start,
                "end": end,
                "step": step
            }
                
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.prometheus_url}/api/v1/query_range", 
                                          params=params)
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"Prometheus range query executed: {query}")
                    return result
                else:
                    raise ConnectionError(
                        f"Prometheus API returned status {response.status_code} for range query '{query}'. "
                        f"Please check query parameters and Prometheus server status."
                    )
                    
        except ConnectionError:
            raise
        except Exception as e:
            logger.error(f"Error executing Prometheus range query: {e}")
            raise RuntimeError(f"Failed to execute Prometheus range query '{query}': {e}")
    
    async def get_metrics(self) -> List[str]:
        """Get list of available metrics"""
        try:
            if not self.connected:
                await self.connect()
            
            if not self.connected:
                raise ConnectionError(
                    f"Cannot connect to Prometheus at {self.prometheus_url}. "
                    f"Please check Prometheus server accessibility."
                )
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.prometheus_url}/api/v1/label/__name__/values")
                
                if response.status_code == 200:
                    result = response.json()
                    metrics = result.get("data", [])
                    logger.info(f"Retrieved {len(metrics)} metrics from Prometheus")
                    return metrics
                else:
                    raise ConnectionError(
                        f"Prometheus API returned status {response.status_code} when getting metrics. "
                        f"Please check Prometheus server status."
                    )
                    
        except ConnectionError:
            raise
        except Exception as e:
            logger.error(f"Error getting Prometheus metrics: {e}")
            raise RuntimeError(f"Failed to get metrics from Prometheus: {e}")
    
    async def get_targets(self) -> Dict[str, Any]:
        """Get Prometheus targets"""
        try:
            if not self.connected:
                await self.connect()
            
            if not self.connected:
                raise ConnectionError(
                    f"Cannot connect to Prometheus at {self.prometheus_url}. "
                    f"Please check Prometheus server accessibility."
                )
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.prometheus_url}/api/v1/targets")
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info("Retrieved Prometheus targets")
                    return result
                else:
                    raise ConnectionError(
                        f"Prometheus API returned status {response.status_code} when getting targets. "
                        f"Please check Prometheus server status."
                    )
                    
        except ConnectionError:
            raise
        except Exception as e:
            logger.error(f"Error getting Prometheus targets: {e}")
            raise RuntimeError(f"Failed to get targets from Prometheus: {e}")