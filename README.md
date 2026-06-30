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

Each CSV starts with two time columns, both ISO 8601: `time_utc` (the fetched
series, with a trailing `Z`) and `time_local` (the same instants with the city's
real DST-aware offset, e.g. `2018-07-01T02:00:00+02:00`). The offset keeps the
duplicated autumn fall-back hour distinguishable, so both columns are safe join
keys. `time_local` is blank for raw `--lat`/`--lon` input, where there is no zone
to look up.

`--all-capitals` loops the EU-27 capitals (the `CAPITALS` list at the top of the
script; edit to change) and writes one CSV per city to `--out-dir`, e.g.
`out/Paris.csv`. The per-city timezone comes from the geocoder, so there is no
hand-maintained zone map.

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
