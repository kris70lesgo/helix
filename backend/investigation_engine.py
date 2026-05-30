"""Deterministic multi-step investigation engine for Coral-backed AEGIS ops."""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from coral_queries import QUERIES
from coral_service import run_query


SESSION_TTL_SECONDS = 1800
MAX_STEPS = 8


QUERY_SOURCES: dict[str, list[str]] = {
    "risk_weather_context": ["aegis_core", "noaa_space_weather"],
    "closest_spacetrack_enrichment": ["aegis_core", "space_track"],
    "starlink_launch_context": ["aegis_core", "launch_library"],
    "launch_weather_window": ["launch_library", "noaa_space_weather"],
    "repeated_satellite_involvement": ["aegis_core"],
    "risk_density_by_day": ["aegis_core"],
    "high_risk_category_distribution": ["aegis_core"],
    "closest_high_risk_events": ["aegis_core"],
}


@dataclass(frozen=True)
class PlannedStep:
    stage: str
    label: str
    reason: str
    query_id: str | None = None


@dataclass
class InvestigationSession:
    id: str
    prompt: str
    strategy: str
    status: str = "queued"
    stage: str = "queued"
    steps: list[dict[str, Any]] = field(default_factory=list)
    executed_queries: list[dict[str, Any]] = field(default_factory=list)
    findings: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    confidence: float = 0.0
    assessment: str = ""
    alerts: list[dict[str, Any]] = field(default_factory=list)
    benchmark: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: _now())
    updated_at: str = field(default_factory=lambda: _now())
    completed_at: str | None = None
    error: str | None = None
    results: dict[str, dict[str, Any]] = field(default_factory=dict)


_sessions: dict[str, InvestigationSession] = {}
_lock = threading.Lock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _snapshot(session: InvestigationSession) -> dict[str, Any]:
    return {
        "id": session.id,
        "prompt": session.prompt,
        "strategy": session.strategy,
        "status": session.status,
        "stage": session.stage,
        "steps": session.steps,
        "executed_queries": session.executed_queries,
        "findings": session.findings,
        "recommendations": session.recommendations,
        "confidence": session.confidence,
        "assessment": session.assessment,
        "alerts": session.alerts,
        "benchmark": session.benchmark,
        "created_at": session.created_at,
        "updated_at": session.updated_at,
        "completed_at": session.completed_at,
        "error": session.error,
    }


def _cleanup_sessions() -> None:
    cutoff = time.time() - SESSION_TTL_SECONDS
    expired = []
    for session_id, session in _sessions.items():
        updated = datetime.fromisoformat(session.updated_at).timestamp()
        if updated < cutoff:
            expired.append(session_id)
    for session_id in expired:
        _sessions.pop(session_id, None)


def classify_strategy(prompt: str) -> str:
    text = prompt.lower()
    if any(word in text for word in ["why", "elevated", "spike", "increased", "today"]):
        return "risk_elevation"
    if any(word in text for word in ["launch", "starlink", "spacex"]):
        return "launch_correlation"
    if any(word in text for word in ["weather", "solar", "storm", "geomagnetic", "noaa", "kp"]):
        return "space_weather_context"
    if any(word in text for word in ["space-track", "spacetrack", "metadata", "country", "object"]):
        return "object_metadata"
    return "general_threat_brief"


