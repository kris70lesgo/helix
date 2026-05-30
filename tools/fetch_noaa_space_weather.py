#!/usr/bin/env python3
"""Fetch NOAA SWPC public JSON products into Coral file-backed assets."""

from __future__ import annotations

import argparse
import json
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = ROOT / "coral" / "data" / "noaa_space_weather"
DEFAULT_MANIFEST = ROOT / "coral" / "sources" / "noaa_space_weather.yaml"

PRODUCTS = {
    "kp_observed": "https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json",
    "kp_forecast": "https://services.swpc.noaa.gov/products/noaa-planetary-k-index-forecast.json",
    "noaa_scales": "https://services.swpc.noaa.gov/products/noaa-scales.json",
    "alerts": "https://services.swpc.noaa.gov/products/alerts.json",
}


def source_location(data_dir: Path) -> str:
    try:
        relative = data_dir.resolve().relative_to(ROOT)
        return f"file:{relative.as_posix()}/"
    except ValueError:
        return data_dir.resolve().as_uri() + "/"


def fetch_json(url: str) -> Any:
    request = urllib.request.Request(url, headers={"User-Agent": "AEGIS-Coral/0.1"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, separators=(",", ":")) + "\n")
            count += 1
    return count


def to_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def normalize_kp_observed(data: list[dict[str, Any]], fetched_at: str) -> list[dict[str, Any]]:
    return [
        {
            "time_tag": row.get("time_tag"),
            "kp": to_float(row.get("Kp")),
            "a_running": to_float(row.get("a_running")),
            "station_count": to_float(row.get("station_count")),
            "fetched_at": fetched_at,
        }
        for row in data
    ]


def normalize_kp_forecast(data: list[dict[str, Any]], fetched_at: str) -> list[dict[str, Any]]:
    return [
        {
            "time_tag": row.get("time_tag"),
            "kp": to_float(row.get("kp")),
            "observed_status": row.get("observed"),
            "noaa_scale": row.get("noaa_scale"),
            "fetched_at": fetched_at,
        }
        for row in data
    ]


