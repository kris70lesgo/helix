# Coral Data Snapshots

Generated JSONL snapshots for local Coral file-backed sources live here.

Regenerate the internal AEGIS source with:

```bash
python3 tools/export_coral_aegis_core.py
```

Regenerate the NOAA space weather source with:

```bash
python3 tools/fetch_noaa_space_weather.py
```

Regenerate the Launch Library source with:

```bash
python3 tools/fetch_launch_library.py --limit 50
```

Regenerate the Space-Track source with:

```bash
python3 tools/fetch_spacetrack.py --limit 1000
```

The SQLite source of truth remains `backend/aegis.db`.
