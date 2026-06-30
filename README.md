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
```

Defaults: 2018-01-01 to today minus 6 days (the ERA5 archive lag), UTC, wind in
m/s. The variables fetched are the `HOURLY` list at the top of
`download_weather.py`; edit there to change them. Location is given by name
(geocoded) or by `--lat`/`--lon`.

Pull one location per country by running it once per location, e.g.:

```bash
for loc in "London" "Paris" "Brussels" "Lisbon" "Berlin"; do
    python download_weather.py --location "$loc" --out "${loc// /_}.csv"
done
```

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
