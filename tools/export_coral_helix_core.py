#!/usr/bin/env python3
"""Export HELIX SQLite data into Coral file-backed source assets.

Coral 0.4.x supports local file-backed sources through JSONL, JSON, CSV, and
Parquet manifests. The current HELIX source of truth remains backend/helix.db;
this script creates read-only JSONL snapshots for Coral queries.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
ROOT_ALIAS = Path.home() / "Documents" / "helix-coral"
DEFAULT_DB = ROOT / "backend" / "helix.db"
DEFAULT_DATA_DIR = ROOT / "coral" / "data" / "helix_core"
DEFAULT_MANIFEST = ROOT / "coral" / "sources" / "helix_core.yaml"


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


def write_jsonl(path: Path, rows: Iterable[sqlite3.Row]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(dict(row), separators=(",", ":")) + "\n")
            count += 1
    return count


def write_manifest(path: Path, data_dir: Path) -> None:
    location = source_location(data_dir)
    manifest = f"""name: helix_core
version: 0.1.0
dsl_version: 3
backend: file
test_queries:
  - SELECT norad_id, name, category FROM helix_core.satellites LIMIT 1
  - SELECT sat1_norad_id, sat2_norad_id, risk FROM helix_core.conjunctions LIMIT 1
tables:
  - name: satellites
    description: HELIX orbital objects exported from the local SQLite database.
    format: jsonl
    source:
      location: {location}
      glob: "satellites.jsonl"
    columns:
      - name: norad_id
        type: Utf8
        nullable: false
        description: NORAD catalog identifier.
      - name: name
        type: Utf8
        nullable: false
        description: Satellite or debris object name.
      - name: category
        type: Utf8
        description: HELIX object category such as active, stations, starlink, oneweb, planet, spire, or debris.
      - name: tle1
        type: Utf8
        nullable: false
        description: First TLE line.
      - name: tle2
        type: Utf8
        nullable: false
        description: Second TLE line.
      - name: last_updated
        type: Utf8
        description: ISO timestamp from the latest local TLE ingestion.
  - name: conjunctions
    description: HELIX conjunction events exported from the local SQLite database.
    format: jsonl
    source:
      location: {location}
      glob: "conjunctions.jsonl"
    columns:
      - name: id
        type: Int64
        nullable: false
        description: Local conjunction row identifier.
      - name: sat1_norad_id
        type: Utf8
        nullable: false
        description: NORAD identifier for the first object.
      - name: sat2_norad_id
        type: Utf8
        nullable: false
        description: NORAD identifier for the second object.
      - name: tca
        type: Utf8
        nullable: false
        description: ISO timestamp for time of closest approach.
      - name: miss_distance_km
        type: Float64
        nullable: false
        description: Closest approach distance in kilometers.
      - name: relative_velocity_km_s
        type: Float64
        description: Relative velocity in kilometers per second.
      - name: risk
        type: Utf8
        nullable: false
        description: HELIX risk label, one of HIGH, MEDIUM, or LOW.
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(manifest, encoding="utf-8")


def export(db_path: Path, data_dir: Path, manifest_path: Path) -> dict[str, int | str]:
    if not db_path.exists():
        raise FileNotFoundError(f"SQLite database not found: {db_path}")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        satellite_rows = conn.execute(
            """
            SELECT norad_id, name, category, tle1, tle2, last_updated
              FROM satellites
             ORDER BY norad_id
            """
        )
        satellite_count = write_jsonl(data_dir / "satellites.jsonl", satellite_rows)

        conjunction_rows = conn.execute(
            """
            SELECT id,
                   sat1 AS sat1_norad_id,
                   sat2 AS sat2_norad_id,
                   tca,
                   distance AS miss_distance_km,
                   velocity AS relative_velocity_km_s,
                   risk
              FROM conjunctions
             ORDER BY distance ASC, id ASC
            """
        )
        conjunction_count = write_jsonl(data_dir / "conjunctions.jsonl", conjunction_rows)
    finally:
        conn.close()

    write_manifest(manifest_path, data_dir)
    return {
        "db_path": str(db_path),
        "data_dir": str(data_dir),
        "manifest_path": str(manifest_path),
        "satellites": satellite_count,
        "conjunctions": conjunction_count,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args()

    result = export(args.db, args.data_dir, args.manifest)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
