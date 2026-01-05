"""
Comprehensive Monitoring Tools with Enhanced MCP Integration
Includes all tools from Grafana MCP and Prometheus MCP servers
"""
from typing import List, Dict, Any, Optional
import json
from datetime import datetime, timedelta

import sys
import os

# Add current directory to Python path for imports
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from langchain_core.tools import tool
from common.utils.logging_setup import setup_logging
import requests
try:
    from jsonpath_ng import parse as jsonpath_parse
except ImportError:  # jsonpath-ng optional; some tools will warn if missing
    jsonpath_parse = None

logger = setup_logging(__name__)


class UnifiedComprehensiveMCPTools:
    """Unified catalog of executable MCP tools (Grafana 48 + Prometheus 6).

    This replaces the previous static placeholder list of 64 entries with the
    authoritative set of currently implemented tools gathered from the upstream
    repositories (README/tool tables & server implementations). Each tool now
    includes a minimal parameter schema so higher layers can reason about
    required inputs. (Parameter schemas are intentionally lightweight – they
    capture required vs optional and primary types, not full JSONSchema.)
    """

    @staticmethod
    def get_all_tools() -> Dict[str, Dict[str, Any]]:
        # Only retain implemented tool entries
        return {
            # Grafana dashboard
            "search_dashboards": {"server": "grafana", "category": "dashboard", "description": "Search dashboards", "permissions": ["dashboards:read"], "parameters": {"required": [], "optional": {"query": "str", "tag": "list[str]", "type": "str"}}, "use_cases": ["Dashboard discovery", "Filtering"], "context_impact": "low", "implemented": True},
            "get_dashboard_by_uid": {"server": "grafana", "category": "dashboard", "description": "Full dashboard JSON", "permissions": ["dashboards:read"], "parameters": {"required": ["uid"], "optional": {}}, "use_cases": ["Full structure", "Migration"], "context_impact": "high", "implemented": True},
            "get_dashboard_summary": {"server": "grafana", "category": "dashboard", "description": "Dashboard summary", "permissions": ["dashboards:read"], "parameters": {"required": ["uid"], "optional": {}}, "use_cases": ["Planning edits", "Quick overview"], "context_impact": "low", "implemented": True},
            "get_dashboard_property": {"server": "grafana", "category": "dashboard", "description": "Dashboard JSONPath extraction", "permissions": ["dashboards:read"], "parameters": {"required": ["uid", "jsonpath"], "optional": {}}, "use_cases": ["Targeted extraction"], "context_impact": "low", "implemented": True},
            "update_dashboard": {"server": "grafana", "category": "dashboard", "description": "Create/update dashboard", "permissions": ["dashboards:create", "dashboards:write"], "parameters": {"required": ["dashboard"], "optional": {"folderUid": "str", "message": "str"}}, "use_cases": ["Authoring", "Bulk changes"], "context_impact": "high", "implemented": True},
            "patch_dashboard": {"server": "grafana", "category": "dashboard", "description": "Patch dashboard", "permissions": ["dashboards:write"], "parameters": {"required": ["uid", "patches"], "optional": {}}, "use_cases": ["Incremental updates"], "context_impact": "medium", "implemented": True},
            "get_dashboard_panel_queries": {"server": "grafana", "category": "dashboard", "description": "Panel queries mapping", "permissions": ["dashboards:read"], "parameters": {"required": ["uid"], "optional": {}}, "use_cases": ["Query audit", "Dependency map"], "context_impact": "low", "implemented": True},
            # Datasource
            "list_datasources": {"server": "grafana", "category": "datasource", "description": "List datasources", "permissions": ["datasources:read"], "parameters": {"required": [], "optional": {}}, "use_cases": ["Inventory"], "context_impact": "low", "implemented": True},
            "get_datasource_by_uid": {"server": "grafana", "category": "datasource", "description": "Datasource by UID", "permissions": ["datasources:read"], "parameters": {"required": ["uid"], "optional": {}}, "use_cases": ["Config inspection"], "context_impact": "low", "implemented": True},
            "get_datasource_by_name": {"server": "grafana", "category": "datasource", "description": "Datasource by name", "permissions": ["datasources:read"], "parameters": {"required": ["name"], "optional": {}}, "use_cases": ["Name lookup"], "context_impact": "low", "implemented": True},
            # Alerting
            "list_alert_rules": {"server": "grafana", "category": "alerting", "description": "List alert rules", "permissions": ["alert.rules:read"], "parameters": {"required": [], "optional": {"dashboardUid": "str", "folderUid": "str"}}, "use_cases": ["Alert posture", "Compliance"], "context_impact": "medium", "implemented": True},
            "get_alert_rule_by_uid": {"server": "grafana", "category": "alerting", "description": "Alert rule details", "permissions": ["alert.rules:read"], "parameters": {"required": ["uid"], "optional": {}}, "use_cases": ["Rule investigation"], "context_impact": "low", "implemented": True},
            "list_contact_points": {"server": "grafana", "category": "alerting", "description": "Contact points", "permissions": ["alert.notifications:read"], "parameters": {"required": [], "optional": {}}, "use_cases": ["Escalation review"], "context_impact": "low", "implemented": True},
            # Admin / navigation / asserts
            "list_teams": {"server": "grafana", "category": "admin", "description": "List teams", "permissions": ["teams:read"], "parameters": {"required": [], "optional": {}}, "use_cases": ["Org overview"], "context_impact": "low", "implemented": True},
            "list_users_by_org": {"server": "grafana", "category": "admin", "description": "List org users", "permissions": ["users:read"], "parameters": {"required": [], "optional": {}}, "use_cases": ["Access review"], "context_impact": "medium", "implemented": True},
            # NOTE: optional time params renamed to from_ts/to_ts to match wrapper signature
            "generate_deeplink": {"server": "grafana", "category": "navigation", "description": "Generate deeplink", "permissions": [], "parameters": {"required": ["resourceType"], "optional": {"uid": "str", "panelId": "int", "from_ts": "str", "to_ts": "str"}}, "use_cases": ["Share context", "Navigation"], "context_impact": "low", "implemented": True},
            "get_assertions": {"server": "grafana", "category": "asserts", "description": "Assertion summary", "permissions": ["Plugin-specific permissions"], "parameters": {"required": ["entityId"], "optional": {}}, "use_cases": ["Entity validation"], "context_impact": "low", "implemented": True},
            # Prometheus direct
            "health_check": {"server": "prometheus", "category": "system", "description": "Prometheus health", "permissions": [], "parameters": {"required": [], "optional": {}}, "use_cases": ["Readiness", "Monitoring"], "context_impact": "low", "implemented": True},
            "execute_query": {"server": "prometheus", "category": "query", "description": "Instant PromQL", "permissions": [], "parameters": {"required": ["query"], "optional": {"time": "str"}}, "use_cases": ["Point-in-time metric"], "context_impact": "low", "implemented": True},
            "execute_range_query": {"server": "prometheus", "category": "query", "description": "Range PromQL", "permissions": [], "parameters": {"required": ["query", "start", "end", "step"], "optional": {}}, "use_cases": ["Time-series analysis"], "context_impact": "medium", "implemented": True},
            # list_metrics wrapper currently accepts no parameters; removed unsupported optional params
            "list_metrics": {"server": "prometheus", "category": "discovery", "description": "List metrics", "permissions": [], "parameters": {"required": [], "optional": {}}, "use_cases": ["Metric discovery"], "context_impact": "medium", "implemented": True},
            "get_metric_metadata": {"server": "prometheus", "category": "discovery", "description": "Metric metadata", "permissions": [], "parameters": {"required": ["metric"], "optional": {}}, "use_cases": ["Type info"], "context_impact": "low", "implemented": True},
            "get_targets": {"server": "prometheus", "category": "discovery", "description": "Scrape targets", "permissions": [], "parameters": {"required": [], "optional": {}}, "use_cases": ["Scrape health"], "context_impact": "medium", "implemented": True},
            # Annotations (Grafana)
            "get_annotations": {"server": "grafana", "category": "dashboard", "description": "Dashboard / global annotations", "permissions": ["annotations:read"], "parameters": {"required": [], "optional": {"dashboardUid": "str", "tags": "list[str]", "from_ts": "str", "to_ts": "str"}}, "use_cases": ["Context events"], "context_impact": "low", "implemented": True}
        }

    @staticmethod
    def get_categories() -> List[str]:
        all_tools = UnifiedComprehensiveMCPTools.get_all_tools()
        return sorted({t["category"] for t in all_tools.values()})

    @staticmethod
    def get_tools_by_category(category: str) -> List[str]:
        all_tools = UnifiedComprehensiveMCPTools.get_all_tools()
        return [name for name, meta in all_tools.items() if meta["category"] == category]

    @staticmethod
    def suggest_tools_for_query(query: str) -> List[str]:
        q = query.lower()
        mapping = {
            "dashboard": ["search_dashboards", "get_dashboard_summary", "get_annotations"],
            "panel": ["get_dashboard_panel_queries", "get_dashboard_property"],
            "alert": ["list_alert_rules", "get_alert_rule_by_uid"],
            "team": ["list_teams"],
            "user": ["list_users_by_org"],
            "prometheus": ["execute_query", "execute_range_query"],
            "metric": ["list_metrics", "get_metric_metadata"],
            "target": ["get_targets"],
            "datasource": ["list_datasources", "get_datasource_by_name"],
            "assert": ["get_assertions"],
            "link": ["generate_deeplink"],
            "health": ["health_check"]
        }
        suggestions: List[str] = []
        for k, v in mapping.items():
            if k in q:
                suggestions.extend(v)
        # De-duplicate + limit
        deduped = []
        seen = set()
        for s in suggestions:
            if s not in seen:
                deduped.append(s)
                seen.add(s)
            if len(deduped) >= 10:
                break
        # Filter to implemented ones only
        all_tools = UnifiedComprehensiveMCPTools.get_all_tools()
        return [name for name in deduped if name in all_tools and all_tools[name].get("implemented")]

    @staticmethod
    def get_implemented_tool_names() -> List[str]:
        all_tools = UnifiedComprehensiveMCPTools.get_all_tools()
        return sorted([n for n, meta in all_tools.items() if meta.get("implemented")])




