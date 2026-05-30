-- Phase 3 sample queries for NOAA SWPC space weather data.

-- Latest observed Kp value.
SELECT time_tag,
       kp,
       station_count
  FROM noaa_space_weather.kp_observed
 ORDER BY time_tag DESC
 LIMIT 1;

-- Forecast geomagnetic storm conditions.
SELECT date_stamp,
       time_stamp,
       geomagnetic_storm_scale,
       geomagnetic_storm_text
  FROM noaa_space_weather.noaa_scales
 ORDER BY date_stamp, time_stamp;

-- NOAA alerts with parsed scale labels.
SELECT issue_datetime,
       product_id,
       message_code,
       noaa_scale,
       noaa_scale_text
  FROM noaa_space_weather.alerts
 ORDER BY issue_datetime DESC
 LIMIT 10;

-- Date-overlap cross-source correlation:
-- high-risk AEGIS conjunctions on days with NOAA Kp observations.
-- This returns rows only when the local conjunction snapshot overlaps the
-- live NOAA observation window.
SELECT substr(c.tca, 1, 10) AS event_date,
       COUNT(*) AS high_risk_conjunctions,
       ROUND(MAX(k.kp), 2) AS max_observed_kp
  FROM aegis_core.conjunctions c
  JOIN noaa_space_weather.kp_observed k
    ON substr(c.tca, 1, 10) = substr(k.time_tag, 1, 10)
 WHERE c.risk = 'HIGH'
 GROUP BY event_date
 ORDER BY event_date DESC;

-- Demo-safe current operational context:
-- current NOAA scale context attached to local AEGIS risk distribution.
SELECT c.risk,
       COUNT(*) AS conjunctions,
       n.date_stamp,
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
 ORDER BY conjunctions DESC;
