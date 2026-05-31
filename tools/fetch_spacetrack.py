#!/usr/bin/env python3
"""Fetch bounded Space-Track snapshots into Coral file-backed assets."""

from __future__ import annotations

import argparse
import json
import os
import urllib.parse
import urllib.request
import http.cookiejar
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
ROOT_ALIAS = Path.home() / "Documents" / "helix-coral"
DEFAULT_DATA_DIR = ROOT / "coral" / "data" / "space_track"
DEFAULT_MANIFEST = ROOT / "coral" / "sources" / "space_track.yaml"
LOGIN_URL = "https://www.space-track.org/ajaxauth/login"
QUERY_BASE = "https://www.space-track.org/basicspacedata/query"


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


def load_env() -> dict[str, str]:
    env = dict(os.environ)
    for path in [ROOT / ".env", ROOT / "backend" / ".env"]:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            env.setdefault(key, value)
    return env


def to_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def login(username: str, password: str) -> urllib.request.OpenerDirector:
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    payload = urllib.parse.urlencode({"identity": username, "password": password}).encode()
    request = urllib.request.Request(
        LOGIN_URL,
        data=payload,
        headers={"User-Agent": "HELIX-Coral/0.1"},
    )
    with opener.open(request, timeout=30) as response:
        if response.status != 200:
            raise RuntimeError(f"Space-Track login failed with status {response.status}")
        response.read()
    return opener


def query_json(opener: urllib.request.OpenerDirector, path: str) -> list[dict[str, Any]]:
    encoded_path = urllib.parse.quote(path, safe="/")
    request = urllib.request.Request(
        f"{QUERY_BASE}/{encoded_path}/format/json",
        headers={"User-Agent": "HELIX-Coral/0.1"},
    )
    with opener.open(request, timeout=60) as response:
        return json.load(response)


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, separators=(",", ":")) + "\n")
            count += 1
    return count


