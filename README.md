# power-weather

Download raw historic hourly weather from the Open-Meteo archive API (ERA5
reanalysis) for use as features in electricity-system modelling.

Single purpose: fetch one location's hourly series and write a CSV.

## Install

```bash
pip install -r requirements.txt
```

Requires Python 3.10+.

## Usage

```bash
python download_weather.py --location "London" --out london.csv
python download_weather.py --location "Paris" --start 2018-01-01 --end 2025-12-31
python download_weather.py --lat 51.5 --lon -0.1 --out gb.csv
python download_weather.py --all-capitals --out-dir out
```

Defaults: 2018-01-01 to today minus 6 days (the ERA5 archive lag), UTC, wind in
m/s. The variables fetched are the `HOURLY` list at the top of
`download_weather.py`; edit there to change them. Location is given by name
(geocoded) or by `--lat`/`--lon`.

Each row starts with identifiers `city`, `country`, `country_code` (ISO 3166-1
alpha-2, e.g. `FR`), `tz` (the IANA zone, e.g. `Europe/Paris`), then two time
columns, both ISO 8601: `time_utc` (the fetched
series, with a trailing `Z`) and `time_local` (the same instants with the city's
real DST-aware offset, e.g. `2018-07-01T02:00:00+02:00`). The offset keeps the
duplicated autumn fall-back hour distinguishable, so both columns are safe join
keys. `time_local`, `tz`, `city` and `country` are blank for raw `--lat`/`--lon`
input, where there is no zone to look up.

## Loading into Postgres

`time_utc` loads into a `timestamptz` (it is an instant). For a local wall-clock
column use `timestamp` (without time zone), not `timestamptz`: Postgres ignores
the offset on input to a `timestamp` column and keeps the wall-clock, whereas a
`timestamptz` would convert `time_local` back to the same UTC instant as
`time_utc`, making the two columns identical.

```sql
timestamp_utc   timestamptz NOT NULL,   -- from time_utc
timestamp_local timestamp   NOT NULL,   -- from time_local (offset dropped)
```

The per-city files share one schema, so `COPY` them all into one table; `tz`
lets you recompute local from UTC in SQL (`timestamp_utc AT TIME ZONE tz`).

The full table definition is in `schema.sql`, including a `COPY` example and two
generated columns, `wind_dir_100m_sin` and `wind_dir_100m_cos`. These are the
cyclical encoding of `wind_direction_100m` for ML: `sin` and `cos` together put
each direction on the unit circle, so 359 deg sits next to 1 deg and no two
directions collapse (`sin` alone maps 30 deg and 150 deg the same). The raw
`wind_direction_100m` column is kept; the encoded columns are derived from it.

`--all-capitals` loops the EU-27 capitals plus GB, NO, CH and IS (the `CAPITALS`
list at the top of the script; edit to change) and writes one CSV per city to
`--out-dir`, named `Country_City.csv` (spaces stripped), e.g.
`out/France_Paris.csv`. The per-city timezone, country and country code come from
the geocoder, so there are no hand-maintained maps. The run skips cities whose
file already exists and backs off on rate limits, so it is safe to re-run to
resume an interrupted pull.

## Data

- Source: Open-Meteo Historical Weather API, ERA5 reanalysis (hourly, ~25 km,
  from 1940). No API key.
- The free tier is non-commercial. Academic/research use is fine; commercial
  use needs the paid plan.
- ERA5 is reanalysis, not gauge observation: gap-free but not a station record.

## Attribution

Data is licenced CC BY 4.0 and must be attributed in any published output:

> Weather data from Open-Meteo (https://open-meteo.com), ERA5 reanalysis,
> Copernicus Climate Change Service. Licenced under CC BY 4.0.

## More context

See `AGENTS.md` for full project context, API constraints, and caveats.
