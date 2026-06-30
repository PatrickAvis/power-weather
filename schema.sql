-- Postgres schema for the weather series written by download_weather.py.
--
-- One table for all cities. The per-city CSVs share one column layout, so every
-- file loads into this table with the same COPY (see bottom).
--
-- Time types matter: time_utc is an instant and loads into timestamptz;
-- time_local is a wall-clock and loads into timestamp WITHOUT time zone. A
-- timestamptz local column would convert back to the same UTC instant as
-- timestamp_utc, making the two columns identical.

CREATE TABLE weather (
    city                 text        NOT NULL,
    country              text,
    country_code         text,                  -- ISO 3166-1 alpha-2, e.g. FR
    tz                   text        NOT NULL,  -- IANA zone, e.g. Europe/Paris
    timestamp_utc        timestamptz NOT NULL,  -- from CSV time_utc  (trailing Z)
    timestamp_local      timestamp   NOT NULL,  -- from CSV time_local (offset dropped)

    temperature_2m       double precision,
    relative_humidity_2m double precision,
    precipitation        double precision,
    wind_speed_10m       double precision,
    wind_speed_100m      double precision,
    wind_direction_100m  double precision,      -- raw, degrees, kept as-is
    shortwave_radiation  double precision,
    cloud_cover          double precision,

    -- Cyclical encoding of wind direction for ML. sin and cos together place
    -- each direction on the unit circle, so 359 deg sits next to 1 deg and no
    -- two directions collapse (sin alone would map 30 deg and 150 deg the same).
    -- Generated, so they can never drift from wind_direction_100m.
    -- sind/cosd are degree-based trig (Postgres 14+). On older versions use
    -- sin(radians(wind_direction_100m)) / cos(radians(wind_direction_100m)).
    wind_dir_100m_sin    double precision
        GENERATED ALWAYS AS (sind(wind_direction_100m)) STORED,
    wind_dir_100m_cos    double precision
        GENERATED ALWAYS AS (cosd(wind_direction_100m)) STORED,

    -- timestamp_utc is gap-free and never duplicated, so it is the safe key.
    -- timestamp_local is NOT unique: the autumn DST fall-back hour repeats it.
    PRIMARY KEY (city, timestamp_utc)
);

-- Cross-city queries over a time window benefit from a time index.
CREATE INDEX weather_timestamp_utc_idx ON weather (timestamp_utc);

-- Load one city (repeat per file, or loop in a shell). List the real columns
-- only; the generated wind_dir_* columns are computed, not loaded. The CSV
-- headers (time_utc, time_local) differ from the column names, so COPY maps by
-- this explicit column list, not by header.
--
-- \copy weather (city, country, country_code, tz, timestamp_utc, timestamp_local,
--                temperature_2m, relative_humidity_2m, precipitation,
--                wind_speed_10m, wind_speed_100m, wind_direction_100m,
--                shortwave_radiation, cloud_cover)
--   FROM 'out/France_Paris.csv' WITH (FORMAT csv, HEADER true);
