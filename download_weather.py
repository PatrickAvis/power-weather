"""
Download raw hourly historical weather from the Open-Meteo archive API (ERA5).
No API key. Data is CC BY 4.0 (attribute Open-Meteo / ERA5).

Examples:
    python download_weather.py --location "London"
    python download_weather.py --location "Paris" --start 2018-01-01 --end 2025-12-31
    python download_weather.py --lat 51.5 --lon -0.1 --out london.csv
    python download_weather.py --all-capitals --out-dir out
"""

import argparse
import datetime as dt
import os
import time
import requests
import pandas as pd

# Big archive pulls are rate-limited (HTTP 429). Retry with backoff, honouring
# the Retry-After header when the server sends one.
MAX_RETRIES = 8

ARCHIVE = "https://archive-api.open-meteo.com/v1/archive"
GEOCODE = "https://geocoding-api.open-meteo.com/v1/search"

# Hourly variables to download. Add or remove as you like.
HOURLY = [
    "temperature_2m",
    "relative_humidity_2m",
    "precipitation",
    "wind_speed_10m",
    "wind_speed_100m",
    "wind_direction_100m",
    "shortwave_radiation",
    "cloud_cover",
]

# EU-27 capitals plus selected non-EU European ones (GB, NO, CH, IS). Edit as
# you like. The timezone, country and country code for each are taken from the
# geocoder, so no hand-maintained maps are needed.
CAPITALS = [
    "Vienna", "Brussels", "Sofia", "Zagreb", "Nicosia", "Prague",
    "Copenhagen", "Tallinn", "Helsinki", "Paris", "Berlin", "Athens",
    "Budapest", "Dublin", "Rome", "Riga", "Vilnius", "Luxembourg",
    "Valletta", "Amsterdam", "Warsaw", "Lisbon", "Bucharest",
    "Bratislava", "Ljubljana", "Madrid", "Stockholm",
    "London", "Oslo", "Bern", "Reykjavik",
]


def geocode(name):
    r = requests.get(GEOCODE, params={"name": name, "count": 1}, timeout=30)
    r.raise_for_status()
    hits = r.json().get("results")
    if not hits:
        raise SystemExit(f"No match for '{name}'. Use --lat/--lon instead.")
    h = hits[0]
    return (h["latitude"], h["longitude"], h.get("timezone"),
            h.get("country"), h.get("country_code"))


def fetch(lat, lon, start, end):
    params = {
        "latitude": lat, "longitude": lon,
        "start_date": start, "end_date": end,
        "hourly": ",".join(HOURLY),
        "timezone": "UTC",
        "wind_speed_unit": "ms",
    }
    for attempt in range(MAX_RETRIES):
        r = requests.get(ARCHIVE, params=params, timeout=120)
        if r.status_code == 429:
            wait = int(r.headers.get("Retry-After", 0)) or min(15 * 2 ** attempt, 120)
            print(f"  rate limited (429), waiting {wait}s...", flush=True)
            time.sleep(wait)
            continue
        r.raise_for_status()
        return pd.DataFrame(r.json()["hourly"])
    raise SystemExit("Still rate limited after retries. Re-run later; finished "
                     "cities are skipped, so it resumes where it stopped.")


def _iso_offset(series):
    """Format a tz-aware datetime Series as ISO 8601 with a colon in the offset
    (e.g. 2018-07-01T02:00:00+02:00), which %z alone does not give."""
    s = series.dt.strftime("%Y-%m-%dT%H:%M:%S%z")
    return s.str.replace(r"([+-]\d{2})(\d{2})$", r"\1:\2", regex=True)


def add_columns(df, tz, city=None, country=None, country_code=None):
    """Prepend row-level identifiers and write the two time columns.

    Identifiers (city, country, country_code, tz) make the per-city files
    loadable into one Postgres table. Both time columns are unambiguous ISO 8601:
    time_utc with a trailing Z (load into timestamptz), time_local with the city's
    real DST-aware UTC offset, so the duplicated autumn fall-back hour stays
    distinguishable (load into timestamp without time zone). time_local is left
    blank when the zone is unknown, i.e. for raw --lat/--lon input.
    """
    df = df.rename(columns={"time": "time_utc"})
    utc = pd.to_datetime(df["time_utc"], utc=True)
    df["time_utc"] = utc.dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    df["time_local"] = _iso_offset(utc.dt.tz_convert(tz)) if tz else pd.NA
    df["city"] = city
    df["country"] = country
    df["country_code"] = country_code  # ISO 3166-1 alpha-2, e.g. FR
    df["tz"] = tz
    lead = ["city", "country", "country_code", "tz", "time_utc", "time_local"]
    return df[lead + [c for c in df.columns if c not in lead]]


def end_default(end):
    return end or (dt.date.today() - dt.timedelta(days=6)).isoformat()


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--location", help='Place name, e.g. "London"')
    p.add_argument("--lat", type=float, help="Latitude")
    p.add_argument("--lon", type=float, help="Longitude")
    p.add_argument("--start", default="2018-01-01")
    p.add_argument("--end", default=None, help="Default: today minus 6 days (ERA5 lag)")
    p.add_argument("--out", default="weather.csv")
    p.add_argument("--all-capitals", action="store_true",
                   help="Loop the EU-27 capitals, one CSV per city into --out-dir")
    p.add_argument("--out-dir", default="out", help="Output dir for --all-capitals")
    args = p.parse_args()

    end = end_default(args.end)

    if args.all_capitals:
        os.makedirs(args.out_dir, exist_ok=True)
        for name in CAPITALS:
            lat, lon, tz, country, code = geocode(name)
            path = os.path.join(args.out_dir, f"{country.replace(' ', '')}_{name}.csv")
            if os.path.exists(path):
                print(f"{name}: already present, skipping", flush=True)
                continue
            df = add_columns(fetch(lat, lon, args.start, end), tz, name, country, code)
            df.to_csv(path, index=False)
            print(f"{name} ({country}, {tz}): {len(df)} rows -> {path}", flush=True)
        return

    if args.lat is not None and args.lon is not None:
        lat, lon, tz, city, country, code = args.lat, args.lon, None, None, None, None
    elif args.location:
        lat, lon, tz, country, code = geocode(args.location)
        city = args.location
    else:
        raise SystemExit("Provide --location, --lat/--lon, or --all-capitals.")

    df = add_columns(fetch(lat, lon, args.start, end), tz, city, country, code)
    df.to_csv(args.out, index=False)
    print(f"Saved {len(df)} rows ({args.start} to {end}) to {args.out}")


if __name__ == "__main__":
    main()