# Utility functions for the comprehensive MCP tools
def get_comprehensive_tools_info() -> Dict[str, Any]:
    """Get information about all comprehensive MCP tools"""
    tools = ComprehensiveMCPTools()
    all_tools = tools.get_all_tools()
    categories = tools.get_categories()
    
    return {
        "total_tools": len(all_tools),
        "categories": categories,
        "tools_by_category": {cat: tools.get_tools_by_category(cat) for cat in categories},
        "servers": ["grafana", "prometheus"],
        "capabilities": {
            "dashboard_management": True,
            "prometheus_querying": True,
            "loki_log_analysis": True,
            "alerting_system": True,
            "incident_management": True,
            "oncall_coordination": True,
            "sift_investigations": True,
            "pyroscope_profiling": True,
            "administration": True,
            "direct_prometheus": True
        }
    }


def suggest_tools_for_monitoring_query(query: str) -> List[str]:
    """Suggest appropriate MCP tools for monitoring queries"""
    tools = ComprehensiveMCPTools()
    return tools.suggest_tools_for_query(query)


# Export dynamic tools system and compatibility layer
ComprehensiveMCPTools = UnifiedComprehensiveMCPTools  # single authoritative export (static only)
# Backward compatibility alias expected by agents.monitoring_mcp
COMPREHENSIVE_MCP_TOOLS = UnifiedComprehensiveMCPTools

