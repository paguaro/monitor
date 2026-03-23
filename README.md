# 🌬 Meteo Skill Monitor

Automated weekly quality control of Open-Meteo wind forecasts for **8 stations in Portugal and Sardegna**, with computation of the **α anemological stability index**.

## What it does

Every **Monday at 06:00 UTC**, a GitHub Actions workflow automatically:

1. Downloads 32 days of wind/humidity data from Open-Meteo (±16 days)
2. Compares last week's **IFS forecast** against this week's **ERA5-NRT observed** data
3. Computes **skill metrics**: RMSE, Bias, MAE direction, Regime hit rate
4. Computes **α stability index** (observed vs forecast vs climatological)
5. Generates an HTML report published via GitHub Pages
6. Commits all results to the repository

## Stations

| ID | Name | Country | Terrain |
|---|---|---|---|
| braganca | Bragança | PT | Plateau interior |
| coimbra | Coimbra | PT | Valley |
| castelo_branco | Castelo Branco | PT | Open valley |
| evora | Évora | PT | Open plain |
| faro | Faro | PT | Coastal |
| cagliari | Cagliari | IT | Coastal |
| nuoro | Nuoro | IT | Highland interior |
| sassari | Sassari | IT | Plateau coastal |

## The α index

α measures **anemological stability** — how predictable and single-regime the wind is:

| α range | Classification | Typical context |
|---|---|---|
| ≥ 0.55 | Stable | Anticyclonic, single dominant regime |
| 0.38–0.55 | Moderate | Regime transitions, coastal breezes |
| < 0.38 | Variable | Frontal activity, multi-regime chaos |

Formula:
```
α = 0.40 × (dominant regime fraction / 0.80)
  + 0.35 × (mean run length / 24h)
  + 0.25 × (1 − changes per day / 4)
```

## Output files

| File | Description |
|---|---|
| `data/skill/skill_cumulative.csv` | Weekly RMSE/Bias/MAE per station, all weeks |
| `data/skill/alpha_weekly.csv` | Weekly α (obs, fct, cli, residual) per station |
| `data/forecasts/YYYY-MM-DD/` | Raw JSON per station per week |
| `reports/index.html` | HTML dashboard (GitHub Pages) |

## View the report

👉 **[Live report](https://YOUR_USERNAME.github.io/meteo-skill-monitor/reports/)**

*(Replace YOUR_USERNAME with your GitHub username after enabling GitHub Pages)*

## Run manually

Go to **Actions** tab → **Weekly Meteo Skill Analysis** → **Run workflow**

## Local development

```bash
git clone https://github.com/YOUR_USERNAME/meteo-skill-monitor
cd meteo-skill-monitor
pip install requests numpy
python scripts/fetch_data.py
python scripts/compute_skill.py
python scripts/compute_alpha.py
python scripts/generate_report.py
open reports/index.html
```

## Data source

[Open-Meteo](https://open-meteo.com/) — free, no API key required.
- **Observed**: ERA5-NRT reanalysis (5–7 day latency)
- **Forecast**: ECMWF IFS (16-day horizon)

> Note: This monitors model-vs-reanalysis consistency, not model-vs-real-station accuracy.
> For true ground truth, integrate SYNOP station data (NOAA ISD, SNIRH, SIARL).

## License

MIT
