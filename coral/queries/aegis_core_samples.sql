-- Phase 2 sample queries for the internal AEGIS Coral source.

-- Risk distribution.
SELECT risk,
       COUNT(*) AS events,
       ROUND(MIN(miss_distance_km), 3) AS closest_km
  FROM aegis_core.conjunctions
 GROUP BY risk
 ORDER BY events DESC;

-- Closest conjunctions with satellite names.
SELECT c.risk,
       c.miss_distance_km,
       c.relative_velocity_km_s,
       s1.name AS sat1_name,
       s2.name AS sat2_name
  FROM aegis_core.conjunctions c
  JOIN aegis_core.satellites s1 ON c.sat1_norad_id = s1.norad_id
  JOIN aegis_core.satellites s2 ON c.sat2_norad_id = s2.norad_id
 ORDER BY c.miss_distance_km ASC
 LIMIT 5;

-- High-risk event categories.
SELECT s.category,
       COUNT(*) AS high_risk_events
  FROM aegis_core.conjunctions c
  JOIN aegis_core.satellites s ON c.sat1_norad_id = s.norad_id
 WHERE c.risk = 'HIGH'
 GROUP BY s.category
 ORDER BY high_risk_events DESC
 LIMIT 8;
