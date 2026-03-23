# 🌬 WildWinds

**Wind & Humidity Analysis Dashboard**  
Open-Meteo · ±16 days observed + forecast · Portugal · Sardegna · California

---

## What it is

WildWinds is a single-file operational meteorological dashboard for wind and humidity analysis, designed for fire weather surveillance and anemological research.

It runs entirely in the browser — no server, no installation, no API key.

**[→ Open Dashboard](https://paguaro.github.io/wildwinds/)**

---

## Features

### Wind Analysis
- **Time-series** wind speed, gust, Δ (gust−wind) — observed + forecast
- **Wind barbs** synchronized with timeline — dot color = temperature, dot size = gust intensity
- **Wind Rose** — Δ frequency + HDW/mode rose with stats panel
- **Wind Clock** — 24h × 16 sector heatmap
- **Regime Persistence** — hours per regime by run duration + start-hour distribution
- **Direction Switch Analysis** — abrupt direction changes by hour
- **Scatter** wind vs VPD / RH

### Humidity & Soil
- RH, VPD, precipitation time series
- Soil moisture — 4 layers (0–1, 1–3, 3–9, 9–27 cm)

### Station Intelligence
- **Summary card** — HDW mean/max, max gust, RH, soil, dominant sector, records
- **Station trends** — α stability index + RH trend bars per station, updated with slider
- **Comparison table** — all stations side by side, sortable, CSV export

### Multi-station
- Up to ~15 simultaneous stations — click map or ± button to add
- Load stations from `stations.json` (compatible with [monitor](https://github.com/paguaro/monitor) repo)
- Station markers colored by HDW, sized by selection — show max gust in label

### UX
- **32-day slider** — dual-thumb, presets 1d/3d/7d/16d/All, today marker
- **Obs / FCT / Both** mode toggle
- **Fullscreen** for every chart — barbs preserved in FS wind charts
- All tables collapsible ▲, sortable, CSV export
- PDF A4 export

---

## Default stations

| Station | Country | Wind system |
|---|---|---|
| Bragança | PT | NE continental |
| Castelo Branco | PT | Valley interior |
| Évora | PT | Open plain |
| Faro | PT | Coastal Algarve |
| Cagliari | IT | Sardegna South |
| Nuoro | IT | Maestrale interior |
| Sassari | IT | Maestrale north |
| Cajon Pass | US | Santa Ana |
| Livermore — Altamont Pass | US | Diablo |
| Santa Barbara — Refugio | US | Sundowner |

---

## Load custom stations

Click **📂 Stations** in the header to load any `stations.json` file.

Compatible format:
```json
{
  "stations": [
    { "id": "mystation", "name": "My Station", "lat": 40.0, "lon": -8.0, "region": "Region", "country": "PT" }
  ]
}
```

---

## The α stability index

α measures anemological predictability — how stable and single-regime the wind is in the selected period:

| α | Classification | Meaning |
|---|---|---|
| ≥ 0.55 | Stable | One regime dominates, long runs, few changes |
| 0.38–0.55 | Moderate | Regime transitions, coastal breezes |
| < 0.38 | Variable | Frontal activity, multiple regimes, chaotic |

---

## Data source

[Open-Meteo](https://open-meteo.com/) — free, no API key required.

- **Observed** (past 16 days): ERA5-NRT reanalysis
- **Forecast** (next 16 days): ECMWF IFS

---

## Related

**[monitor](https://github.com/paguaro/monitor)** — automated weekly quality control of Open-Meteo forecasts for the same stations, with skill metrics (RMSE, Bias, MAE) and α index tracking.

---

## License

MIT
