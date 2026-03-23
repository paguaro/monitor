"""
compute_skill.py
----------------
Compares last week's Open-Meteo forecast against this week's observed data
(ERA5-NRT assimilated) and appends skill metrics to a cumulative CSV.

Metrics computed per station per week:
  - BIAS, RMSE, MAE for wind speed, gust, temperature, RH
  - MAE circular for wind direction
  - Regime hit rate (correct quadrant forecast)
  - Number of matched pairs
"""

import json
import csv
import os
import math
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np


# ── Wind regime classification (4 quadrants) ─────────────────────────────────

def wind_regime(deg):
    if deg is None:
        return None
    d = float(deg) % 360
    if d >= 315 or d < 45:   return "N/NW"
    if 45  <= d < 135:        return "NE/E"
    if 135 <= d < 225:        return "S/SE"
    return "W/SW"


def angular_diff(a, b):
    """Minimum circular difference between two bearings (0–180°)."""
    d = abs(float(a) - float(b)) % 360
    return min(d, 360 - d)


# ── Skill computation ─────────────────────────────────────────────────────────

def compute_skill(obs: dict, fct: dict) -> dict:
    """
    Match timestamps between obs and fct dicts, compute skill metrics.
    Both dicts must have a 'time' key (ISO strings) plus variable arrays.
    """
    obs_index = {t: i for i, t in enumerate(obs["time"])}

    pairs = {k: [] for k in ["ws", "wg", "wd", "t", "rh"]}
    regime_hits = 0
    regime_total = 0

    field_map = {
        "ws": ("windspeed_10m",      "windspeed_10m"),
        "wg": ("windgusts_10m",      "windgusts_10m"),
        "wd": ("winddirection_10m",  "winddirection_10m"),
        "t":  ("temperature_2m",     "temperature_2m"),
        "rh": ("relativehumidity_2m","relativehumidity_2m"),
    }

    for i, t in enumerate(fct["time"]):
        if t not in obs_index:
            continue
        j = obs_index[t]

        for key, (fo, ff) in field_map.items():
            ov = obs.get(fo, [])[j] if j < len(obs.get(fo, [])) else None
            fv = fct.get(ff, [])[i] if i < len(fct.get(ff, [])) else None
            if ov is not None and fv is not None:
                pairs[key].append((float(ov), float(fv)))

        wd_o = obs.get("winddirection_10m", [])[j] if j < len(obs.get("winddirection_10m", [])) else None
        wd_f = fct.get("winddirection_10m", [])[i] if i < len(fct.get("winddirection_10m", [])) else None
        if wd_o is not None and wd_f is not None:
            regime_total += 1
            if wind_regime(wd_o) == wind_regime(wd_f):
                regime_hits += 1

    def scalar_stats(p):
        if not p:
            return {"bias": None, "rmse": None, "mae": None}
        obs_a = np.array([x[0] for x in p])
        fct_a = np.array([x[1] for x in p])
        diff  = fct_a - obs_a
        return {
            "bias": round(float(np.mean(diff)), 3),
            "rmse": round(float(np.sqrt(np.mean(diff ** 2))), 3),
            "mae":  round(float(np.mean(np.abs(diff))), 3),
        }

    def circular_stats(p):
        if not p:
            return {"bias": None, "rmse": None, "mae": None}
        diffs = [angular_diff(f, o) for o, f in p]
        return {
            "bias": None,
            "rmse": round(float(np.sqrt(np.mean(np.array(diffs) ** 2))), 2),
            "mae":  round(float(np.mean(diffs)), 2),
        }

    return {
        "ws":  scalar_stats(pairs["ws"]),
        "wg":  scalar_stats(pairs["wg"]),
        "wd":  circular_stats(pairs["wd"]),
        "t":   scalar_stats(pairs["t"]),
        "rh":  scalar_stats(pairs["rh"]),
        "regime_hit_rate": round(regime_hits / regime_total, 3) if regime_total else None,
        "n_pairs": len(pairs["ws"]),
    }


# ── Weekly run ────────────────────────────────────────────────────────────────

SKILL_FIELDS = [
    "week", "station_id", "station_name", "country",
    "n_pairs",
    "bias_ws",  "rmse_ws",  "mae_ws",
    "bias_wg",  "rmse_wg",  "mae_wg",
    "rmse_wd",  "mae_wd",
    "bias_t",   "rmse_t",
    "bias_rh",  "rmse_rh",
    "regime_hit_rate",
]


def run_weekly(
    data_dir: str = "data/forecasts",
    output:   str = "data/skill/skill_cumulative.csv",
) -> None:
    today     = datetime.now(timezone.utc)
    last_week = (today - timedelta(days=7)).strftime("%Y-%m-%d")
    this_week = today.strftime("%Y-%m-%d")

    last_dir = Path(data_dir) / last_week
    this_dir = Path(data_dir) / this_week

    if not last_dir.exists():
        print(f"  No forecast data for {last_week} — skipping skill (first run?)")
        return

    if not this_dir.exists():
        print(f"  No observed data for {this_week} — run fetch_data.py first")
        return

    Path(output).parent.mkdir(parents=True, exist_ok=True)
    rows = []

    for fct_file in sorted(last_dir.glob("*.json")):
        sid      = fct_file.stem
        obs_file = this_dir / fct_file.name

        if not obs_file.exists():
            print(f"  ⚠ No observed file for {sid} — skipping")
            continue

        with open(fct_file)  as f: fct_all = json.load(f)
        with open(obs_file)  as f: obs_all = json.load(f)

        # Forecast from last week vs observed this week (now assimilated)
        skill = compute_skill(obs_all["observed"], fct_all["forecast"])

        row = {
            "week":             this_week,
            "station_id":       sid,
            "station_name":     fct_all["station"]["name"],
            "country":          fct_all["station"]["country"],
            "n_pairs":          skill["n_pairs"],
            "bias_ws":          skill["ws"]["bias"],
            "rmse_ws":          skill["ws"]["rmse"],
            "mae_ws":           skill["ws"]["mae"],
            "bias_wg":          skill["wg"]["bias"],
            "rmse_wg":          skill["wg"]["rmse"],
            "mae_wg":           skill["wg"]["mae"],
            "rmse_wd":          skill["wd"]["rmse"],
            "mae_wd":           skill["wd"]["mae"],
            "bias_t":           skill["t"]["bias"],
            "rmse_t":           skill["t"]["rmse"],
            "bias_rh":          skill["rh"]["bias"],
            "rmse_rh":          skill["rh"]["rmse"],
            "regime_hit_rate":  skill["regime_hit_rate"],
        }
        rows.append(row)

        hr  = skill["regime_hit_rate"]
        print(f"  ✓ {sid:20s}  RMSE_ws={row['rmse_ws']}  MAE_wd={row['mae_wd']}°  "
              f"RegimeHR={hr:.0%}" if hr else f"  ✓ {sid}")

    if not rows:
        print("  No rows computed — nothing to save")
        return

    file_exists = os.path.exists(output)
    with open(output, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=SKILL_FIELDS)
        if not file_exists:
            writer.writeheader()
        writer.writerows(rows)

    print(f"\n  Skill saved → {output}  ({len(rows)} rows)")


if __name__ == "__main__":
    run_weekly()