def plan_investigation(prompt: str) -> tuple[str, list[PlannedStep]]:
    strategy = classify_strategy(prompt)
    base = [
        PlannedStep(
            "gathering_conjunctions",
            "Querying current conjunction risk distribution",
            "Establish the operational risk baseline from AEGIS conjunction data.",
            "risk_weather_context",
        ),
        PlannedStep(
            "analyzing_patterns",
            "Analyzing closest high-risk events",
            "Identify the tightest miss distances before looking for causes.",
            "closest_high_risk_events",
        ),
    ]
    strategy_steps: dict[str, list[PlannedStep]] = {
        "risk_elevation": base + [
            PlannedStep("analyzing_patterns", "Detecting repeated satellite involvement", "Find recurring objects that may explain elevated density.", "repeated_satellite_involvement"),
            PlannedStep("analyzing_patterns", "Comparing conjunction density by day", "Check whether the current snapshot shows temporal clustering.", "risk_density_by_day"),
            PlannedStep("checking_launch_activity", "Correlating launch activity", "Determine whether upcoming launch activity is relevant to the risk posture.", "launch_weather_window"),
            PlannedStep("checking_space_weather", "Checking NOAA space weather", "Rule in or out geomagnetic and radiation conditions.", "risk_weather_context"),
        ],
        "launch_correlation": base + [
            PlannedStep("checking_launch_activity", "Checking Starlink launch context", "Correlate constellation launch activity with local conjunction pressure.", "starlink_launch_context"),
            PlannedStep("checking_launch_activity", "Checking launch weather windows", "Attach NOAA context to upcoming launch activity.", "launch_weather_window"),
            PlannedStep("analyzing_patterns", "Detecting repeated satellite involvement", "Look for recurring spacecraft families in the conjunction set.", "repeated_satellite_involvement"),
        ],
        "space_weather_context": base + [
            PlannedStep("checking_space_weather", "Checking NOAA geomagnetic conditions", "Attach current NOAA scale context to the risk distribution.", "risk_weather_context"),
            PlannedStep("checking_launch_activity", "Checking launch windows", "Confirm whether launch operations overlap the current NOAA context.", "launch_weather_window"),
        ],
        "object_metadata": base + [
            PlannedStep("checking_spacetrack_metadata", "Enriching closest conjunctions with Space-Track", "Identify object type and country metadata for closest events.", "closest_spacetrack_enrichment"),
            PlannedStep("analyzing_patterns", "Summarizing high-risk satellite categories", "Check which object categories dominate high-risk events.", "high_risk_category_distribution"),
        ],
        "general_threat_brief": base + [
            PlannedStep("checking_spacetrack_metadata", "Enriching closest objects with Space-Track", "Add object metadata to closest conjunctions.", "closest_spacetrack_enrichment"),
            PlannedStep("checking_launch_activity", "Checking launch activity", "Correlate the risk picture with upcoming launch operations.", "launch_weather_window"),
            PlannedStep("analyzing_patterns", "Comparing historical density patterns", "Use stored conjunction timestamps as lightweight historical context.", "risk_density_by_day"),
        ],
    }
    steps = strategy_steps[strategy][:MAX_STEPS]
    steps.append(PlannedStep("correlating_results", "Correlating findings", "Combine completed query results into an explainable operational assessment."))
    steps.append(PlannedStep("generating_assessment", "Generating recommendations", "Produce conservative operator-facing next actions."))
    return strategy, steps[:MAX_STEPS]


def create_investigation(prompt: str) -> dict[str, Any]:
    cleaned = prompt.strip()
    if not cleaned:
        raise ValueError("prompt is required")
    strategy, planned_steps = plan_investigation(cleaned)
    session = InvestigationSession(id=uuid.uuid4().hex[:12], prompt=cleaned, strategy=strategy)
    session.steps = [_step_dict(i + 1, step) for i, step in enumerate(planned_steps)]
    with _lock:
        _cleanup_sessions()
        _sessions[session.id] = session
    thread = threading.Thread(target=_run_investigation, args=(session.id,), daemon=True)
    thread.start()
    return {"investigation_id": session.id, "status": "queued"}


def get_investigation(session_id: str) -> dict[str, Any] | None:
    with _lock:
        session = _sessions.get(session_id)
        return _snapshot(session) if session else None


def evaluate_alerts() -> dict[str, Any]:
    alerts = []
    try:
        risk = run_query("risk_weather_context")
        high = next((row for row in risk["rows"] if row.get("risk") == "HIGH"), None)
        if high:
            high_count = int(high.get("conjunctions") or 0)
            closest = float(high.get("closest_km") or 999999)
            if high_count >= 50:
                alerts.append(_alert("high", "High-risk conjunction density elevated", f"{high_count} high-risk conjunctions are currently stored.", ["aegis_core"], "Why are conjunction risks elevated today?"))
            if closest < 1:
                alerts.append(_alert("critical", "Sub-1 km miss distance detected", f"Closest high-risk miss distance is {closest:.3f} km.", ["aegis_core"], "Investigate the closest high-risk conjunctions and recurring satellites."))
            storm = float(high.get("geomagnetic_storm_scale") or 0)
            if storm >= 3:
                alerts.append(_alert("high", "NOAA geomagnetic storm elevated", f"Current NOAA geomagnetic scale is {storm}.", ["noaa_space_weather"], "Assess conjunction risk under current NOAA space weather."))
    except Exception as exc:
        alerts.append(_alert("medium", "Alert evaluator degraded", str(exc), ["coral"], "Summarize operational threats for the next 48 hours."))

    try:
        launches = run_query("launch_weather_window")
        if launches["row_count"] >= 10:
            alerts.append(_alert("medium", "Launch activity elevated", f"{launches['row_count']} upcoming launches are in the active snapshot.", ["launch_library", "noaa_space_weather"], "Correlate upcoming launch activity with current conjunction risk."))
    except Exception:
        pass

    severity_rank = {"critical": 3, "high": 2, "medium": 1, "low": 0}
    alerts.sort(key=lambda item: severity_rank.get(item["severity"], 0), reverse=True)
    return {"alerts": alerts, "count": len(alerts), "generated_at": _now()}


