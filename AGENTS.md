# AGENTS.md

Context for working on this repository. Read this first.

## Purpose

Download raw historic hourly weather data from the Open-Meteo archive API for
use as features in electricity-system modelling (demand and renewable-resource
drivers). Scope is deliberately narrow: fetch the raw series and write CSVs.
Nothing more.

Initial plan is one location per country across the markets of interest (GB,
France, Belgium, Portugal, Germany), for model testing. National
capacity-weighted sampling is explicitly out of scope (see below).

## Repository contents

- `download_weather.py` — the only script. Fetches one location's hourly series
  from the Open-Meteo archive API and writes a CSV.
- `schema.sql` — Postgres table for loading the CSVs. Holds the timestamp types
  and the wind-direction sin/cos generated columns. The downloader stays raw;
  derived ML features live here. See README for details.

## Usage

```bash
python download_weather.py --location "London" --out london.csv
python download_weather.py --location "Paris" --start 2018-01-01 --end 2025-12-31
python download_weather.py --lat 51.5 --lon -0.1 --out gb.csv
python download_weather.py --all-capitals --out-dir out
```

Requires `requests` and `pandas`.

### Defaults

- Window: `2018-01-01` to today minus 6 days.
- Variables: defined in the `HOURLY` list at the top of the script. Edit there.
- Time zone: series is fetched in UTC. Wind in m/s.
- Location: by name (geocoded via Open-Meteo) or by `--lat`/`--lon`.

### Time columns

Output leads with identifiers `city`, `country`, `tz`, then `time_utc` and
`time_local`, both ISO 8601. `time_utc` carries a trailing `Z`; `time_local`
carries the city's real DST-aware offset (e.g. `+02:00`), which keeps the
duplicated autumn fall-back hour distinguishable so both columns join cleanly.
The local zone is the IANA name returned by the geocoder, so no zone map is
maintained. With raw `--lat`/`--lon` there is no name to geocode, so `tz`,
`city`, `country` and `time_local` are left blank.

The identifiers let the per-city files load into one table. For Postgres,
`time_utc` -> `timestamptz` and `time_local` -> `timestamp` (without time zone):
a `timestamptz` local column would convert back to the same instant as
`time_utc`. See README for the DDL.

### EU-27 capitals loop

`--all-capitals` iterates the `CAPITALS` list at the top of the script (one city
per member state) and writes one CSV per city to `--out-dir`. Each city is
geocoded for its lat/lon and timezone.

## API facts worth not re-deriving

- Endpoint: `https://archive-api.open-meteo.com/v1/archive`. No API key.
- Data is ERA5 reanalysis: hourly, global, ~25 km (0.25 deg), from 1940.
- The archive lags real time by about 5 days; the script ends at today minus 6
  to stay clear of the edge. A requested end past that should be clamped.
- Free tier is non-commercial: 600 calls/min, 5,000/hour, 10,000/day,
  300,000/month. The Historical Weather API is included on the free tier.
- Call cost is weighted: a request over 2 weeks or 10 variables counts as
  more than one call (fractional). A full 2018-to-present single-location pull
  is one HTTP request but costs roughly 220 calls against the daily budget.
  One point per country (5 pulls) is trivial; no client-side throttling needed.
- Data licence: CC BY 4.0. Attribute Open-Meteo and ERA5/Copernicus in any
  published output.
- Full variable list: https://open-meteo.com/en/docs/historical-weather-api

## Conventions

- British English. No em dashes. Concise, expert-to-expert register.
- Python. Keep the script simple and single-purpose; resist adding features
  that are not asked for.
- Flag uncertainty and data-quality issues honestly rather than papering over.

## Known caveats

- ERA5 is reanalysis (model reconstruction constrained by observations), not
  raw gauge data. Gap-free, but not a station record.
- A single grid cell represents local conditions. It is a reasonable proxy for
  temperature-driven demand but a poor proxy for national wind, which is
  coastal/offshore and spatially decorrelated from a capital city. This matters
  if generation results are ever taken from a single point.
- Commercial-use boundary: the free tier is non-commercial. Academic/research
  use is fine. If a pull feeds commercial trading decisions, that likely needs
  the paid customer plan.

## Out of scope (do not add unless explicitly asked)

- Capacity-weighted multi-point aggregation.
- Wind power-curve or PV capacity-factor transforms.
- Variable "profiles", model-selection flags, or other configurability beyond
  what is in the script today.

These were prototyped earlier and removed deliberately. Keep the tool minimal.

## Likely next steps (only if requested)

- Year-chunking for very large multi-point pulls (not needed at current scope).
