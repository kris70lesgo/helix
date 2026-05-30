"""Predefined Coral operational intelligence queries for AEGIS."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CoralQuery:
    title: str
    description: str
    sql: str


QUERIES: dict[str, CoralQuery] = {
    "risk_weather_context": CoralQuery(
        title="Risk distribution with current NOAA space weather",
        description="Summarizes local AEGIS conjunction risk under the current NOAA scale context.",
        sql="""
SELECT c.risk,
       COUNT(*) AS conjunctions,
       ROUND(MIN(c.miss_distance_km), 3) AS closest_km,
       n.date_stamp AS noaa_date,
       n.geomagnetic_storm_scale,
       n.geomagnetic_storm_text,
       n.solar_radiation_scale
  FROM aegis_core.conjunctions c
 CROSS JOIN (
       SELECT date_stamp,
              geomagnetic_storm_scale,
              geomagnetic_storm_text,
              solar_radiation_scale
         FROM noaa_space_weather.noaa_scales
        WHERE period_key = '0'
        LIMIT 1
      ) n
 GROUP BY c.risk,
          n.date_stamp,
          n.geomagnetic_storm_scale,
          n.geomagnetic_storm_text,
          n.solar_radiation_scale
 ORDER BY conjunctions DESC
""".strip(),
    ),
    "closest_spacetrack_enrichment": CoralQuery(
        title="Closest conjunctions enriched with Space-Track metadata",
        description="Joins AEGIS risk events to current Space-Track GP metadata for object type and country.",
        sql="""
SELECT c.risk,
       c.miss_distance_km,
       c.relative_velocity_km_s,
       s.name AS aegis_name,
       gp.object_type,
       gp.country_code,
       gp.epoch
  FROM aegis_core.conjunctions c
  JOIN aegis_core.satellites s ON c.sat1_norad_id = s.norad_id
  JOIN space_track.gp_current gp ON c.sat1_norad_id = gp.norad_cat_id
 ORDER BY c.miss_distance_km ASC
 LIMIT 20
""".strip(),
    ),
    "starlink_launch_context": CoralQuery(
        title="Upcoming Starlink launches with local conjunction context",
        description="Correlates upcoming Starlink launch activity with current local Starlink-named conjunction volume.",
        sql="""
SELECT l.net,
       l.name AS launch_name,
       l.launch_service_provider,
       l.orbit_abbrev,
       sc.starlink_conjunction_events
  FROM launch_library.upcoming_launches l
 CROSS JOIN (
       SELECT COUNT(DISTINCT c.id) AS starlink_conjunction_events
         FROM aegis_core.satellites s
         JOIN aegis_core.conjunctions c
           ON c.sat1_norad_id = s.norad_id OR c.sat2_norad_id = s.norad_id
        WHERE lower(s.name) LIKE '%starlink%'
      ) sc
 WHERE lower(l.name) LIKE '%starlink%'
 ORDER BY l.net
 LIMIT 10
""".strip(),
    ),
    "launch_weather_window": CoralQuery(
        title="Upcoming launches with current NOAA scale context",
        description="Combines launch schedule data with current NOAA space-weather scales for operational briefing.",
        sql="""
SELECT l.net,
       l.name AS launch_name,
       l.launch_service_provider,
       l.mission_type,
       l.orbit_abbrev,
       n.geomagnetic_storm_scale,
       n.geomagnetic_storm_text,
       n.solar_radiation_scale
  FROM launch_library.upcoming_launches l
 CROSS JOIN (
       SELECT geomagnetic_storm_scale,
              geomagnetic_storm_text,
              solar_radiation_scale
         FROM noaa_space_weather.noaa_scales
        WHERE period_key = '0'
        LIMIT 1
      ) n
 ORDER BY l.net
 LIMIT 15
""".strip(),
    ),
    "repeated_satellite_involvement": CoralQuery(
        title="Repeated satellite involvement in conjunction events",
        description="Finds satellites that recur most often in the current conjunction snapshot.",
        sql="""
WITH participants AS (
       SELECT sat1_norad_id AS norad_id, risk, miss_distance_km
         FROM aegis_core.conjunctions
        UNION ALL
       SELECT sat2_norad_id AS norad_id, risk, miss_distance_km
         FROM aegis_core.conjunctions
)
SELECT p.norad_id,
       s.name,
       s.category,
       COUNT(*) AS conjunction_events,
       SUM(CASE WHEN p.risk = 'HIGH' THEN 1 ELSE 0 END) AS high_risk_events,
       ROUND(MIN(p.miss_distance_km), 3) AS closest_km
  FROM participants p
  JOIN aegis_core.satellites s ON p.norad_id = s.norad_id
 GROUP BY p.norad_id, s.name, s.category
 ORDER BY high_risk_events DESC, conjunction_events DESC
 LIMIT 20
""".strip(),
    ),
    "risk_density_by_day": CoralQuery(
        title="Conjunction density by TCA day",
        description="Shows current stored conjunction density and high-risk volume by day.",
        sql="""
SELECT substr(tca, 1, 10) AS event_date,
       COUNT(*) AS conjunction_events,
       SUM(CASE WHEN risk = 'HIGH' THEN 1 ELSE 0 END) AS high_risk_events,
       ROUND(MIN(miss_distance_km), 3) AS closest_km
  FROM aegis_core.conjunctions
 GROUP BY substr(tca, 1, 10)
 ORDER BY event_date DESC
 LIMIT 14
""".strip(),
    ),
    "high_risk_category_distribution": CoralQuery(
        title="High-risk conjunction distribution by satellite category",
        description="Summarizes high-risk events by satellite category for pattern analysis.",
        sql="""
SELECT s.category,
       COUNT(DISTINCT c.id) AS high_risk_events,
       ROUND(MIN(c.miss_distance_km), 3) AS closest_km
  FROM aegis_core.conjunctions c
  JOIN aegis_core.satellites s
    ON c.sat1_norad_id = s.norad_id OR c.sat2_norad_id = s.norad_id
 WHERE c.risk = 'HIGH'
 GROUP BY s.category
 ORDER BY high_risk_events DESC
 LIMIT 10
""".strip(),
    ),
    "closest_high_risk_events": CoralQuery(
        title="Closest high-risk conjunction events",
        description="Returns closest high-risk conjunctions with both satellite names.",
        sql="""
SELECT c.tca,
       c.miss_distance_km,
       c.relative_velocity_km_s,
       c.sat1_norad_id,
       s1.name AS sat1_name,
       c.sat2_norad_id,
       s2.name AS sat2_name
  FROM aegis_core.conjunctions c
  JOIN aegis_core.satellites s1 ON c.sat1_norad_id = s1.norad_id
  JOIN aegis_core.satellites s2 ON c.sat2_norad_id = s2.norad_id
 WHERE c.risk = 'HIGH'
 ORDER BY c.miss_distance_km ASC
 LIMIT 20
""".strip(),
    ),
}


def list_queries() -> list[dict[str, str]]:
    return [
        {
            "id": query_id,
            "title": query.title,
            "description": query.description,
        }
        for query_id, query in QUERIES.items()
    ]
