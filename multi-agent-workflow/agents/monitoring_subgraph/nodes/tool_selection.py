"""
Tool Selection LLM Node (Static Unified Catalog Mode)
Selects only tools explicitly defined in UnifiedComprehensiveMCPTools (implemented wrappers).

Features:
 - Single authoritative static catalog (no runtime introspection)
 - Parameter name alignment (generate_deeplink uses from_ts/to_ts)
 - Required/optional parameter validation
 - Optional parameter filtering (drop unknown extras)
 - Retry pass if first selection yields zero tools
 - Basic type coercion
"""
import asyncio
import importlib
import re
from datetime import datetime, timedelta
from ..state_schemas import MonitoringSubgraphState
from tools.monitoring_tools import UnifiedComprehensiveMCPTools
from common.utils.logging_setup import setup_logging

logger = setup_logging(__name__)


def _coerce_param_value(value, expected_type: str):
    """Coerce simple scalar parameter values based on expected type string."""
    if expected_type in ("any", "unknown", "object"):
        return value
    if expected_type.startswith("list"):
        # Accept already-list, comma-separated string, or single value to list
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            parts = [v.strip() for v in value.split(',') if v.strip()]
            return parts
        return [value]
    if expected_type.startswith("dict"):
        # Leave dicts; try JSON decode for strings
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            import json
            try:
                return json.loads(value)
            except Exception:
                return {"raw": value}
        return {"value": value}
    if expected_type in ("int", "integer"):
        try:
            return int(value)
        except Exception:
            return value
    if expected_type in ("float", "double"):
        try:
            return float(value)
        except Exception:
            return value
    if expected_type in ("bool", "boolean"):
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ["true", "1", "yes"]
        return bool(value)
    # Default: ensure string for str types
    if expected_type in ("str", "string") and not isinstance(value, str):
        return str(value)
    return value