def _alert(severity: str, title: str, reason: str, sources: list[str], prompt: str) -> dict[str, Any]:
    return {
        "severity": severity,
        "title": title,
        "reason": reason,
        "sources": sources,
        "recommended_prompt": prompt,
    }


def _step_dict(index: int, step: PlannedStep) -> dict[str, Any]:
    return {
        "index": index,
        "stage": step.stage,
        "label": step.label,
        "status": "pending",
        "reason": step.reason,
        "query_id": step.query_id,
        "sources": QUERY_SOURCES.get(step.query_id or "", []),
        "row_count": None,
        "elapsed_ms": None,
        "finding": "",
        "started_at": None,
        "completed_at": None,
    }


def _run_investigation(session_id: str) -> None:
    started = time.perf_counter()
    with _lock:
        session = _sessions[session_id]
        session.status = "running"
        session.updated_at = _now()

    try:
        for step in _session_steps(session_id):
            _start_step(session_id, step["index"])
            if step["query_id"]:
                result = run_query(step["query_id"])
                finding = _finding_for_result(result)
                _complete_query_step(session_id, step["index"], result, finding)
            else:
                _complete_reasoning_step(session_id, step["index"])
            time.sleep(0.15)
        _finalize_session(session_id, round((time.perf_counter() - started) * 1000, 2))
    except Exception as exc:
        _abort_session(session_id, str(exc), round((time.perf_counter() - started) * 1000, 2))


def _session_steps(session_id: str) -> list[dict[str, Any]]:
    with _lock:
        return [dict(step) for step in _sessions[session_id].steps]


def _start_step(session_id: str, index: int) -> None:
    with _lock:
        session = _sessions[session_id]
        step = session.steps[index - 1]
        session.stage = step["stage"]
        step["status"] = "running"
        step["started_at"] = _now()
        session.updated_at = _now()


def _complete_query_step(session_id: str, index: int, result: dict[str, Any], finding: str) -> None:
    with _lock:
        session = _sessions[session_id]
        step = session.steps[index - 1]
        step["status"] = "completed"
        step["row_count"] = result["row_count"]
        step["elapsed_ms"] = result["elapsed_ms"]
        step["finding"] = finding
        step["completed_at"] = _now()
        query_trace = {
            "query_id": result["id"],
            "title": result["title"],
            "sources": QUERY_SOURCES.get(result["id"], []),
            "row_count": result["row_count"],
            "elapsed_ms": result["elapsed_ms"],
            "finding": finding,
        }
        session.executed_queries.append(query_trace)
        session.findings.append(finding)
        session.results[result["id"]] = result
        session.updated_at = _now()


def _complete_reasoning_step(session_id: str, index: int) -> None:
    with _lock:
        session = _sessions[session_id]
        step = session.steps[index - 1]
        if step["stage"] == "correlating_results":
            finding = _correlation_finding(session)
        else:
            _build_assessment(session)
            finding = "Operational recommendations generated from completed Coral query findings."
        step["status"] = "completed"
        step["finding"] = finding
        step["completed_at"] = _now()
        session.findings.append(finding)
        session.updated_at = _now()


def _finalize_session(session_id: str, elapsed_ms: float) -> None:
    with _lock:
        session = _sessions[session_id]
        _build_assessment(session)
        session.status = "completed"
        session.stage = "completed"
        session.completed_at = _now()
        session.updated_at = session.completed_at
        session.benchmark = {
            "duration_ms": elapsed_ms,
            "query_chain_length": len(session.executed_queries),
            "total_query_latency_ms": round(sum(q["elapsed_ms"] for q in session.executed_queries), 2),
            "source_count": len({source for q in session.executed_queries for source in q["sources"]}),
        }
        session.alerts = evaluate_alerts().get("alerts", [])[:3]


def _abort_session(session_id: str, error: str, elapsed_ms: float) -> None:
    with _lock:
        session = _sessions[session_id]
        session.status = "aborted"
        session.stage = "aborted"
        session.error = error
        session.completed_at = _now()
        session.updated_at = session.completed_at
        session.benchmark = {"duration_ms": elapsed_ms, "query_chain_length": len(session.executed_queries)}
        for step in session.steps:
            if step["status"] == "running":
                step["status"] = "aborted"
                step["finding"] = error
                step["completed_at"] = _now()
                break


