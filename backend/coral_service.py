"""Small Coral CLI execution wrapper for backend intelligence endpoints."""

from __future__ import annotations

import json
import shutil
import subprocess
import time
from dataclasses import asdict
from typing import Any

from coral_queries import QUERIES, list_queries


class CoralUnavailable(RuntimeError):
    pass


def ensure_coral() -> str:
    coral = shutil.which("coral")
    if not coral:
        raise CoralUnavailable("coral CLI is not installed or not on PATH")
    return coral


def run_sql(sql: str, timeout_seconds: int = 30) -> dict[str, Any]:
    coral = ensure_coral()
    started = time.perf_counter()
    proc = subprocess.run(
        [coral, "sql", "--format", "json", sql],
        text=True,
        capture_output=True,
        timeout=timeout_seconds,
        check=False,
    )
    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "coral sql failed")
    rows = json.loads(proc.stdout or "[]")
    return {
        "rows": rows,
        "row_count": len(rows),
        "elapsed_ms": elapsed_ms,
    }


def run_query(query_id: str) -> dict[str, Any]:
    query = QUERIES.get(query_id)
    if not query:
        raise KeyError(query_id)
    result = run_sql(query.sql)
    return {
        "id": query_id,
        **asdict(query),
        **result,
    }


def benchmark_queries() -> dict[str, Any]:
    results = []
    for query_id in QUERIES:
        try:
            result = run_query(query_id)
            results.append(
                {
                    "id": query_id,
                    "ok": True,
                    "row_count": result["row_count"],
                    "elapsed_ms": result["elapsed_ms"],
                }
            )
        except Exception as exc:
            results.append({"id": query_id, "ok": False, "error": str(exc)})
    return {
        "queries": list_queries(),
        "results": results,
    }
