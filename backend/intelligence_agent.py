"""Structured natural-language planner for Coral-backed HELIX intelligence."""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

from coral_queries import list_queries
from coral_service import run_query


ROOT = Path(__file__).resolve().parents[1]


def _env_value(key: str, default: str = "") -> str:
    if os.getenv(key):
        return os.getenv(key, default)
    for path in [ROOT / ".env", ROOT / "backend" / ".env"]:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            env_key, value = line.split("=", 1)
            if env_key == key:
                return value
    return default


GEMINI_API_KEY = _env_value("GEMINI_API_KEY")
GEMINI_MODEL = _env_value("HELIX_GEMINI_MODEL", "gemini-2.5-flash")
OPENROUTER_API_KEY = _env_value("OPENROUTER_API_KEY")
OPENROUTER_MODEL = _env_value("HELIX_OPENROUTER_MODEL")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
AGENT_CACHE_TTL = 300

_agent_cache = {"data": {}, "lock": threading.Lock()}


QUERY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "risk_weather_context": (
        "weather",
        "solar",
        "storm",
        "geomagnetic",
        "noaa",
        "kp",
        "risk",
        "threat",
        "summary",
        "48 hours",
    ),
    "closest_spacetrack_enrichment": (
        "closest",
        "space-track",
        "spacetrack",
        "metadata",
        "country",
        "object type",
        "who owns",
        "enrich",
    ),
    "starlink_launch_context": (
        "starlink",
        "spacex",
        "launch",
        "launches",
        "constellation",
    ),
    "launch_weather_window": (
        "launch",
        "launches",
        "window",
        "mission",
        "provider",
        "weather",
        "solar",
        "storm",
    ),
}


def _cache_key(prompt: str) -> str:
    return hashlib.md5(prompt.strip().lower().encode()).hexdigest()


def _get_cached(key: str) -> dict[str, Any] | None:
    with _agent_cache["lock"]:
        entry = _agent_cache["data"].get(key)
        if entry and datetime.now().timestamp() - entry["timestamp"] < AGENT_CACHE_TTL:
            return entry["response"]
    return None


def _save_cached(key: str, response: dict[str, Any]) -> None:
    with _agent_cache["lock"]:
        _agent_cache["data"][key] = {
            "response": response,
            "timestamp": datetime.now().timestamp(),
        }


def plan_queries(prompt: str) -> list[str]:
    text = prompt.lower()
    scores: dict[str, int] = {}
    for query_id, keywords in QUERY_KEYWORDS.items():
        scores[query_id] = sum(1 for keyword in keywords if keyword in text)

    selected = [query_id for query_id, score in sorted(scores.items(), key=lambda x: x[1], reverse=True) if score > 0]
    if not selected:
        selected = ["risk_weather_context", "closest_spacetrack_enrichment"]

    if "launch" in text and "weather" in text and "launch_weather_window" not in selected:
        selected.insert(0, "launch_weather_window")
    if ("starlink" in text or "spacex" in text) and "starlink_launch_context" not in selected:
        selected.insert(0, "starlink_launch_context")

    # Keep responses quick and explainable.
    deduped: list[str] = []
    for query_id in selected:
        if query_id not in deduped:
            deduped.append(query_id)
    return deduped[:3]


def _fallback_summary(prompt: str, query_results: list[dict[str, Any]]) -> dict[str, Any]:
    lines = []
    recommendations = []

    for result in query_results:
        query_id = result["id"]
        rows = result.get("rows", [])
        if query_id == "risk_weather_context":
            high = next((row for row in rows if row.get("risk") == "HIGH"), None)
            if high:
                lines.append(
                    f"{high.get('conjunctions', 0)} high-risk conjunctions are present; closest miss distance is {high.get('closest_km')} km."
                )
                lines.append(
                    f"Current NOAA geomagnetic scale is {high.get('geomagnetic_storm_scale')} ({high.get('geomagnetic_storm_text')})."
                )
        elif query_id == "closest_spacetrack_enrichment" and rows:
            first = rows[0]
            lines.append(
                f"Closest enriched object is {first.get('helix_name')} at {first.get('miss_distance_km')} km, classified by Space-Track as {first.get('object_type')} from {first.get('country_code')}."
            )
        elif query_id == "starlink_launch_context" and rows:
            lines.append(
                f"{len(rows)} upcoming Starlink launches were correlated with {rows[0].get('starlink_conjunction_events')} local Starlink-named conjunction events."
            )
        elif query_id == "launch_weather_window" and rows:
            lines.append(
                f"{len(rows)} upcoming launches were checked against current NOAA scale context."
            )

    if not lines:
        lines.append("No matching operational signals were returned by the approved Coral queries.")

    recommendations.append("Use the returned query IDs and SQL for auditability before taking operational action.")
    recommendations.append("Refresh source snapshots before a live demo or operational briefing.")

    return {
        "summary": " ".join(lines),
        "recommendations": recommendations,
        "model_used": None,
        "fallback": True,
    }