def _finding_for_result(result: dict[str, Any]) -> str:
    rows = result.get("rows", [])
    query_id = result["id"]
    if not rows:
        return f"{result['title']} returned no rows."
    if query_id == "risk_weather_context":
        high = next((row for row in rows if row.get("risk") == "HIGH"), rows[0])
        return f"{high.get('conjunctions', 0)} high-risk conjunctions observed; closest miss distance is {high.get('closest_km')} km under NOAA geomagnetic scale {high.get('geomagnetic_storm_scale')}."
    if query_id == "closest_high_risk_events":
        first = rows[0]
        return f"Closest high-risk pair is {first.get('sat1_name')} vs {first.get('sat2_name')} at {first.get('miss_distance_km')} km."
    if query_id == "repeated_satellite_involvement":
        first = rows[0]
        return f"{first.get('name')} appears most frequently with {first.get('high_risk_events')} high-risk events and {first.get('conjunction_events')} total events."
    if query_id == "risk_density_by_day":
        first = rows[0]
        return f"Most recent density window {first.get('event_date')} has {first.get('conjunction_events')} conjunctions and {first.get('high_risk_events')} high-risk events."
    if query_id == "starlink_launch_context":
        first = rows[0]
        return f"{len(rows)} upcoming Starlink launches correlate with {first.get('starlink_conjunction_events')} Starlink-named conjunction events."
    if query_id == "launch_weather_window":
        return f"{len(rows)} upcoming launches checked against current NOAA space-weather scale context."
    if query_id == "closest_spacetrack_enrichment":
        first = rows[0]
        return f"Closest enriched object is {first.get('aegis_name')} classified as {first.get('object_type')} from {first.get('country_code')}."
    if query_id == "high_risk_category_distribution":
        first = rows[0]
        return f"Category {first.get('category')} dominates high-risk events with {first.get('high_risk_events')} entries."
    return f"{result['title']} returned {result['row_count']} rows."


def _correlation_finding(session: InvestigationSession) -> str:
    sources = sorted({source for q in session.executed_queries for source in q["sources"]})
    if len(sources) >= 3:
        return f"Correlation pass combined {len(sources)} source systems: {', '.join(sources)}."
    return f"Correlation pass combined available source systems: {', '.join(sources) or 'none'}."


def _build_assessment(session: InvestigationSession) -> None:
    risk = session.results.get("risk_weather_context", {})
    high = next((row for row in risk.get("rows", []) if row.get("risk") == "HIGH"), None)
    high_count = int(high.get("conjunctions") or 0) if high else 0
    storm = float(high.get("geomagnetic_storm_scale") or 0) if high else 0
    launch_rows = session.results.get("launch_weather_window", {}).get("row_count", 0)
    repeated_rows = session.results.get("repeated_satellite_involvement", {}).get("rows", [])

    parts = []
    if high:
        parts.append(f"Current posture includes {high_count} high-risk conjunctions, with closest miss distance {high.get('closest_km')} km.")
    if repeated_rows:
        parts.append(f"Repeated involvement is concentrated around {repeated_rows[0].get('name')}.")
    if launch_rows:
        parts.append(f"Launch context is active with {launch_rows} upcoming launches checked.")
    if storm >= 3:
        parts.append("NOAA geomagnetic conditions are elevated and should remain in the watch path.")
    elif high:
        parts.append("NOAA geomagnetic activity is currently low, so weather is unlikely to be the primary driver.")
    if not parts:
        parts.append("No strong operational correlation was found from the approved query chain.")

    recommendations = [
        "Continue monitoring closest high-risk conjunctions and refresh Coral snapshots before operational briefing.",
        "Prioritize recurring satellites in follow-up analysis because repeated involvement can indicate localized congestion.",
    ]
    if launch_rows:
        recommendations.append("Review upcoming launch windows against current conjunction density before demo or mission handoff.")
    if storm >= 3:
        recommendations.append("Escalate NOAA weather monitoring cadence while storm scale remains elevated.")

    source_count = len({source for q in session.executed_queries for source in q["sources"]})
    successful_queries = len(session.executed_queries)
    session.confidence = round(min(0.95, 0.35 + 0.08 * successful_queries + 0.08 * source_count), 2)
    session.assessment = " ".join(parts)
    session.recommendations = recommendations[:4]
