#!/usr/bin/env python3
"""Fetch Launch Library 2 upcoming launches into Coral file-backed assets."""

from __future__ import annotations

import argparse
import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
ROOT_ALIAS = Path.home() / "Documents" / "helix-coral"
DEFAULT_DATA_DIR = ROOT / "coral" / "data" / "launch_library"
DEFAULT_MANIFEST = ROOT / "coral" / "sources" / "launch_library.yaml"
BASE_URL = "https://ll.thespacedevs.com/2.3.0/launches/upcoming/"


def source_location(data_dir: Path) -> str:
    if ROOT_ALIAS.exists() and ROOT_ALIAS.resolve() == ROOT:
        try:
            relative = data_dir.resolve().relative_to(ROOT)
            return (ROOT_ALIAS / relative).as_uri() + "/"
        except ValueError:
            pass
    try:
        relative = data_dir.resolve().relative_to(ROOT)
        return f"file:{relative.as_posix()}/"
    except ValueError:
        return data_dir.resolve().as_uri() + "/"


def nested(data: dict[str, Any], *keys: str) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def fetch_upcoming(limit: int) -> dict[str, Any]:
    query = urllib.parse.urlencode({"limit": limit})
    request = urllib.request.Request(
        f"{BASE_URL}?{query}",
        headers={"User-Agent": "HELIX-Coral/0.1"},
    )
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


def normalize_launches(data: dict[str, Any], fetched_at: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for launch in data.get("results", []):
        mission = launch.get("mission") or {}
        pad = launch.get("pad") or {}
        location = pad.get("location") or {}
        rocket_config = nested(launch, "rocket", "configuration") or {}
        provider = launch.get("launch_service_provider") or {}
        orbit = mission.get("orbit") or {}

        rows.append(
            {
                "launch_id": launch.get("id"),
                "name": launch.get("name"),
                "slug": launch.get("slug"),
                "status_name": nested(launch, "status", "name"),
                "status_abbrev": nested(launch, "status", "abbrev"),
                "net": launch.get("net"),
                "window_start": launch.get("window_start"),
                "window_end": launch.get("window_end"),
                "last_updated": launch.get("last_updated"),
                "probability": launch.get("probability"),
                "weather_concerns": launch.get("weather_concerns"),
                "launch_service_provider": provider.get("name"),
                "provider_type": nested(provider, "type", "name"),
                "rocket_name": rocket_config.get("full_name") or rocket_config.get("name"),
                "rocket_family": ", ".join(
                    family.get("name", "")
                    for family in (rocket_config.get("families") or [])
                    if family.get("name")
                )
                or None,
                "mission_name": mission.get("name"),
                "mission_type": mission.get("type"),
                "mission_description": mission.get("description"),
                "orbit_name": orbit.get("name"),
                "orbit_abbrev": orbit.get("abbrev"),
                "pad_name": pad.get("name"),
                "pad_location_name": location.get("name"),
                "pad_country_code": location.get("country_code"),
                "fetched_at": fetched_at,
            }
        )
    return rows


def write_manifest(path: Path, data_dir: Path) -> None:
    location = source_location(data_dir)
    manifest = f"""name: launch_library
version: 0.1.0
dsl_version: 3
backend: file
test_queries:
  - SELECT launch_id, name, net FROM launch_library.upcoming_launches ORDER BY net LIMIT 1
  - SELECT launch_service_provider, COUNT(*) AS launches FROM launch_library.upcoming_launches GROUP BY launch_service_provider LIMIT 5
tables:
  - name: upcoming_launches
    description: Upcoming launches from The Space Devs Launch Library 2 API.
    format: jsonl
    source:
      location: {location}
      glob: "upcoming_launches.jsonl"
    columns:
      - name: launch_id
        type: Utf8
        nullable: false
      - name: name
        type: Utf8
        nullable: false
      - name: slug
        type: Utf8
      - name: status_name
        type: Utf8
      - name: status_abbrev
        type: Utf8
      - name: net
        type: Utf8
        description: No-earlier-than launch timestamp.
      - name: window_start
        type: Utf8
      - name: window_end
        type: Utf8
      - name: last_updated
        type: Utf8
      - name: probability
        type: Float64
      - name: weather_concerns
        type: Utf8
      - name: launch_service_provider
        type: Utf8
      - name: provider_type
        type: Utf8
      - name: rocket_name
        type: Utf8
      - name: rocket_family
        type: Utf8
      - name: mission_name
        type: Utf8
      - name: mission_type
        type: Utf8
      - name: mission_description
        type: Utf8
      - name: orbit_name
        type: Utf8
      - name: orbit_abbrev
        type: Utf8
      - name: pad_name
        type: Utf8
      - name: pad_location_name
        type: Utf8
      - name: pad_country_code
        type: Utf8
      - name: fetched_at
        type: Utf8
        nullable: false
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(manifest, encoding="utf-8")


def export(data_dir: Path, manifest_path: Path, limit: int) -> dict[str, Any]:
    fetched_at = datetime.now(timezone.utc).isoformat()
    raw = fetch_upcoming(limit)
    rows = normalize_launches(raw, fetched_at)
    count = write_jsonl(data_dir / "upcoming_launches.jsonl", rows)
    write_manifest(manifest_path, data_dir)
    return {
        "data_dir": str(data_dir),
        "manifest_path": str(manifest_path),
        "fetched_at": fetched_at,
        "api_count": raw.get("count"),
        "upcoming_launches": count,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--limit", type=int, default=50)
    args = parser.parse_args()

    print(json.dumps(export(args.data_dir, args.manifest, args.limit), indent=2))


if __name__ == "__main__":
    main()