async def tool_selection_llm_node(state: MonitoringSubgraphState) -> MonitoringSubgraphState:
    """Static catalog tool selection using UnifiedComprehensiveMCPTools.

    Steps:
      1. Validate LLM & MCP availability
      2. Load static catalog (implemented tools only)
    3. Build inline prompt (no DynamicToolSelector / dynamic discovery)
      4. First-pass LLM selection
      5. Retry with lower temperature if empty
      6. Validate required/optional parameters, coerce types
      7. Produce selection summary
    """
    try:
        query = state["query"]
        config = state["config"]
        
        llm_client = state.get("_llm_client")
        mcp_client = state.get("_mcp_client")
        
        # Validate client availability
        if not llm_client or not llm_client.is_functional():
            logger.error("❌ LLM client not functional for tool selection")
            state["errors"] = ["LLM client not functional for tool selection"]
            state["failed_at_node"] = "tool_selection"
            state["error_type"] = "llm_unavailable"
            return state
            
        if not mcp_client:
            logger.error("❌ MCP client not available for tool discovery")
            state["errors"] = ["MCP client not available for tool discovery"]
            state["failed_at_node"] = "tool_selection"
            state["error_type"] = "mcp_unavailable"
            return state
        
        # Load static catalog
        static_catalog = UnifiedComprehensiveMCPTools.get_all_tools()
        implemented = {name: meta for name, meta in static_catalog.items() if meta.get("implemented")}
        if not implemented:
            state["errors"] = ["Static catalog empty (no implemented tools)"]
            state["failed_at_node"] = "tool_selection"
            state["error_type"] = "no_tools_available"
            return state
        logger.info(f"📦 Static catalog loaded: {len(implemented)} implemented tools")

        # Simple keyword suggestions from catalog (not dynamic discovery)
        def _suggest(q: str) -> list[str]:
            ql = q.lower().split()
            scored = []
            for name, meta in implemented.items():
                score = 0
                desc = meta.get("description", "").lower()
                for kw in ql:
                    if kw in name.lower():
                        score += 3
                    if kw in desc:
                        score += 1
                if score > 0:
                    scored.append((score, name))
            return [n for _, n in sorted(scored, reverse=True)[:5]]
        suggestion_names = _suggest(query)
        if suggestion_names:
            logger.debug(f"💡 Suggested tools (static): {suggestion_names}")

        # Build static prompt directly (avoid dynamic selector dependency)
        def _build_prompt(q: str, catalog: dict[str, dict[str, any]]) -> str:
            lines = [f'User Query: "{q}"', '', 'Available Monitoring Tools (name(signature): description):']
            for name, meta in catalog.items():
                params_meta = meta.get("parameters", {})
                required = params_meta.get("required", [])
                optional = list(params_meta.get("optional", {}).keys())
                sig_parts = required + [f"{o}?" for o in optional]
                signature = f"({', '.join(sig_parts)})" if sig_parts else "()"
                lines.append(f" - {name}{signature}: {meta.get('description','')}")
            lines.append('')
            lines.append('Instructions:')
            lines.append('1. Pick 1-3 most relevant tools for the query.')
            lines.append('2. Provide ONLY required params and any truly helpful optional params.')
            lines.append('3. Use realistic values (do NOT invent impossible IDs).')
            lines.append('4. Output each selection on its own line as: tool_name(param="value", param2=123)')
            lines.append('5. If no tool applies, output: none')
            lines.append('')
            lines.append('Selections:')
            return '\n'.join(lines)

        async def _llm_select(q: str, temp: float, max_tokens: int) -> list[dict[str, any]]:
            prompt = _build_prompt(q, implemented)
            try:
                raw = await asyncio.wait_for(
                    llm_client.get_completion(prompt, temperature=temp, max_tokens=max_tokens),
                    timeout=config.get("llm_timeout", 30)
                )
            except asyncio.TimeoutError:
                return []
            if not raw:
                return []
            lines = [l.strip() for l in raw.splitlines() if l.strip()]
            if any(l.lower() == "none" for l in lines):
                return []
            selected: list[dict[str, any]] = []
            tool_call_pattern = re.compile(r'^(\w+)\s*\((.*)\)$')
            for line in lines:
                m = tool_call_pattern.match(line)
                if not m:
                    continue
                tname, param_blob = m.groups()
                if tname not in implemented:
                    continue
                params: dict[str, any] = {}
                if param_blob.strip():
                    # Split respecting quotes
                    parts = []
                    current = ''
                    in_quotes = False
                    quote_char = ''
                    for ch in param_blob:
                        if ch in ['"', "'"]:
                            if not in_quotes:
                                in_quotes = True
                                quote_char = ch
                            elif quote_char == ch:
                                in_quotes = False
                            current += ch
                        elif ch == ',' and not in_quotes:
                            if current.strip():
                                parts.append(current.strip())
                            current = ''
                        else:
                            current += ch
                    if current.strip():
                        parts.append(current.strip())
                    for part in parts:
                        if '=' not in part:
                            continue
                        k, v = part.split('=', 1)
                        k = k.strip()
                        v = v.strip()
                        if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
                            v = v[1:-1]
                        # Primitive coercion
                        if v.lower() in ["true", "false"]:
                            v = v.lower() == "true"
                        else:
                            if re.fullmatch(r'-?\d+', v):
                                try: v = int(v)
                                except: pass
                            elif re.fullmatch(r'-?\d+\.\d+', v):
                                try: v = float(v)
                                except: pass
                        params[k] = v
                selected.append({"tool_name": tname, "parameters": params})
            return selected

        # Time range extraction (natural language: "last X unit")
        def _extract_time_range(q: str):
            pat = re.search(r"last\s+(\d+)\s+(minute|minutes|hour|hours|day|days|week|weeks)", q.lower())
            if not pat:
                return None
            value = int(pat.group(1))
            unit = pat.group(2)
            now = datetime.utcnow()
            if unit.startswith("minute"):
                delta = timedelta(minutes=value)
                step = "60"  # 1m resolution
            elif unit.startswith("hour"):
                delta = timedelta(hours=value)
                step = "300"  # 5m
            elif unit.startswith("day"):
                delta = timedelta(days=value)
                step = "900"  # 15m
            elif unit.startswith("week"):
                delta = timedelta(weeks=value)
                step = "1800"  # 30m
            else:
                delta = timedelta(hours=value)
                step = "300"
            start = now - delta
            return {
                "start_iso": start.isoformat(timespec="seconds") + "Z",
                "end_iso": now.isoformat(timespec="seconds") + "Z",
                "step": step,
                "from_ts": str(int(start.timestamp() * 1000)),  # Grafana ms epoch
                "to_ts": str(int(now.timestamp() * 1000))
            }

        tr = _extract_time_range(query)
        augmented_query = query if not tr else f"{query} [time_range start={tr['start_iso']} end={tr['end_iso']} step={tr['step']}]"

        logger.info(f"🧠 Selecting tools (pass 1 static inline) for query: {augmented_query[:120]}...")
        selected_tools = await _llm_select(augmented_query, config.get("llm_temperature", 0.7), config.get("max_tokens", 200))
        if not selected_tools:
            logger.warning("⚠️ No tools selected in first pass; attempting low-temp retry")
            selected_tools = await _llm_select(augmented_query, 0.1, 160)

        if not selected_tools:
            logger.warning("❌ No tools selected after retry (no synthesis applied)")
            state["errors"] = ["Tool selection produced no candidates"]
            state["failed_at_node"] = "tool_selection"
            state["error_type"] = "no_tools_selected"
            state["llm_decisions"]["tool_selection"] = f"None selected. Suggestions: {suggestion_names}" if suggestion_names else "None selected."
            return state

        # Validate & coerce parameters using static catalog metadata (always executed)
        validated_tools = []
        initial_candidates = selected_tools[:]
        for tool_info in selected_tools:
            tool_name = tool_info.get("tool_name")
            params = tool_info.get("parameters", {})
            meta = implemented.get(tool_name)
            if not meta:
                logger.debug(f"⏭️ Not implemented tool skipped: {tool_name}")
                continue

            # Alias normalization for time params
            if "from" in params and "from_ts" not in params:
                params["from_ts"] = params.pop("from")
            if "to" in params and "to_ts" not in params:
                params["to_ts"] = params.pop("to")

            # Inject extracted time range if relevant and missing
            if tr:
                if tool_name == "execute_range_query":
                    for key in ["start", "end", "step"]:
                        if key not in params:
                            if key == "start":
                                params[key] = tr["start_iso"]
                            elif key == "end":
                                params[key] = tr["end_iso"]
                            elif key == "step":
                                params[key] = tr["step"]
                if tool_name in ["get_annotations", "generate_deeplink"]:
                    if "from_ts" not in params:
                        params["from_ts"] = tr["from_ts"]
                    if "to_ts" not in params:
                        params["to_ts"] = tr["to_ts"]

            # Required params
            param_schema = meta.get("parameters", {})
            required = param_schema.get("required", [])
            missing = [r for r in required if r not in params]
            if missing:
                logger.debug(f"⚠️ Missing required for {tool_name}: {missing}")
                continue

            # Unexpected params
            all_param_names = set(required) | set(param_schema.get("optional", {}).keys())
            unexpected = [p for p in params.keys() if p not in all_param_names]
            if unexpected:
                logger.debug(f"🔍 Dropping unexpected params for {tool_name}: {unexpected}")
                for u in unexpected:
                    params.pop(u, None)

            # Type coercion (basic)
            coerced = {}
            for pname, pval in params.items():
                expected_type = "str"
                if pname in param_schema.get("optional", {}):
                    expected_type = param_schema["optional"][pname].lower()
                coerced[pname] = _coerce_param_value(pval, expected_type)

            tool_info["parameters"] = coerced

            if any(r not in coerced for r in required):
                logger.debug(f"⛔ Post-coercion missing required for {tool_name}")
                continue
            logger.info(f"✅ {tool_name} validated ({list(coerced.keys())})")
            validated_tools.append(tool_info)

        if not validated_tools:
            # Multi-pass refinement (no synthetic data). Up to N retries to let LLM fill ONLY genuinely inferable params.
            max_param_retries = min(3, int(config.get("tool_param_retry_attempts", 3)))
            refinement_attempts = 0
            missing_map = {}
            # Build missing map for first pass
            for cand in initial_candidates:
                tname = cand.get("tool_name")
                meta = implemented.get(tname, {})
                req = meta.get("parameters", {}).get("required", [])
                provided = set(cand.get("parameters", {}).keys())
                missing = [r for r in req if r not in provided]
                if missing:
                    missing_map[tname] = missing
            while refinement_attempts < max_param_retries and not validated_tools and missing_map:
                refinement_attempts += 1
                target_tool = list(missing_map.keys())[0]
                target_missing = missing_map[target_tool]
                logger.info(f"🔄 Param refinement attempt {refinement_attempts} for {target_tool}; missing: {target_missing}")
                # Refinement prompt instructs: only fill if confidently inferable; else output ask_user
                refinement_prompt = (
                    "User query: '" + query + "'\n" +
                    f"Tool '{target_tool}' requires missing parameters: {', '.join(target_missing)}.\n" +
                    "If you can confidently infer REAL values from the query (e.g. explicit IDs, time references already extracted), output a single line: " +
                    target_tool + "(" + ", ".join([m + "=\"value\"" for m in target_missing]) + ")" + "\n" +
                    "If not confident, output exactly: ask_user\n" +
                    "Do NOT invent metric names or dashboard IDs."
                )
                try:
                    refine_raw = await asyncio.wait_for(
                        llm_client.get_completion(refinement_prompt, temperature=0.2, max_tokens=60),
                        timeout=config.get("llm_timeout", 30)
                    )
                except Exception as ex:
                    logger.warning(f"Refinement LLM error: {ex}")
                    break
                if not refine_raw or refine_raw.strip().lower().startswith("ask_user"):
                    logger.info("🛑 LLM signaled clarification required; stopping refinement loop")
                    break
                # Parse refinement selection like normal
                refinement_selected = await _llm_select(refine_raw, 0.2, 60)
                # Filter to target tool only
                refinement_selected = [c for c in refinement_selected if c.get("tool_name") == target_tool]
                if not refinement_selected:
                    logger.debug("Refinement produced no parsable tool line")
                    continue
                # Merge refined params into candidate and revalidate
                for ref in refinement_selected:
                    params = ref.get("parameters", {})
                    meta = implemented.get(target_tool, {})
                    param_schema = meta.get("parameters", {})
                    required = param_schema.get("required", [])
                    # Reject if still missing
                    if any(r not in params for r in required):
                        logger.debug("Refined params still missing required; continuing")
                        continue
                    coerced = {}
                    for pname, pval in params.items():
                        expected_type = "str"
                        if pname in param_schema.get("optional", {}):
                            expected_type = param_schema["optional"][pname].lower()
                        coerced[pname] = _coerce_param_value(pval, expected_type)
                    ref["parameters"] = coerced
                    validated_tools.append(ref)
                # Update missing map (remove tool if validated)
                if any(t.get("tool_name") == target_tool for t in validated_tools):
                    missing_map.pop(target_tool, None)
            if not validated_tools:
                # Clarification required
                missing_details = {t: miss for t, miss in missing_map.items()} if missing_map else {}
                state["errors"] = ["Tool validation failed; clarification required", str(missing_details)]
                state["failed_at_node"] = "tool_selection"
                state["error_type"] = "tool_validation_failed"
                state.setdefault("llm_decisions", {})["tool_selection_refinement"] = (
                    f"Refinement attempts={refinement_attempts}; clarification needed for: {missing_details}" if missing_details else "Refinement attempts exhausted"
                )
                return state

        # Clear stale errors from earlier nodes if we have a successful validation
        if validated_tools and state.get("errors"):
            logger.debug("🧹 Clearing stale errors after successful tool validation")
            state.pop("errors", None)

        state["selected_tools"] = validated_tools
        # Build human-readable execution previews for logging/inspection (non-execution)
        previews = []
        for t in validated_tools:
            name = t.get("tool_name")
            params = t.get("parameters", {})
            if name in ["execute_query", "execute_range_query"]:
                query_str = params.get("query", "<missing>")
                if name == "execute_range_query":
                    preview = f"{name}: query='{query_str}' start={params.get('start')} end={params.get('end')} step={params.get('step')}"
                else:
                    preview = f"{name}: query='{query_str}' time={params.get('time','<none>')}"
            else:
                # Generic preview
                trimmed = {k: v for k, v in params.items()}
                preview = f"{name}: params={trimmed}"
            previews.append(preview)
            logger.info(f"🔍 Tool preview → {preview}")
        state.setdefault("tool_parameters", {})["previews"] = previews
        # Ensure errors cleared on success
        state["errors"] = []
        tool_names = [t["tool_name"] for t in validated_tools]
        selection_summary = f"Validated {len(validated_tools)} tools (static): {tool_names}" + (f" | suggestions: {suggestion_names}" if suggestion_names else "")
        state["llm_decisions"]["tool_selection"] = selection_summary
        logger.info(f"🎯 Static inline tool selection complete: {tool_names}")
        logger.debug(f"📊 {selection_summary}")

        # Optional immediate execution mode (combines selection + execution in one node)
        # Enable via config flag: config['auto_execute_tools'] == True
        if config.get("auto_execute_tools"):
            logger.info("🚀 Auto-execution mode enabled; invoking selected tools directly")
            execution_results = []
            monitoring_module = importlib.import_module("tools.monitoring_tools")
            for tool_info in validated_tools:
                name = tool_info.get("tool_name")
                params = tool_info.get("parameters", {})
                fn = getattr(monitoring_module, name, None)
                if not callable(fn):
                    logger.warning(f"⚠️ Tool function not found for execution: {name}")
                    execution_results.append({"tool_name": name, "error": "function_not_found"})
                    continue
                try:
                    raw = fn(**params) if params else fn()
                    parsed = None
                    if isinstance(raw, str):
                        try:
                            import json as _json
                            parsed = _json.loads(raw)
                        except Exception:
                            parsed = {"raw": raw}
                    else:
                        parsed = raw
                    execution_results.append({
                        "tool_name": name,
                        "parameters": params,
                        "raw_output": raw,
                        "parsed_output": parsed
                    })
                    logger.info(f"🛠️ Executed tool {name} (params={list(params.keys())})")
                except Exception as ex:
                    logger.error(f"❌ Execution failed for {name}: {ex}")
                    execution_results.append({"tool_name": name, "error": str(ex)})
            state["raw_tool_results"] = execution_results
            state["tool_results"] = [r.get("parsed_output", r) for r in execution_results]
            state["llm_decisions"]["tool_execution"] = f"Executed {len(execution_results)} tools immediately"
            logger.debug(f"📦 Auto-execution collected {len(execution_results)} result objects")
            return state
        # Return mutated state after successful validation (non auto-exec path)
        return state
            
    except Exception as e:
        logger.error(f"❌ Tool selection error: {e}", exc_info=True)
        state["errors"] = [f"Tool selection failed: {str(e)}"]
        state["failed_at_node"] = "tool_selection"
        state["error_type"] = "tool_selection_error"
        return state