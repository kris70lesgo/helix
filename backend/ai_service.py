"""
ai_service.py — Lightweight AI layer for HELIX using OpenRouter API

Provides:
  - Single conjunction analysis via OpenRouter
  - Summary of top risk conjunctions
  - In-memory cache for AI responses
"""

import hashlib
import json
import os
import re
import threading
from datetime import datetime
from pathlib import Path

import requests

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
                return value.strip().strip('"').strip("'")
    return default


OPENROUTER_API_KEY = _env_value("OPENROUTER_API_KEY")
OPENROUTER_MODEL = _env_value("HELIX_OPENROUTER_MODEL", "openrouter/free")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

AI_CACHE_TTL = 300  # 5 minutes

_ai_cache: dict = {
    "data": {},
    "lock": threading.Lock(),
}


def _make_cache_key(data: dict) -> str:
    """Generate deterministic cache key from input data."""
    s = f"{data.get('sat1', '')}{data.get('sat2', '')}{data.get('miss_distance_km', 0)}{data.get('tca_timestamp', '')}"
    return hashlib.md5(s.encode()).hexdigest()


def _get_from_cache(key: str) -> dict | None:
    """Get cached AI response if not expired."""
    with _ai_cache["lock"]:
        entry = _ai_cache["data"].get(key)
        if entry and (datetime.now().timestamp() - entry["timestamp"]) < AI_CACHE_TTL:
            return entry["response"]
    return None


def _save_to_cache(key: str, response: dict) -> None:
    """Store AI response in cache."""
    with _ai_cache["lock"]:
        _ai_cache["data"][key] = {
            "response": response,
            "timestamp": datetime.now().timestamp(),
        }


def _parse_ai_json(text: str) -> dict | None:
    """Parse JSON even when a model wraps it as a quoted JSON string."""
    if not text:
        return None
    try:
        parsed = json.loads(text)
        if isinstance(parsed, str):
            parsed = json.loads(parsed)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        parsed = json.loads(text[start : end + 1])
        if isinstance(parsed, dict):
            return parsed
    return None


def _extract_text_analysis(text: str) -> dict | None:
    """Gracefully handle free models that ignore JSON-only formatting."""
    cleaned = " ".join(text.replace("\n", " ").split())
    if not cleaned:
        return None

    text_lower = cleaned.lower()
    risk = "LOW"
    if any(k in text_lower for k in ["high risk", "critical", "severe", "dangerous", "very high"]):
        risk = "HIGH"
    elif any(k in text_lower for k in ["medium risk", "moderate", "elevated", "concern"]):
        risk = "MEDIUM"
    else:
        dist_match = re.search(r"(\d+(?:\.\d+)?)\s*km", text_lower)
        if dist_match:
            distance = float(dist_match.group(1))
            if distance < 1:
                risk = "HIGH"
            elif distance < 5:
                risk = "MEDIUM"

    recommendation = "monitor"
    if any(k in text_lower for k in ["plan maneuver", "collision avoidance", "evasive", "maneuver recommended"]):
        recommendation = "plan maneuver"
    elif any(k in text_lower for k in ["ignore", "no action", "safe to dismiss"]):
        recommendation = "ignore"

    explanation = cleaned[:260].strip()
    if len(cleaned) > 260:
        explanation = explanation.rstrip(" .,") + "."

    return {
        "risk_summary": f"{risk} risk conjunction assessed by OpenRouter",
        "recommendation": recommendation,
        "explanation": explanation,
    }


def _call_ai(prompt: str) -> dict | None:
    """Call OpenRouter API and extract structured conjunction analysis."""
    if not OPENROUTER_API_KEY:
        print("[ai_service] No OPENROUTER_API_KEY set")
        return None

    try:
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://helix.space",
            "X-Title": "HELIX Satellite Monitor",
        }
        payload = {
            "model": OPENROUTER_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a HELIX space operations analyst. "
                        "Return a compact conjunction assessment. Prefer JSON with keys: risk_summary, recommendation, explanation. "
                        "recommendation must be one of: monitor, plan maneuver, ignore."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,
            "max_tokens": 800,
        }

        resp = requests.post(
            OPENROUTER_URL,
            headers=headers,
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

        msg = data.get("choices", [{}])[0].get("message", {})
        text = msg.get("content") or msg.get("reasoning", "") or ""

        parsed = _parse_ai_json(text)
        if not parsed:
            return _extract_text_analysis(text)

        recommendation = str(parsed.get("recommendation", "monitor")).strip().lower()
        if recommendation not in {"monitor", "plan maneuver", "ignore"}:
            recommendation = "monitor"

        return {
            "risk_summary": str(parsed.get("risk_summary", "Risk assessment generated")).strip(),
            "recommendation": recommendation,
            "explanation": str(parsed.get("explanation", "Analysis generated by OpenRouter.")).strip(),
        }
    except Exception as e:
        print(f"[ai_service] OpenRouter API error: {e}")
        return None


def analyze_conjunction(sat1: str, sat2: str, distance_km: float, velocity_kms: float, tca: str) -> dict:
    """Analyze a single conjunction event using OpenRouter AI."""
    cache_key = _make_cache_key({
        "sat1": sat1,
        "sat2": sat2,
        "miss_distance_km": distance_km,
        "tca_timestamp": tca,
    })

    cached = _get_from_cache(cache_key)
    if cached:
        return cached

    prompt = f"""Space conjunction analysis:
Satellite 1: {sat1}
Satellite 2: {sat2}
Miss distance: {distance_km} km
Relative velocity: {velocity_kms} km/s
Time of closest approach: {tca}

Classify the risk level and recommend action: monitor, plan maneuver, or ignore?"""

    result = _call_ai(prompt)
    if not result:
        result = _make_fallback()
    
    # Ensure we have a valid response
    if not result or result.get("risk_summary") == "Analysis unavailable":
        result = _make_fallback()
    
    if result and "risk_summary" in result:
        _save_to_cache(cache_key, result)
    
    return result


def summarize_top_risks(conjunctions: list[dict], count: int = 3) -> dict:
    """Get AI summary of top risk conjunctions."""
    if not OPENROUTER_API_KEY or not conjunctions:
        return {"summaries": []}

    sorted_conjs = sorted(conjunctions, key=lambda x: x.get("distance", 9999))[:count]

    conj_text = "\n".join(
        f"- {c.get('sat1', '?')} vs {c.get('sat2', '?')}: {c.get('distance', 0):.2f} km ({c.get('risk', 'LOW')})"
        for c in sorted_conjs
    )

    prompt = f"Rank these {count} close approaches by risk:\n{conj_text}\nWhich 3 need most urgent attention?"
    result = _call_ai(prompt)
    
    if result:
        summaries = [{
            "sat_pair": f"{c.get('sat1', '')}-{c.get('sat2', '')}",
            "summary": result.get("explanation", "Monitor")[0:50]
        } for c in sorted_conjs]
        return {"summaries": summaries}
    
    return {"summaries": []}


def _make_fallback() -> dict:
    return {
        "risk_summary": "Analysis unavailable",
        "recommendation": "monitor",
        "explanation": "AI service temporarily unavailable. Continue monitoring via standard risk assessment.",
    }


def invalidate_cache() -> None:
    """Clear AI response cache."""
    with _ai_cache["lock"]:
        _ai_cache["data"].clear()