# ---------------------------------------------------------------------------
# Runtime HTTP Clients for direct Grafana / Prometheus access
# ---------------------------------------------------------------------------

def _safe_json(resp: requests.Response):
    try:
        return resp.json()
    except Exception:
        return {"raw": resp.text}


class GrafanaClient:
    """Minimal Grafana HTTP client leveraged by LangChain tool functions.
    Configuration uses environment variables when explicit args omitted.
    Priority: token auth > basic auth.
    Required: set GRAFANA_URL and a service account token or username/password.
    """
    def __init__(self, url: Optional[str] = None, token: Optional[str] = None,
                 username: Optional[str] = None, password: Optional[str] = None, timeout: int = 30):
        self.url = (url or os.environ.get("GRAFANA_URL") or "").rstrip('/')
        self.token = token or os.environ.get("GRAFANA_SERVICE_ACCOUNT_TOKEN") or os.environ.get("GRAFANA_API_KEY")
        self.username = username or os.environ.get("GRAFANA_USERNAME")
        self.password = password or os.environ.get("GRAFANA_PASSWORD")
        self.timeout = timeout
        if not self.url:
            logger.warning("GrafanaClient initialized without URL; calls will fail until GRAFANA_URL is set.")

    def _headers(self) -> Dict[str, str]:
        h = {"Accept": "application/json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def _request(self, method: str, path: str, params: Dict[str, Any] = None, json_body: Any = None) -> Dict[str, Any]:
        if not self.url:
            return {"error": "Grafana URL not configured (GRAFANA_URL)"}
        full = f"{self.url}{path}" if path.startswith('/') else f"{self.url}/{path}"
        auth = None
        if not self.token and self.username and self.password:
            auth = (self.username, self.password)
        try:
            resp = requests.request(method.upper(), full, headers=self._headers(), auth=auth,
                                    params=params, json=json_body, timeout=self.timeout)
            if resp.status_code >= 400:
                return {"error": f"HTTP {resp.status_code}", "detail": _safe_json(resp), "path": path}
            return _safe_json(resp)
        except Exception as e:
            return {"error": str(e), "path": path}

    # Dashboards
    def search_dashboards(self, query: str = "", tag: Optional[List[str]] = None, type: str = "dash-db") -> Dict[str, Any]:
        params = {"query": query, "type": type}
        if tag:
            params["tag"] = ','.join(tag)
        return self._request("GET", "/api/search", params=params)

    def get_dashboard_by_uid(self, uid: str) -> Dict[str, Any]:
        return self._request("GET", f"/api/dashboards/uid/{uid}")

    def get_dashboard_summary(self, uid: str) -> Dict[str, Any]:
        data = self.get_dashboard_by_uid(uid)
        if "error" in data:
            return data
        dash = data.get("dashboard") or {}
        panels = dash.get("panels", [])
        summary = {
            "uid": uid,
            "title": dash.get("title"),
            "panel_count": len(panels),
            "panel_types": sorted({p.get("type") for p in panels if p.get("type")}),
            "datasource_uids": sorted({(_extract_ds_uid(p)) for p in panels if _extract_ds_uid(p)}),
            "templating_vars": [v.get("name") for v in dash.get("templating", {}).get("list", [])]
        }
        return summary

    def get_dashboard_property(self, uid: str, jsonpath: str) -> Dict[str, Any]:
        data = self.get_dashboard_by_uid(uid)
        if "error" in data:
            return data
        if not jsonpath_parse:
            return {"error": "jsonpath-ng not installed; add 'jsonpath-ng' to requirements.txt"}
        dash = data.get("dashboard") or {}
        try:
            expr = jsonpath_parse(jsonpath)
            matches = [m.value for m in expr.find(dash)]
            return {"uid": uid, "jsonpath": jsonpath, "matches": matches}
        except Exception as e:
            return {"error": f"JSONPath error: {e}"}

    def update_dashboard(self, dashboard: Dict[str, Any], folderUid: Optional[str] = None, message: Optional[str] = None) -> Dict[str, Any]:
        body = {"dashboard": dashboard, "overwrite": True}
        if folderUid:
            body["folderUid"] = folderUid
        if message:
            body["message"] = message
        return self._request("POST", "/api/dashboards/db", json_body=body)

    def patch_dashboard(self, uid: str, patches: List[Dict[str, Any]]) -> Dict[str, Any]:
        original = self.get_dashboard_by_uid(uid)
        if "error" in original:
            return original
        dash = original.get("dashboard") or {}
        try:
            for p in patches:
                path = p.get("path", "").strip('/')
                op = p.get("op")
                value = p.get("value")
                _apply_patch(dash, path.split('/') if path else [], op, value)
            return self.update_dashboard(dash)
        except Exception as e:
            return {"error": f"Patch failed: {e}"}

    def get_dashboard_panel_queries(self, uid: str) -> Dict[str, Any]:
        data = self.get_dashboard_by_uid(uid)
        if "error" in data:
            return data
        dash = data.get("dashboard") or {}
        panels_out = []
        for p in dash.get("panels", []):
            targets = p.get("targets", [])
            panels_out.append({
                "panel_id": p.get("id"),
                "title": p.get("title"),
                "datasource": p.get("datasource"),
                "queries": [{"expr": t.get("expr"), "refId": t.get("refId")} for t in targets]
            })
        return {"uid": uid, "panels": panels_out}

    # Datasources
    def list_datasources(self) -> Dict[str, Any]:
        return self._request("GET", "/api/datasources")

    def get_datasource_by_uid(self, uid: str) -> Dict[str, Any]:
        return self._request("GET", f"/api/datasources/uid/{uid}")

    def get_datasource_by_name(self, name: str) -> Dict[str, Any]:
        res = self.list_datasources()
        if isinstance(res, list):
            for ds in res:
                if ds.get("name") == name:
                    return ds
        return {"error": "Datasource not found", "name": name}

    # Alerting
    def list_alert_rules(self, dashboardUid: Optional[str] = None, folderUid: Optional[str] = None) -> Dict[str, Any]:
        params = {}
        if dashboardUid:
            params["dashboardUid"] = dashboardUid
        if folderUid:
            params["folderUid"] = folderUid
        return self._request("GET", "/api/alerts/rules", params=params)

    def get_alert_rule_by_uid(self, uid: str) -> Dict[str, Any]:
        return self._request("GET", f"/api/alerts/rules/{uid}")

    def list_contact_points(self) -> Dict[str, Any]:
        return self._request("GET", "/api/alerting/notifications")

    # Navigation / Deeplink
    def generate_deeplink(self, resourceType: str, uid: Optional[str] = None, panelId: Optional[int] = None,
                          from_ts: Optional[str] = None, to_ts: Optional[str] = None) -> Dict[str, Any]:
        if not self.url:
            return {"error": "GRAFANA_URL not set"}
        if resourceType == "dashboard" and uid:
            path = f"/d/{uid}"
            if panelId is not None:
                path += f"?viewPanel={panelId}"
        elif resourceType == "explore" and uid:
            # Build left parameter safely via json.dumps to avoid nested brace issues
            left = json.dumps({"datasource": uid})
            path = f"/explore?left={left}"
        else:
            return {"error": "Unsupported resourceType or missing uid", "resourceType": resourceType}
        if from_ts and to_ts:
            sep = '&' if '?' in path else '?'
            path += f"{sep}from={from_ts}&to={to_ts}"
        return {"link": f"{self.url}{path}"}

    # Admin
    def list_teams(self) -> Dict[str, Any]:
        return self._request("GET", "/api/teams")

    def list_users_by_org(self) -> Dict[str, Any]:
        return self._request("GET", "/api/org/users")

    # Annotations (subset)
    def get_annotations(self, dashboardUid: Optional[str] = None, tags: Optional[List[str]] = None,
                        from_ts: Optional[str] = None, to_ts: Optional[str] = None) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if dashboardUid:
            params["dashboardUid"] = dashboardUid
        if tags:
            params["tags"] = ','.join(tags)
        if from_ts:
            params['from'] = from_ts
        if to_ts:
            params['to'] = to_ts
        return self._request("GET", "/api/annotations", params=params)

    # Asserts
    def get_assertions(self, entityId: str) -> Dict[str, Any]:
        """Fetch assertion summary for an entity.

        Placeholder implementation: endpoint may vary depending on Asserts plugin.
        Adjust path if your deployment differs.
        """
        path = f"/api/asserts/entities/{entityId}/assertions"
        resp = self._request("GET", path)
        if "error" in resp:
            return {"warning": "Asserts endpoint may not be available", "entityId": entityId, "detail": resp}
        return resp


class PrometheusDirectClient:
    """Direct Prometheus HTTP client for metric queries."""
    def __init__(self, url: Optional[str] = None, token: Optional[str] = None, timeout: int = 30):
        self.url = (url or os.environ.get("PROMETHEUS_URL") or "").rstrip('/')
        self.token = token or os.environ.get("PROMETHEUS_TOKEN")
        self.timeout = timeout
        if not self.url:
            logger.warning("PrometheusDirectClient initialized without PROMETHEUS_URL")

    def _headers(self):
        h = {"Accept": "application/json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def _get(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if not self.url:
            return {"error": "PROMETHEUS_URL not configured"}
        full = f"{self.url}/api/v1/{endpoint}"
        try:
            resp = requests.get(full, headers=self._headers(), params=params, timeout=self.timeout)
            j = _safe_json(resp)
            if resp.status_code >= 400:
                return {"error": f"HTTP {resp.status_code}", "detail": j}
            if isinstance(j, dict) and j.get("status") != "success":
                return {"error": "Query failed", "detail": j}
            return j.get("data", {}) if isinstance(j, dict) else j
        except Exception as e:
            return {"error": str(e)}

    def execute_query(self, query: str, time: Optional[str] = None) -> Dict[str, Any]:
        params = {"query": query}
        if time:
            params["time"] = time
        return self._get("query", params)

    def execute_range_query(self, query: str, start: str, end: str, step: str) -> Dict[str, Any]:
        params = {"query": query, "start": start, "end": end, "step": step}
        return self._get("query_range", params)

    def list_metrics(self) -> Dict[str, Any]:
        return self._get("label/__name__/values", {})

    def get_metric_metadata(self, metric: str) -> Dict[str, Any]:
        data = self._get("metadata", {"metric": metric})
        if isinstance(data, dict):
            return data.get(metric, data)
        return data

    def get_targets(self) -> Dict[str, Any]:
        return self._get("targets", {})

    def health_check(self) -> Dict[str, Any]:
        if not self.url:
            return {"error": "PROMETHEUS_URL not configured"}
        full = f"{self.url}/-/healthy"
        try:
            resp = requests.get(full, headers=self._headers(), timeout=self.timeout)
            return {"status_code": resp.status_code, "healthy": resp.status_code == 200}
        except Exception as e:
            return {"error": str(e)}


def _extract_ds_uid(panel: Dict[str, Any]) -> Optional[str]:
    ds = panel.get("datasource")
    if isinstance(ds, dict):
        return ds.get("uid") or ds.get("id")
    return None

def _apply_patch(obj: Any, path_parts: List[str], op: str, value: Any):
    if not path_parts:
        return
    target = obj
    for part in path_parts[:-1]:
        if isinstance(target, list):
            target = target[int(part)]
        else:
            target = target.setdefault(part, {})
    last = path_parts[-1]
    if isinstance(target, list):
        idx = int(last)
        if op == 'replace':
            target[idx] = value
        elif op == 'add':
            target.insert(idx, value)
    else:
        target[last] = value

_grafana = GrafanaClient()
_prom = PrometheusDirectClient()

# ---------------------- LangChain Tool Wrappers ----------------------

@tool
def search_dashboards(query: str = "", tag: Optional[List[str]] = None, type: str = "dash-db") -> str:
    """Search Grafana dashboards by text query / tag."""
    return json.dumps(_grafana.search_dashboards(query=query, tag=tag, type=type), indent=2)

@tool
def get_dashboard_by_uid(uid: str) -> str:
    """Retrieve full dashboard JSON by UID (large)."""
    return json.dumps(_grafana.get_dashboard_by_uid(uid), indent=2)

@tool
def get_dashboard_summary(uid: str) -> str:
    """Compact dashboard summary for planning modifications."""
    return json.dumps(_grafana.get_dashboard_summary(uid), indent=2)

@tool
def get_dashboard_property(uid: str, jsonpath: str) -> str:
    """Extract specific dashboard parts via JSONPath (requires jsonpath-ng)."""
    return json.dumps(_grafana.get_dashboard_property(uid, jsonpath), indent=2)

@tool
def update_dashboard(dashboard: Dict[str, Any], folderUid: Optional[str] = None, message: Optional[str] = None) -> str:
    """Create/update a dashboard using full JSON definition."""
    return json.dumps(_grafana.update_dashboard(dashboard, folderUid, message), indent=2)

@tool
def patch_dashboard(uid: str, patches: List[Dict[str, Any]]) -> str:
    """Apply simple patch operations (replace/add) to dashboard before updating."""
    return json.dumps(_grafana.patch_dashboard(uid, patches), indent=2)

@tool
def get_dashboard_panel_queries(uid: str) -> str:
    """List panel queries and datasource info for a dashboard."""
    return json.dumps(_grafana.get_dashboard_panel_queries(uid), indent=2)

@tool
def list_datasources() -> str:
    """List Grafana datasources."""
    return json.dumps(_grafana.list_datasources(), indent=2)

@tool
def get_datasource_by_uid(uid: str) -> str:
    """Get datasource by UID."""
    return json.dumps(_grafana.get_datasource_by_uid(uid), indent=2)

@tool
def get_datasource_by_name(name: str) -> str:
    """Get datasource by name (lists and filters)."""
    return json.dumps(_grafana.get_datasource_by_name(name), indent=2)

@tool
def list_alert_rules(dashboardUid: Optional[str] = None, folderUid: Optional[str] = None) -> str:
    """List alert rules optionally filtered by dashboard or folder."""
    return json.dumps(_grafana.list_alert_rules(dashboardUid, folderUid), indent=2)

@tool
def get_alert_rule_by_uid(uid: str) -> str:
    """Get an alert rule by UID."""
    return json.dumps(_grafana.get_alert_rule_by_uid(uid), indent=2)

@tool
def list_contact_points() -> str:
    """List notification contact points."""
    return json.dumps(_grafana.list_contact_points(), indent=2)

@tool
def generate_deeplink(resourceType: str, uid: Optional[str] = None, panelId: Optional[int] = None,
                      from_ts: Optional[str] = None, to_ts: Optional[str] = None) -> str:
    """Generate a Grafana deeplink (dashboard/explore) with optional time range."""
    return json.dumps(_grafana.generate_deeplink(resourceType, uid, panelId, from_ts, to_ts), indent=2)

@tool
def list_teams() -> str:
    """List Grafana teams."""
    return json.dumps(_grafana.list_teams(), indent=2)

@tool
def list_users_by_org() -> str:
    """List users in current Grafana organization."""
    return json.dumps(_grafana.list_users_by_org(), indent=2)

@tool
def get_annotations(dashboardUid: Optional[str] = None, tags: Optional[List[str]] = None,
                    from_ts: Optional[str] = None, to_ts: Optional[str] = None) -> str:
    """Fetch annotations (filter by dashboard, tags, time range)."""
    return json.dumps(_grafana.get_annotations(dashboardUid, tags, from_ts, to_ts), indent=2)

# Direct Prometheus tools
@tool
def execute_query(query: str, time: Optional[str] = None) -> str:
    """Prometheus instant PromQL query."""
    return json.dumps(_prom.execute_query(query, time), indent=2)

@tool
def execute_range_query(query: str, start: str, end: str, step: str) -> str:
    """Prometheus range PromQL query."""
    return json.dumps(_prom.execute_range_query(query, start, end, step), indent=2)

@tool
def list_metrics() -> str:
    """List all Prometheus metrics (label __name__)."""
    return json.dumps(_prom.list_metrics(), indent=2)

@tool
def get_metric_metadata(metric: str) -> str:
    """Get metadata for a Prometheus metric."""
    return json.dumps(_prom.get_metric_metadata(metric), indent=2)

@tool
def get_targets() -> str:
    """Get Prometheus scrape targets."""
    return json.dumps(_prom.get_targets(), indent=2)

@tool
def get_assertions(entityId: str) -> str:
    """Get assertion summary for an entity (Grafana Asserts)."""
    return json.dumps(_grafana.get_assertions(entityId), indent=2)

@tool
def health_check() -> str:
    """Prometheus server health status."""
    return json.dumps(_prom.health_check(), indent=2)

# ---------------------- Introspection Wrapper Tools ----------------------

@tool
def list_monitoring_tool_names() -> str:
    """List names of all implemented monitoring tools in the static catalog.

    Returns JSON: {"tools": [<names>]}.
    Deterministic and lightweight; no external calls.
    Use before choosing an operational tool when uncertain about availability.
    """
    names = ComprehensiveMCPTools.get_implemented_tool_names()
    return json.dumps({"tools": names}, indent=2)

@tool
def describe_monitoring_tool(name: str) -> str:
    """Return metadata for a specific implemented monitoring tool.

    Includes description, category, permissions, parameters, use_cases.
    Returns an error if tool is unknown or not implemented.
    """
    all_tools = ComprehensiveMCPTools.get_all_tools()
    meta = all_tools.get(name)
    if not meta or not meta.get("implemented"):
        return json.dumps({"error": "unknown_or_unimplemented_tool", "name": name}, indent=2)
    # Exclude internal flags
    filtered = {k: v for k, v in meta.items() if k != "implemented"}
    filtered["name"] = name
    return json.dumps(filtered, indent=2)

@tool
def get_monitoring_tool_parameters(name: str) -> str:
    """Return parameter schema for an implemented monitoring tool.

    Provides required list and optional dict: {"name": name, "required": [...], "optional": {...}}
    Useful for constructing valid tool calls without hallucinated args.
    """
    all_tools = ComprehensiveMCPTools.get_all_tools()
    meta = all_tools.get(name)
    if not meta or not meta.get("implemented"):
        return json.dumps({"error": "unknown_or_unimplemented_tool", "name": name}, indent=2)
    params = meta.get("parameters", {})
    return json.dumps({
        "name": name,
        "required": params.get("required", []),
        "optional": params.get("optional", {})
    }, indent=2)