-- Phase 3 sample queries for Launch Library 2 data.

-- Upcoming launch manifest.
SELECT net,
       name,
       status_name,
       launch_service_provider,
       rocket_name,
       mission_type,
       orbit_abbrev
  FROM launch_library.upcoming_launches
 ORDER BY net
 LIMIT 10;

-- Provider activity.
SELECT launch_service_provider,
       COUNT(*) AS launches
  FROM launch_library.upcoming_launches
 GROUP BY launch_service_provider
 ORDER BY launches DESC;

-- Cross-source Starlink operational context:
-- upcoming Starlink launch activity with local Starlink-named conjunction count.
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
 LIMIT 10;