def normalize_noaa_scales(data: dict[str, Any], fetched_at: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for period_key, value in data.items():
        r = value.get("R", {}) or {}
        s = value.get("S", {}) or {}
        g = value.get("G", {}) or {}
        rows.append(
            {
                "period_key": period_key,
                "date_stamp": value.get("DateStamp"),
                "time_stamp": value.get("TimeStamp"),
                "radio_blackout_scale": to_float(r.get("Scale")),
                "radio_blackout_text": r.get("Text"),
                "radio_blackout_minor_probability": to_float(r.get("MinorProb")),
                "radio_blackout_major_probability": to_float(r.get("MajorProb")),
                "solar_radiation_scale": to_float(s.get("Scale")),
                "solar_radiation_text": s.get("Text"),
                "solar_radiation_probability": to_float(s.get("Prob")),
                "geomagnetic_storm_scale": to_float(g.get("Scale")),
                "geomagnetic_storm_text": g.get("Text"),
                "fetched_at": fetched_at,
            }
        )
    return rows


def normalize_alerts(data: list[dict[str, Any]], fetched_at: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    scale_pattern = re.compile(r"NOAA\\s+Scale:\\s*([RSG]\\d)\\s*-\\s*([^\\r\\n]+)", re.IGNORECASE)
    code_pattern = re.compile(r"Space Weather Message Code:\\s*([^\\r\\n]+)", re.IGNORECASE)

    for row in data:
        message = row.get("message") or ""
        scale_match = scale_pattern.search(message)
        code_match = code_pattern.search(message)
        rows.append(
            {
                "product_id": row.get("product_id"),
                "issue_datetime": row.get("issue_datetime"),
                "message_code": code_match.group(1).strip() if code_match else None,
                "noaa_scale": scale_match.group(1).upper() if scale_match else None,
                "noaa_scale_text": scale_match.group(2).strip() if scale_match else None,
                "message": message,
                "fetched_at": fetched_at,
            }
        )
    return rows


def write_manifest(path: Path, data_dir: Path) -> None:
    location = source_location(data_dir)
    manifest = f"""name: noaa_space_weather
version: 0.1.0
dsl_version: 3
backend: file
test_queries:
  - SELECT time_tag, kp FROM noaa_space_weather.kp_observed ORDER BY time_tag DESC LIMIT 1
  - SELECT date_stamp, geomagnetic_storm_scale FROM noaa_space_weather.noaa_scales LIMIT 1
tables:
  - name: kp_observed
    description: Observed NOAA planetary K-index values from SWPC.
    format: jsonl
    source:
      location: {location}
      glob: "kp_observed.jsonl"
    columns:
      - name: time_tag
        type: Utf8
        nullable: false
        description: Observation timestamp.
      - name: kp
        type: Float64
        description: Planetary K-index.
      - name: a_running
        type: Float64
        description: Running A-index value.
      - name: station_count
        type: Float64
        description: Number of contributing stations.
      - name: fetched_at
        type: Utf8
        nullable: false
        description: Snapshot fetch timestamp.
  - name: kp_forecast
    description: NOAA planetary K-index observed and forecast values from SWPC.
    format: jsonl
    source:
      location: {location}
      glob: "kp_forecast.jsonl"
    columns:
      - name: time_tag
        type: Utf8
        nullable: false
        description: Forecast timestamp.
      - name: kp
        type: Float64
        description: Planetary K-index value.
      - name: observed_status
        type: Utf8
        description: NOAA observed/estimated/forecast label.
      - name: noaa_scale
        type: Utf8
        description: NOAA geomagnetic scale label when provided.
      - name: fetched_at
        type: Utf8
        nullable: false
        description: Snapshot fetch timestamp.
  - name: noaa_scales
    description: Current and forecast NOAA space weather scales.
    format: jsonl
    source:
      location: {location}
      glob: "noaa_scales.jsonl"
    columns:
      - name: period_key
        type: Utf8
        nullable: false
        description: NOAA product period key.
      - name: date_stamp
        type: Utf8
        nullable: false
        description: Forecast date.
      - name: time_stamp
        type: Utf8
        nullable: false
        description: Forecast time.
      - name: radio_blackout_scale
        type: Float64
      - name: radio_blackout_text
        type: Utf8
      - name: radio_blackout_minor_probability
        type: Float64
      - name: radio_blackout_major_probability
        type: Float64
      - name: solar_radiation_scale
        type: Float64
      - name: solar_radiation_text
        type: Utf8
      - name: solar_radiation_probability
        type: Float64
      - name: geomagnetic_storm_scale
        type: Float64
      - name: geomagnetic_storm_text
        type: Utf8
      - name: fetched_at
        type: Utf8
        nullable: false
        description: Snapshot fetch timestamp.
  - name: alerts
    description: NOAA SWPC watches, warnings, alerts, and summaries.
    format: jsonl
    source:
      location: {location}
      glob: "alerts.jsonl"
    columns:
      - name: product_id
        type: Utf8
        nullable: false
      - name: issue_datetime
        type: Utf8
        nullable: false
      - name: message_code
        type: Utf8
      - name: noaa_scale
        type: Utf8
      - name: noaa_scale_text
        type: Utf8
      - name: message
        type: Utf8
        nullable: false
      - name: fetched_at
        type: Utf8
        nullable: false
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(manifest, encoding="utf-8")


def export(data_dir: Path, manifest_path: Path) -> dict[str, Any]:
    fetched_at = datetime.now(timezone.utc).isoformat()
    raw = {name: fetch_json(url) for name, url in PRODUCTS.items()}

    rows = {
        "kp_observed": normalize_kp_observed(raw["kp_observed"], fetched_at),
        "kp_forecast": normalize_kp_forecast(raw["kp_forecast"], fetched_at),
        "noaa_scales": normalize_noaa_scales(raw["noaa_scales"], fetched_at),
        "alerts": normalize_alerts(raw["alerts"], fetched_at),
    }

    counts = {
        name: write_jsonl(data_dir / f"{name}.jsonl", table_rows)
        for name, table_rows in rows.items()
    }
    write_manifest(manifest_path, data_dir)
    return {
        "data_dir": str(data_dir),
        "manifest_path": str(manifest_path),
        "fetched_at": fetched_at,
        **counts,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args()

    print(json.dumps(export(args.data_dir, args.manifest), indent=2))


if __name__ == "__main__":
    main()
