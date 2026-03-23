"""
fetch_data.py
-------------
Downloads 32-day wind/humidity/soil data from Open-Meteo for all stations.
Splits into observed (past) and forecast (future) slices and saves as JSON.

Run manually:  python scripts/fetch_data.py
Run in CI:     called by weekly_analysis.yml every Monday 06:00 UTC
"""

import requests
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

# ── Configuration ────────────────────────────────────────────────────────────

BASE_URL = "https://api.open-meteo.com/v1/forecast"

VARIABLES = [
    "windspeed_10m",
    "windgusts_10m",
    "winddirection_10m",
    "temperature_2m",
    "relativehumidity_2m",
    "precipitation",
    "soil_moisture_0_to_1cm",
    "soil_moisture_1_to_3cm",
]

PAST_DAYS     = 16
FORECAST_DAYS = 16

# ── Helpers ──────────────────────────────────────────────────────────────────

def fetch_station(station: dict, retries: int = 3) -> dict:
    """Call Open-Meteo API for one station with retry logic."""
    params = {
        "latitude":        station["lat"],
        "longitude":       station["lon"],
        "hourly":          ",".join(VARIABLES),
        "wind_speed_unit": "kmh",
        "past_days":       PAST_DAYS,
        "forecast_days":   FORECAST_DAYS,
        "timezone":        "auto",
    }
    for attempt in range(retries):
        try:
            r = requests.get(BASE_URL, params=params, timeout=30)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            print(f"    Attempt {attempt + 1} failed: {e}")
            if attempt < retries - 1:
                time.sleep(5)
    raise RuntimeError(f"Failed to fetch {station['name']} after {retries} attempts")


def split_obs_fct(hourly: dict) -> tuple[dict, dict]:
    """Split hourly dict into observed (past) and forecast (future) slices."""
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H")
    obs_idx = [i for i, t in enumerate(hourly["time"]) if t[:13] <= now_str]
    fct_idx = [i for i, t in enumerate(hourly["time"]) if t[:13] >  now_str]

    def _slice(idxs: list) -> dict:
        return {k: [v[i] for i in idxs] for k, v in hourly.items()}

    return _slice(obs_idx), _slice(fct_idx)


# ── Main ─────────────────────────────────────────────────────────────────────

def fetch_all(stations_path: str = "config/stations.json") -> None:
    with open(stations_path) as f:
        cfg = json.load(f)

    today    = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_dir  = Path("data/forecasts") / today
    out_dir.mkdir(parents=True, exist_ok=True)

    success, failed = 0, []

    for st in cfg["stations"]:
        print(f"  ↓ {st['name']} ({st['country']}) ...")
        try:
            raw           = fetch_station(st)
            hourly        = raw["hourly"]
            obs, fct      = split_obs_fct(hourly)

            payload = {
                "station":  st,
                "fetched":  today,
                "timezone": raw.get("timezone", "UTC"),
                "observed": obs,   # ERA5-NRT — past 16 days
                "forecast": fct,   # IFS forecast — next 16 days
            }

            out_file = out_dir / f"{st['id']}.json"
            with open(out_file, "w") as f:
                json.dump(payload, f, indent=2)

            print(f"    ✓ {len(obs['time'])} obs + {len(fct['time'])} fct hours saved")
            success += 1
            time.sleep(0.5)   # be polite to the API

        except Exception as e:
            print(f"    ✗ ERROR: {e}")
            failed.append(st["name"])

    print(f"\n  Done: {success} OK, {len(failed)} failed")
    if failed:
        print(f"  Failed stations: {', '.join(failed)}")
        raise SystemExit(1)


if __name__ == "__main__":
    fetch_all()
