"""
Download raw hourly historical weather from the Open-Meteo archive API (ERA5).
No API key. Data is CC BY 4.0 (attribute Open-Meteo / ERA5).

Examples:
    python download_weather.py --location "London"
    python download_weather.py --location "Paris" --start 2018-01-01 --end 2025-12-31
    python download_weather.py --lat 51.5 --lon -0.1 --out london.csv
"""

import argparse
import datetime as dt
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


def geocode(name):
    r = requests.get(GEOCODE, params={"name": name, "count": 1}, timeout=30)
    r.raise_for_status()
    hits = r.json().get("results")
    if not hits:
        raise SystemExit(f"No match for '{name}'. Use --lat/--lon instead.")
    h = hits[0]
    return h["latitude"], h["longitude"]


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--location", help='Place name, e.g. "London"')
    p.add_argument("--lat", type=float, help="Latitude")
    p.add_argument("--lon", type=float, help="Longitude")
    p.add_argument("--start", default="2018-01-01")
    p.add_argument("--end", default=None, help="Default: today minus 6 days (ERA5 lag)")
    p.add_argument("--out", default="weather.csv")
    args = p.parse_args()

    if args.lat is not None and args.lon is not None:
        lat, lon = args.lat, args.lon
    elif args.location:
        lat, lon = geocode(args.location)
    else:
        raise SystemExit("Provide --location or --lat/--lon.")

    end = args.end or (dt.date.today() - dt.timedelta(days=6)).isoformat()

    r = requests.get(ARCHIVE, params={
        "latitude": lat, "longitude": lon,
        "start_date": args.start, "end_date": end,
        "hourly": ",".join(HOURLY),
        "timezone": "UTC",
        "wind_speed_unit": "ms",
    }, timeout=120)
    r.raise_for_status()

    df = pd.DataFrame(r.json()["hourly"])
    df.to_csv(args.out, index=False)
    print(f"Saved {len(df)} rows ({args.start} to {end}) to {args.out}")


if __name__ == "__main__":
    main()
