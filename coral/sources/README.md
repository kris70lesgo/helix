# Coral Sources

Source manifests and source-specific setup notes live here.

Current source:

- `aegis_core.yaml`: file-backed source generated from `backend/aegis.db`.
- `noaa_space_weather.yaml`: file-backed source generated from NOAA SWPC public JSON products.
- `launch_library.yaml`: file-backed source generated from Launch Library 2 upcoming launches.
- `space_track.yaml`: file-backed source generated from bounded Space-Track API snapshots.

Regenerate it with:

```bash
python3 tools/export_coral_aegis_core.py
coral source lint coral/sources/aegis_core.yaml
coral source add --file coral/sources/aegis_core.yaml
```

Regenerate NOAA with:

```bash
python3 tools/fetch_noaa_space_weather.py
coral source lint coral/sources/noaa_space_weather.yaml
coral source add --file coral/sources/noaa_space_weather.yaml
```

Regenerate Launch Library:

```bash
python3 tools/fetch_launch_library.py --limit 50
coral source lint coral/sources/launch_library.yaml
coral source add --file coral/sources/launch_library.yaml
```

Regenerate Space-Track:

```bash
python3 tools/fetch_spacetrack.py --limit 1000
coral source lint coral/sources/space_track.yaml
coral source add --file coral/sources/space_track.yaml
```