def normalize_gp(data: list[dict[str, Any]], fetched_at: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in data:
        rows.append(
            {
                "norad_cat_id": row.get("NORAD_CAT_ID"),
                "object_name": row.get("OBJECT_NAME"),
                "object_id": row.get("OBJECT_ID"),
                "object_type": row.get("OBJECT_TYPE"),
                "country_code": row.get("COUNTRY_CODE"),
                "epoch": row.get("EPOCH"),
                "creation_date": row.get("CREATION_DATE"),
                "launch_date": row.get("LAUNCH_DATE"),
                "decay_date": row.get("DECAY_DATE"),
                "inclination": to_float(row.get("INCLINATION")),
                "eccentricity": to_float(row.get("ECCENTRICITY")),
                "mean_motion": to_float(row.get("MEAN_MOTION")),
                "period": to_float(row.get("PERIOD")),
                "semimajor_axis": to_float(row.get("SEMIMAJOR_AXIS")),
                "apoapsis": to_float(row.get("APOAPSIS")),
                "periapsis": to_float(row.get("PERIAPSIS")),
                "tle_line0": row.get("TLE_LINE0"),
                "tle_line1": row.get("TLE_LINE1"),
                "tle_line2": row.get("TLE_LINE2"),
                "fetched_at": fetched_at,
            }
        )
    return rows


def normalize_satcat(data: list[dict[str, Any]], fetched_at: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in data:
        rows.append(
            {
                "norad_cat_id": row.get("NORAD_CAT_ID"),
                "object_number": row.get("OBJECT_NUMBER"),
                "object_name": row.get("OBJECT_NAME") or row.get("SATNAME"),
                "object_id": row.get("OBJECT_ID") or row.get("INTLDES"),
                "object_type": row.get("OBJECT_TYPE"),
                "country": row.get("COUNTRY"),
                "launch": row.get("LAUNCH"),
                "site": row.get("SITE"),
                "decay": row.get("DECAY"),
                "period": to_float(row.get("PERIOD")),
                "inclination": to_float(row.get("INCLINATION")),
                "apogee": to_float(row.get("APOGEE")),
                "perigee": to_float(row.get("PERIGEE")),
                "current": row.get("CURRENT"),
                "rcs_size": row.get("RCS_SIZE"),
                "fetched_at": fetched_at,
            }
        )
    return rows


def write_manifest(path: Path, data_dir: Path) -> None:
    location = source_location(data_dir)
    manifest = f"""name: space_track
version: 0.1.0
dsl_version: 3
backend: file
test_queries:
  - SELECT norad_cat_id, object_name, epoch FROM space_track.gp_current LIMIT 1
  - SELECT norad_cat_id, object_name, launch FROM space_track.satcat_recent LIMIT 1
tables:
  - name: gp_current
    description: Bounded current GP records from Space-Track.
    format: jsonl
    source:
      location: {location}
      glob: "gp_current.jsonl"
    columns:
      - name: norad_cat_id
        type: Utf8
        nullable: false
      - name: object_name
        type: Utf8
      - name: object_id
        type: Utf8
      - name: object_type
        type: Utf8
      - name: country_code
        type: Utf8
      - name: epoch
        type: Utf8
      - name: creation_date
        type: Utf8
      - name: launch_date
        type: Utf8
      - name: decay_date
        type: Utf8
      - name: inclination
        type: Float64
      - name: eccentricity
        type: Float64
      - name: mean_motion
        type: Float64
      - name: period
        type: Float64
      - name: semimajor_axis
        type: Float64
      - name: apoapsis
        type: Float64
      - name: periapsis
        type: Float64
      - name: tle_line0
        type: Utf8
      - name: tle_line1
        type: Utf8
      - name: tle_line2
        type: Utf8
      - name: fetched_at
        type: Utf8
        nullable: false
  - name: satcat_recent
    description: Bounded recent SATCAT records from Space-Track.
    format: jsonl
    source:
      location: {location}
      glob: "satcat_recent.jsonl"
    columns:
      - name: norad_cat_id
        type: Utf8
        nullable: false
      - name: object_number
        type: Utf8
      - name: object_name
        type: Utf8
      - name: object_id
        type: Utf8
      - name: object_type
        type: Utf8
      - name: country
        type: Utf8
      - name: launch
        type: Utf8
      - name: site
        type: Utf8
      - name: decay
        type: Utf8
      - name: period
        type: Float64
      - name: inclination
        type: Float64
      - name: apogee
        type: Float64
      - name: perigee
        type: Float64
      - name: current
        type: Utf8
      - name: rcs_size
        type: Utf8
      - name: fetched_at
        type: Utf8
        nullable: false
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(manifest, encoding="utf-8")


def export(data_dir: Path, manifest_path: Path, limit: int) -> dict[str, Any]:
    env = load_env()
    username = env.get("SPACE_TRACK_USERNAME")
    password = env.get("SPACE_TRACK_PASSWORD")
    if not username or not password:
        raise RuntimeError("SPACE_TRACK_USERNAME and SPACE_TRACK_PASSWORD are required")

    fetched_at = datetime.now(timezone.utc).isoformat()
    opener = login(username, password)
    gp_raw = query_json(opener, f"class/gp/orderby/EPOCH desc/limit/{limit}")
    satcat_raw = query_json(opener, f"class/satcat/orderby/LAUNCH desc/limit/{limit}")

    gp_count = write_jsonl(data_dir / "gp_current.jsonl", normalize_gp(gp_raw, fetched_at))
    satcat_count = write_jsonl(
        data_dir / "satcat_recent.jsonl",
        normalize_satcat(satcat_raw, fetched_at),
    )
    write_manifest(manifest_path, data_dir)
    return {
        "data_dir": str(data_dir),
        "manifest_path": str(manifest_path),
        "fetched_at": fetched_at,
        "gp_current": gp_count,
        "satcat_recent": satcat_count,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--limit", type=int, default=1000)
    args = parser.parse_args()
    print(json.dumps(export(args.data_dir, args.manifest, args.limit), indent=2))


if __name__ == "__main__":
    main()
