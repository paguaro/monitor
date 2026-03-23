"""
compute_alpha.py
----------------
Computes the α stability index for each station from both observed and
forecast wind direction data. Appends results to alpha_weekly.csv.

α formula (empirically calibrated on PT/IT/AU/CL dataset):
  α = 0.40 × dominant_regime_fraction
    + 0.35 × mean_run_length_normalised
    + 0.25 × (1 − changes_per_day / 4)

Range: 0 (chaotic, all regimes equal, high change rate)
       1 (one regime, long runs, no changes)
"""

import json
import csv
import os
import calendar
from datetime import datetime, timezone, timedelta
from pathlib import Path


# ── Wind regime ───────────────────────────────────────────────────────────────

def wind_regime(deg):
    if deg is None:
        return None
    d = float(deg) % 360
    if d >= 315 or d < 45:  return "N/NW"
    if 45  <= d < 135:       return "NE/E"
    if 135 <= d < 225:       return "S/SE"
    return "W/SW"


# ── Alpha computation ─────────────────────────────────────────────────────────

def compute_alpha(times: list, wind_dirs: list) -> dict | None:
    """
    Returns α value plus component metrics, or None if insufficient data.
    """
    if not times or len(times) < 12:
        return None

    regimes = [wind_regime(d) for d in wind_dirs]
    valid   = [r for r in regimes if r is not None]
    if len(valid) < 6:
        return None

    # 1. Dominant regime fraction
    counts = {}
    for r in valid:
        counts[r] = counts.get(r, 0) + 1
    total    = len(valid)
    dom_reg  = max(counts, key=counts.get)
    dom_frac = counts[dom_reg] / total

    # 2. Mean run length (hours of consecutive same regime)
    runs, cur = [], 1
    for i in range(1, len(regimes)):
        if regimes[i] is None:
            continue
        if regimes[i] == regimes[i - 1]:
            cur += 1
        else:
            runs.append(cur)
            cur = 1
    runs.append(cur)
    avg_run = sum(runs) / len(runs) if runs else 1.0
    max_run = max(runs)

    # 3. Direction changes per day
    n_days = len(times) / 24.0
    changes = sum(
        1 for i in range(1, len(regimes))
        if regimes[i] and regimes[i - 1] and regimes[i] != regimes[i - 1]
    )
    changes_per_day = changes / n_days if n_days > 0 else 0

    # Normalise each component
    dom_norm     = min(dom_frac / 0.80, 1.0)
    persist_norm = min(avg_run / 24.0,  1.0)
    change_norm  = max(0.0, 1.0 - changes_per_day / 4.0)

    alpha = (0.40 * dom_norm) + (0.35 * persist_norm) + (0.25 * change_norm)

    return {
        "alpha":            round(alpha, 3),
        "dominant_regime":  dom_reg,
        "dominant_pct":     round(dom_frac * 100, 1),
        "avg_run_h":        round(avg_run, 1),
        "max_run_h":        max_run,
        "changes_per_day":  round(changes_per_day, 2),
        "n_hours":          len(times),
    }


# ── Weekly run ────────────────────────────────────────────────────────────────

ALPHA_FIELDS = [
    "week", "station_id", "station_name", "country",
    "alpha_obs", "alpha_fct", "alpha_error",
    "dom_regime_obs", "dom_regime_fct",
    "dom_pct_obs", "dom_pct_fct",
    "avg_run_obs", "avg_run_fct",
    "max_run_obs", "max_run_fct",
    "changes_day_obs", "changes_day_fct",
    "n_hours_obs", "n_hours_fct",
    "alpha_cli",       # climatological reference from stations.json
    "alpha_residual",  # alpha_obs - alpha_cli (model vs climatology)
]


def run_weekly(
    data_dir: str = "data/forecasts",
    output:   str = "data/skill/alpha_weekly.csv",
) -> None:
    today    = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    today_dir = Path(data_dir) / today

    if not today_dir.exists():
        print(f"  No data for {today} — run fetch_data.py first")
        return

    # Get current month for alpha_cli lookup
    month = datetime.now(timezone.utc).strftime("%b").lower()  # e.g. "mar"
    cli_key = f"alpha_cli_{month}"

    Path(output).parent.mkdir(parents=True, exist_ok=True)
    rows = []

    for f in sorted(today_dir.glob("*.json")):
        with open(f) as fh:
            d = json.load(fh)

        st  = d["station"]
        obs = d["observed"]
        fct = d["forecast"]

        a_obs = compute_alpha(obs["time"], obs["winddirection_10m"])
        a_fct = compute_alpha(fct["time"], fct["winddirection_10m"])

        # Climatological alpha from config (may not exist for current month)
        alpha_cli = st.get(cli_key) or st.get("alpha_cli_mar")  # fallback to march

        alpha_obs_val = a_obs["alpha"] if a_obs else None
        alpha_fct_val = a_fct["alpha"] if a_fct else None

        row = {
            "week":             today,
            "station_id":       st["id"],
            "station_name":     st["name"],
            "country":          st["country"],
            "alpha_obs":        alpha_obs_val,
            "alpha_fct":        alpha_fct_val,
            "alpha_error":      round(alpha_fct_val - alpha_obs_val, 3)
                                if alpha_obs_val and alpha_fct_val else None,
            "dom_regime_obs":   a_obs["dominant_regime"]  if a_obs else None,
            "dom_regime_fct":   a_fct["dominant_regime"]  if a_fct else None,
            "dom_pct_obs":      a_obs["dominant_pct"]     if a_obs else None,
            "dom_pct_fct":      a_fct["dominant_pct"]     if a_fct else None,
            "avg_run_obs":      a_obs["avg_run_h"]         if a_obs else None,
            "avg_run_fct":      a_fct["avg_run_h"]         if a_fct else None,
            "max_run_obs":      a_obs["max_run_h"]         if a_obs else None,
            "max_run_fct":      a_fct["max_run_h"]         if a_fct else None,
            "changes_day_obs":  a_obs["changes_per_day"]   if a_obs else None,
            "changes_day_fct":  a_fct["changes_per_day"]   if a_fct else None,
            "n_hours_obs":      a_obs["n_hours"]            if a_obs else None,
            "n_hours_fct":      a_fct["n_hours"]            if a_fct else None,
            "alpha_cli":        alpha_cli,
            "alpha_residual":   round(alpha_obs_val - alpha_cli, 3)
                                if alpha_obs_val and alpha_cli else None,
        }
        rows.append(row)

        print(f"  ✓ {st['name']:20s}  "
              f"α_obs={alpha_obs_val}  "
              f"α_fct={alpha_fct_val}  "
              f"α_cli={alpha_cli}  "
              f"dom={row['dom_regime_obs']}")

    if not rows:
        print("  No rows computed")
        return

    file_exists = os.path.exists(output)
    with open(output, "a", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=ALPHA_FIELDS)
        if not file_exists:
            writer.writeheader()
        writer.writerows(rows)

    print(f"\n  Alpha saved → {output}  ({len(rows)} rows)")


if __name__ == "__main__":
    run_weekly()
