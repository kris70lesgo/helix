-- Phase 3 sample queries for Space-Track data.

-- Latest GP records captured in the bounded snapshot.
SELECT norad_cat_id,
       object_name,
       object_type,
       epoch,
       period,
       apoapsis,
       periapsis
  FROM space_track.gp_current
 ORDER BY epoch DESC
 LIMIT 10;

-- Recent catalog objects by launch date.
SELECT norad_cat_id,
       object_name,
       object_type,
       country,
       launch,
       site
  FROM space_track.satcat_recent
 ORDER BY launch DESC
 LIMIT 10;

-- Cross-source metadata enrichment for AEGIS conjunction objects that appear
-- in the current Space-Track GP snapshot.
SELECT c.risk,
       c.miss_distance_km,
       s.name AS aegis_name,
       gp.object_type,
       gp.country_code,
       gp.epoch
  FROM aegis_core.conjunctions c
  JOIN aegis_core.satellites s ON c.sat1_norad_id = s.norad_id
  JOIN space_track.gp_current gp ON c.sat1_norad_id = gp.norad_cat_id
 ORDER BY c.miss_distance_km ASC
 LIMIT 10;