def _summary_prompt(prompt: str, query_results: list[dict[str, Any]]) -> str:
    compact_results = [
        {
            "id": result["id"],
            "title": result["title"],
            "row_count": result["row_count"],
            "elapsed_ms": result["elapsed_ms"],
            "rows": result["rows"][:5],
        }
        for result in query_results
    ]
    return f"""You are HELIX, a space operations intelligence analyst.
Use only the provided structured Coral query results. Do not invent external facts.
Return compact JSON with keys: summary, recommendations.

Operator question: {prompt}

Coral results:
{json.dumps(compact_results, indent=2)}
"""


def _parse_summary_text(text: str, model_used: str) -> dict[str, Any] | None:
    if not text:
        return None
    parsed: Any | None = None
    try:
        parsed = json.loads(text)
        if isinstance(parsed, str):
            parsed = json.loads(parsed)
    except json.JSONDecodeError:
        parsed = None

    start = text.find("{")
    end = text.rfind("}")
    if parsed is None and start >= 0 and end > start:
        parsed = json.loads(text[start : end + 1])

    if isinstance(parsed, dict):
        recommendations = parsed.get("recommendations", [])
        if isinstance(recommendations, str):
            recommendations = [recommendations]
        return {
            "summary": parsed.get("summary", "").strip(),
            "recommendations": recommendations,
            "model_used": model_used,
            "fallback": False,
        }
    return None


def _gemini_summary(prompt: str, query_results: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not GEMINI_API_KEY:
        return None

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": _summary_prompt(prompt, query_results)}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 700,
            "responseMimeType": "application/json",
        },
    }
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": GEMINI_API_KEY,
    }

    for attempt in range(2):
        try:
            response = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent",
                headers=headers,
                json=payload,
                timeout=30,
            )
            if response.status_code in {429, 500, 502, 503, 504} and attempt == 0:
                time.sleep(1.0)
                continue
            response.raise_for_status()
            data = response.json()
            text = (
                data.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text", "")
            )
            return _parse_summary_text(text, GEMINI_MODEL)
        except Exception as exc:
            if attempt == 0:
                time.sleep(1.0)
                continue
            print(f"[intelligence_agent] Gemini summary failed: {exc}")
            return None
    return None


def _openrouter_summary(prompt: str, query_results: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not OPENROUTER_API_KEY or not OPENROUTER_MODEL:
        return None

    try:
        response = requests.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://helix.space",
                "X-Title": "HELIX Coral Intelligence",
            },
            json={
                "model": OPENROUTER_MODEL,
                "messages": [{"role": "user", "content": _summary_prompt(prompt, query_results)}],
                "temperature": 0.2,
                "max_tokens": 700,
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return _parse_summary_text(text, OPENROUTER_MODEL)
    except Exception as exc:
        print(f"[intelligence_agent] OpenRouter summary failed: {exc}")
    return None


def _llm_summary(prompt: str, query_results: list[dict[str, Any]]) -> dict[str, Any] | None:
    return _gemini_summary(prompt, query_results) or _openrouter_summary(prompt, query_results)


def answer_prompt(prompt: str) -> dict[str, Any]:
    cleaned = prompt.strip()
    if not cleaned:
        raise ValueError("prompt is required")

    key = _cache_key(cleaned)
    cached = _get_cached(key)
    if cached:
        return cached

    selected = plan_queries(cleaned)
    results = [run_query(query_id) for query_id in selected]
    synthesis = _llm_summary(cleaned, results) or _fallback_summary(cleaned, results)
    response = {
        "prompt": cleaned,
        "planner": "structured_keyword_planner_v1",
        "available_queries": list_queries(),
        "selected_query_ids": selected,
        "synthesis": synthesis,
        "results": results,
    }
    _save_cached(key, response)
    return response
