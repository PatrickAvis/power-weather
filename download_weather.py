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
import requests
import pandas as pd

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

# EU-27 capitals, one city per member state. Edit as you like. The timezone for
# each is taken from the geocoder, so no hand-maintained zone map is needed.
CAPITALS = [
    "Vienna", "Brussels", "Sofia", "Zagreb", "Nicosia", "Prague",
    "Copenhagen", "Tallinn", "Helsinki", "Paris", "Berlin", "Athens",
    "Budapest", "Dublin", "Rome", "Riga", "Vilnius", "Luxembourg",
    "Valletta", "Amsterdam", "Warsaw", "Lisbon", "Bucharest",
    "Bratislava", "Ljubljana", "Madrid", "Stockholm",
]


def geocode(name):
    r = requests.get(GEOCODE, params={"name": name, "count": 1}, timeout=30)
    r.raise_for_status()
    hits = r.json().get("results")
    if not hits:
        raise SystemExit(f"No match for '{name}'. Use --lat/--lon instead.")
    h = hits[0]
    return h["latitude"], h["longitude"], h.get("timezone"), h.get("country")


def fetch(lat, lon, start, end):
    r = requests.get(ARCHIVE, params={
        "latitude": lat, "longitude": lon,
        "start_date": start, "end_date": end,
        "hourly": ",".join(HOURLY),
        "timezone": "UTC",
        "wind_speed_unit": "ms",
    }, timeout=120)
    r.raise_for_status()
    return pd.DataFrame(r.json()["hourly"])


def _iso_offset(series):
    """Format a tz-aware datetime Series as ISO 8601 with a colon in the offset
    (e.g. 2018-07-01T02:00:00+02:00), which %z alone does not give."""
    s = series.dt.strftime("%Y-%m-%dT%H:%M:%S%z")
    return s.str.replace(r"([+-]\d{2})(\d{2})$", r"\1:\2", regex=True)


def add_time_columns(df, tz):
    """Rename the UTC time column and add a local wall-clock column.

    Both columns are written as unambiguous ISO 8601: time_utc with a trailing Z,
    time_local with the city's real (DST-aware) UTC offset, so the duplicated
    autumn fall-back hour stays distinguishable. time_local is left blank when the
    zone is unknown, i.e. for raw --lat/--lon input.
    """
    df = df.rename(columns={"time": "time_utc"})
    utc = pd.to_datetime(df["time_utc"], utc=True)
    df["time_utc"] = utc.dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    df["time_local"] = _iso_offset(utc.dt.tz_convert(tz)) if tz else pd.NA
    lead = ["time_utc", "time_local"]
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
            lat, lon, tz, country = geocode(name)
            df = add_time_columns(fetch(lat, lon, args.start, end), tz)
            path = os.path.join(args.out_dir, f"{name}.csv")
            df.to_csv(path, index=False)
            print(f"{name} ({country}, {tz}): {len(df)} rows -> {path}")
        return

    if args.lat is not None and args.lon is not None:
        lat, lon, tz = args.lat, args.lon, None
    elif args.location:
        lat, lon, tz, _ = geocode(args.location)
    else:
        raise SystemExit("Provide --location, --lat/--lon, or --all-capitals.")

    df = add_time_columns(fetch(lat, lon, args.start, end), tz)
    df.to_csv(args.out, index=False)
    print(f"Saved {len(df)} rows ({args.start} to {end}) to {args.out}")


if __name__ == "__main__":
    main()
