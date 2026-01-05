"""
MCP Client for connecting to Grafana and other monitoring services
Uses the official mcp package for Model Context Protocol communication
"""
import asyncio
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

try:
    import mcp
    from mcp.client.stdio import stdio_client
    from mcp.client.sse import sse_client
    from mcp.types import CallToolRequest, ListToolsRequest
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

from .logging_setup import setup_logging
from .config import MCPConfig

logger = setup_logging(__name__)


class MCPGrafanaClient:
    """MCP client for connecting to Grafana monitoring services"""
    
    def __init__(self, grafana_url: str = None, api_key: str = None):
        self.grafana_url = grafana_url or MCPConfig.GRAFANA_URL
        self.api_key = api_key or MCPConfig.GRAFANA_API_KEY
        self.client = None
        self.connected = False
        
    def _get_http_client_kwargs(self) -> Dict[str, Any]:
        """Get HTTP client configuration with SSL settings"""
        kwargs = {
            "timeout": MCPConfig.MCP_TIMEOUT,
            "verify": MCPConfig.SSL_VERIFY
        }
        
        # If SSL verification is enabled and custom cert paths are provided
        if MCPConfig.SSL_VERIFY and MCPConfig.SSL_CERT_PATH:
            if MCPConfig.SSL_KEY_PATH:
                kwargs["cert"] = (MCPConfig.SSL_CERT_PATH, MCPConfig.SSL_KEY_PATH)
            else:
                kwargs["cert"] = MCPConfig.SSL_CERT_PATH
        
        # Custom CA certificate
        if MCPConfig.SSL_CA_PATH:
            kwargs["verify"] = MCPConfig.SSL_CA_PATH
        
        logger.debug(f"HTTP client SSL settings: verify={kwargs['verify']}")
        return kwargs
        
    async def connect(self):
        """Connect to the Grafana MCP server"""
        try:
            logger.info("Attempting to connect to Grafana MCP server...")
            
            # Check if Grafana is accessible
            if await self._test_grafana_connection():
                self.connected = True
                logger.info("✅ Successfully connected to Grafana MCP server")
                return True
            else:
                logger.warning("⚠️ Could not connect to Grafana")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to connect to Grafana MCP server: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from the MCP server"""
        try:
            if self.client:
                # In a real MCP implementation, this would close the client connection
                pass
            self.connected = False
            logger.debug("Disconnected from MCP server")
        except Exception as e:
            logger.error(f"Error disconnecting: {e}")
    
    async def _test_grafana_connection(self) -> bool:
        """Test if Grafana is accessible"""
        try:
            import httpx
            
            if not self.grafana_url or not self.api_key:
                logger.warning("Grafana URL or API key not configured")
                return False
                
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            http_kwargs = self._get_http_client_kwargs()
            async with httpx.AsyncClient(**http_kwargs) as client:
                response = await client.get(f"{self.grafana_url}/api/health", headers=headers)
                if response.status_code == 200:
                    logger.info("Grafana health check passed")
                    return True
                else:
                    logger.warning(f"Grafana health check failed: {response.status_code}")
                    return False
                    
        except Exception as e:
            logger.warning(f"Grafana connection test failed: {e}")
            return False

    # ------------------------------------------------------------------
    # Tool Invocation Layer (bridging monitoring_tools.py wrappers)
    # ------------------------------------------------------------------
    def _normalize_relative_time(self, value: str) -> Optional[str]:
        """Convert relative token like now-5m or now to RFC3339 UTC timestamp."""
        if not isinstance(value, str):
            return value
        value = value.strip()
        from datetime import datetime, timedelta, timezone
        if value == "now":
            return datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')
        if value.startswith("now-"):
            try:
                part = value[4:]  # after now-
                num = int(''.join(ch for ch in part if ch.isdigit()))
                unit = ''.join(ch for ch in part if ch.isalpha())
                delta = timedelta()
                if unit == 's':
                    delta = timedelta(seconds=num)
                elif unit == 'm':
                    delta = timedelta(minutes=num)
                elif unit == 'h':
                    delta = timedelta(hours=num)
                elif unit == 'd':
                    delta = timedelta(days=num)
                elif unit == 'w':
                    delta = timedelta(weeks=num)
                ts = datetime.now(timezone.utc) - delta
                return ts.isoformat(timespec='seconds').replace('+00:00', 'Z')
            except Exception:
                return value  # leave unchanged on parse failure
        return value

    def _step_to_seconds(self, step: str) -> str:
        """Convert step strings like '15s', '5m' to integer seconds string."""
        if isinstance(step, (int, float)):
            return str(int(step))
        if not isinstance(step, str):
            return '15'
        step = step.strip()
        if step.isdigit():
            return step
        try:
            num = int(''.join(ch for ch in step if ch.isdigit()))
            unit = ''.join(ch for ch in step if ch.isalpha()) or 's'
            mult = {'s':1,'m':60,'h':3600,'d':86400,'w':604800}.get(unit,1)
            return str(num * mult)
        except Exception:
            return '15'

    def _parse_wrapper_output(self, raw) -> Any:
        """Parse JSON string output from monitoring_tools wrappers into Python object."""
        if isinstance(raw, str):
            try:
                return json.loads(raw)
            except Exception:
                return {"raw": raw}
        return raw

    async def _invoke_tool(self, name: str, **params) -> Any:
        """Internal unified invocation: imports monitoring_tools and calls matching wrapper.

        Applies time normalization for Prometheus range queries.
        """
        try:
            from tools import monitoring_tools as mt
        except Exception as e:
            raise RuntimeError(f"monitoring_tools import failed: {e}")
        fn = getattr(mt, name, None)
        # Normalize time params BEFORE early exits so we log transformed values if needed
        if name == 'execute_range_query':
            if 'start' in params:
                params['start'] = self._normalize_relative_time(params['start'])
            if 'end' in params:
                params['end'] = self._normalize_relative_time(params['end'])
            if 'step' in params:
                params['step'] = self._step_to_seconds(params['step'])
        if name == 'execute_query' and 'time' in params:
            params['time'] = self._normalize_relative_time(params['time'])

        if fn is None:
            raise RuntimeError(f"tool_wrapper_not_found:{name}")
        # Support LangChain Tool objects that may expose run/invoke only
        try:
            if callable(fn):
                raw = fn(**params) if params else fn()
            elif hasattr(fn, 'invoke') and callable(getattr(fn, 'invoke')):
                raw = fn.invoke(params if params else {})
            elif hasattr(fn, 'run') and callable(getattr(fn, 'run')):
                # BaseTool.run expects a single tool_input argument
                raw = fn.run(params if params else {})
            else:
                raise RuntimeError(f"tool_not_callable:{name}:{type(fn)}")
        except Exception as e:
            raise RuntimeError(f"wrapper_execution_failed:{name}:{e}")
        parsed = self._parse_wrapper_output(raw)
        # Bubble underlying tool errors to caller so execute_single_tool can capture
        if isinstance(parsed, dict) and 'error' in parsed:
            raise RuntimeError(f"tool_error:{name}:{parsed.get('error')}")
        return parsed

    # ------------------------------------------------------------------
    # Exposed async methods matching tool names (for execute_single_tool)
    # Each returns parsed Python object (dict/list) or error dict.
    # ------------------------------------------------------------------
    async def search_dashboards(self, query: str = "", tag: Optional[List[str]] = None, type: str = "dash-db"):
        return await self._invoke_tool('search_dashboards', query=query, tag=tag, type=type)

    async def get_dashboard_by_uid(self, uid: str):
        return await self._invoke_tool('get_dashboard_by_uid', uid=uid)

    async def get_dashboard_summary(self, uid: str):
        return await self._invoke_tool('get_dashboard_summary', uid=uid)

    async def get_dashboard_property(self, uid: str, jsonpath: str):
        return await self._invoke_tool('get_dashboard_property', uid=uid, jsonpath=jsonpath)

    async def update_dashboard(self, dashboard: Dict[str, Any], folderUid: Optional[str] = None, message: Optional[str] = None):
        return await self._invoke_tool('update_dashboard', dashboard=dashboard, folderUid=folderUid, message=message)

    async def patch_dashboard(self, uid: str, patches: List[Dict[str, Any]]):
        return await self._invoke_tool('patch_dashboard', uid=uid, patches=patches)

    async def get_dashboard_panel_queries(self, uid: str):
        return await self._invoke_tool('get_dashboard_panel_queries', uid=uid)

    async def list_datasources(self):
        return await self._invoke_tool('list_datasources')

    async def get_datasource_by_uid(self, uid: str):
        return await self._invoke_tool('get_datasource_by_uid', uid=uid)

    async def get_datasource_by_name(self, name: str):
        return await self._invoke_tool('get_datasource_by_name', name=name)

    async def list_alert_rules(self, dashboardUid: Optional[str] = None, folderUid: Optional[str] = None):
        return await self._invoke_tool('list_alert_rules', dashboardUid=dashboardUid, folderUid=folderUid)

    async def get_alert_rule_by_uid(self, uid: str):
        return await self._invoke_tool('get_alert_rule_by_uid', uid=uid)

    async def list_contact_points(self):
        return await self._invoke_tool('list_contact_points')

    async def generate_deeplink(self, resourceType: str, uid: Optional[str] = None, panelId: Optional[int] = None, from_ts: Optional[str] = None, to_ts: Optional[str] = None):
        return await self._invoke_tool('generate_deeplink', resourceType=resourceType, uid=uid, panelId=panelId, from_ts=from_ts, to_ts=to_ts)

    async def list_teams(self):
        return await self._invoke_tool('list_teams')

    async def list_users_by_org(self):
        return await self._invoke_tool('list_users_by_org')

    async def get_annotations(self, dashboardUid: Optional[str] = None, tags: Optional[List[str]] = None, from_ts: Optional[str] = None, to_ts: Optional[str] = None):
        return await self._invoke_tool('get_annotations', dashboardUid=dashboardUid, tags=tags, from_ts=from_ts, to_ts=to_ts)

    async def get_assertions(self, entityId: str):
        return await self._invoke_tool('get_assertions', entityId=entityId)

    async def execute_query(self, query: str, time: Optional[str] = None):
        return await self._invoke_tool('execute_query', query=query, time=time)

    async def execute_range_query(self, query: str, start: str, end: str, step: str):
        return await self._invoke_tool('execute_range_query', query=query, start=start, end=end, step=step)

    async def list_metrics(self):
        return await self._invoke_tool('list_metrics')

    async def get_metric_metadata(self, metric: str):
        return await self._invoke_tool('get_metric_metadata', metric=metric)

    async def get_targets(self):
        return await self._invoke_tool('get_targets')

    async def health_check(self):
        return await self._invoke_tool('health_check')

    async def grafana_health_check(self):
        return await self._invoke_tool('grafana_health_check')

    async def show_monitoring_environment(self):
        return await self._invoke_tool('show_monitoring_environment')

    
    
    
    
    # async def get_dashboards(self) -> List[Dict[str, Any]]:
    #     """Get all dashboards from Grafana"""
    #     try:
    #         if not self.connected:
    #             await self.connect()
            
    #         if self.connected:
    #             return await self._fetch_real_dashboards()
    #         else:
    #             raise ConnectionError(
    #                 f"Cannot connect to Grafana at {self.grafana_url}. "
    #                 f"Please check: 1) Grafana server is running, "
    #                 f"2) URL is correct, 3) API key has permissions, "
    #                 f"4) SSL configuration if using HTTPS"
    #             )
                
    #     except ConnectionError:
    #         raise
    #     except Exception as e:
    #         logger.error(f"Error getting dashboards: {e}")
    #         raise RuntimeError(f"Failed to retrieve dashboards from Grafana: {e}")
    
    # async def _fetch_real_dashboards(self) -> List[Dict[str, Any]]:
    #     """Fetch real dashboards from Grafana API"""
    #     try:
    #         import httpx
            
    #         headers = {
    #             "Authorization": f"Bearer {self.api_key}",
    #             "Content-Type": "application/json"
    #         }
            
    #         http_kwargs = self._get_http_client_kwargs()
    #         async with httpx.AsyncClient(**http_kwargs) as client:
    #             response = await client.get(f"{self.grafana_url}/api/search", headers=headers)
                
    #             if response.status_code == 200:
    #                 dashboards = response.json()
    #                 logger.info(f"Fetched {len(dashboards)} dashboards from Grafana")
    #                 return dashboards
    #             else:
    #                 raise ConnectionError(
    #                     f"Grafana API returned status {response.status_code}. "
    #                     f"Please check API key permissions and Grafana server status."
    #                 )
                    
    #     except ConnectionError:
    #         raise
    #     except Exception as e:
    #         logger.error(f"Error fetching real dashboards: {e}")
    #         raise RuntimeError(f"Failed to fetch dashboards from Grafana API: {e}")
    
    # async def search_dashboards(self, query: str) -> List[Dict[str, Any]]:
    #     """Search for dashboards matching a query"""
    #     try:
    #         all_dashboards = await self.get_dashboards()
    #         query_lower = query.lower()
            
    #         matching_dashboards = []
    #         for dashboard in all_dashboards:
    #             title = dashboard.get('title', '').lower()
    #             tags = [tag.lower() for tag in dashboard.get('tags', [])]
    #             description = dashboard.get('description', '').lower()
                
    #             if (query_lower in title or
    #                 any(query_lower in tag for tag in tags) or
    #                 query_lower in description):
    #                 matching_dashboards.append(dashboard)
            
    #         logger.info(f"Found {len(matching_dashboards)} dashboards matching '{query}'")
    #         return matching_dashboards
            
    #     except Exception as e:
    #         logger.error(f"Error searching dashboards: {e}")
    #         raise RuntimeError(f"Failed to search dashboards for query '{query}': {e}")
    
    # async def get_dashboard_data(self, dashboard_uid: str) -> Dict[str, Any]:
    #     """Get detailed data for a specific dashboard"""
    #     try:
    #         if not self.connected:
    #             await self.connect()
            
    #         if self.connected:
    #             return await self._fetch_real_dashboard_data(dashboard_uid)
    #         else:
    #             raise ConnectionError(
    #                 f"Cannot connect to Grafana at {self.grafana_url}. "
    #                 f"Please check Grafana server accessibility and API key permissions."
    #             )
                
    #     except ConnectionError:
    #         raise
    #     except Exception as e:
    #         logger.error(f"Error getting dashboard data for {dashboard_uid}: {e}")
    #         raise RuntimeError(f"Failed to get dashboard data for '{dashboard_uid}': {e}")
    
    # async def _fetch_real_dashboard_data(self, dashboard_uid: str) -> Dict[str, Any]:
    #     """Fetch real dashboard data from Grafana API"""
    #     try:
    #         import httpx
            
    #         headers = {
    #             "Authorization": f"Bearer {self.api_key}",
    #             "Content-Type": "application/json"
    #         }
            
    #         http_kwargs = self._get_http_client_kwargs()
    #         async with httpx.AsyncClient(**http_kwargs) as client:
    #             response = await client.get(
    #                 f"{self.grafana_url}/api/dashboards/uid/{dashboard_uid}",
    #                 headers=headers
    #             )
                
    #             if response.status_code == 200:
    #                 dashboard_data = response.json()
    #                 logger.info(f"Fetched dashboard data for {dashboard_uid}")
    #                 return dashboard_data
    #             else:
    #                 raise ConnectionError(
    #                     f"Grafana API returned status {response.status_code} for dashboard {dashboard_uid}. "
    #                     f"Please check if dashboard exists and API key has permissions."
    #                 )
                    
    #     except ConnectionError:
    #         raise
    #     except Exception as e:
    #         logger.error(f"Error fetching real dashboard data: {e}")
    #         raise RuntimeError(f"Failed to fetch dashboard data from Grafana API: {e}")
    
    # async def get_available_metrics(self) -> List[str]:
    #     """Get list of available metrics"""
    #     try:
    #         if not self.connected:
    #             await self.connect()
            
    #         if not self.connected:
    #             raise ConnectionError(
    #                 f"Cannot connect to Grafana at {self.grafana_url}. "
    #                 f"Please check Grafana server accessibility and configuration."
    #             )
            
    #         # For now, return a basic list since this would typically come from datasources
    #         # In a real implementation, this would query Grafana's datasources for available metrics
    #         return [
    #             "cpu_usage_percent",
    #             "memory_usage_percent", 
    #             "disk_usage_percent",
    #             "network_bytes_total",
    #             "http_requests_total",
    #             "response_time_seconds",
    #             "error_rate_percent",
    #             "uptime_seconds",
    #             "active_connections",
    #             "database_connections"
    #         ]
            
    #     except ConnectionError:
    #         raise
    #     except Exception as e:
    #         logger.error(f"Error getting available metrics: {e}")
    #         raise RuntimeError(f"Failed to get available metrics from Grafana: {e}")

    # # (Mock mode removed)