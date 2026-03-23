"""
generate_report.py
------------------
Reads skill_cumulative.csv and alpha_weekly.csv and generates
a static HTML dashboard saved to reports/index.html.

The report shows:
  - Current week skill metrics table (colour-coded)
  - Alpha trend chart (last 8 weeks, per station)
  - Summary interpretation panel
"""

import csv
import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


# ── Colour helpers ────────────────────────────────────────────────────────────

def rmse_color(val, thresholds=(2.0, 4.0)):
    """Green / amber / red for RMSE-like metrics."""
    try:
        v = float(val)
        if v < thresholds[0]: return "#15803d"
        if v < thresholds[1]: return "#d97706"
        return "#dc2626"
    except:
        return "#9ca3af"

def bias_color(val, neutral=0.5):
    """Blue for negative bias, red for positive, grey near zero."""
    try:
        v = float(val)
        if abs(v) < neutral: return "#6b7280"
        return "#dc2626" if v > 0 else "#1d4ed8"
    except:
        return "#9ca3af"

def hr_color(val):
    """Hit-rate: green > 0.70, amber 0.55–0.70, red < 0.55."""
    try:
        v = float(val)
        if v >= 0.70: return "#15803d"
        if v >= 0.55: return "#d97706"
        return "#dc2626"
    except:
        return "#9ca3af"

def alpha_badge(val):
    """Classify alpha value."""
    try:
        v = float(val)
        if v >= 0.55: return "Stable",   "#15803d", "#dcfce7"
        if v >= 0.38: return "Moderate", "#d97706", "#fef3c7"
        return             "Variable",  "#dc2626", "#fee2e2"
    except:
        return "—", "#9ca3af", "#f3f4f6"


def fmt(val, dec=2, suffix=""):
    try:
        return f"{float(val):.{dec}f}{suffix}"
    except:
        return "—"


# ── Load data ─────────────────────────────────────────────────────────────────

def load_csv(path):
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return list(csv.DictReader(f))


# ── Chart data ────────────────────────────────────────────────────────────────

def build_alpha_chart_data(alpha_rows, n_weeks=8):
    """Build a simple SVG sparkline dataset from alpha_weekly."""
    by_station = defaultdict(list)
    for r in alpha_rows:
        by_station[r["station_name"]].append(r)
    # Sort each station's history by week
    for sid in by_station:
        by_station[sid].sort(key=lambda x: x["week"])
        by_station[sid] = by_station[sid][-n_weeks:]
    return dict(by_station)


STATION_COLORS = [
    "#e85d2f","#1d4ed8","#15803d","#7c3aed",
    "#0891b2","#d97706","#dc2626","#374151",
]


def sparkline_svg(values, color, width=120, height=30):
    """Tiny SVG sparkline for alpha trend."""
    clean = []
    for v in values:
        try:    clean.append(float(v))
        except: clean.append(None)

    valid = [v for v in clean if v is not None]
    if len(valid) < 2:
        return "<span style='color:#9ca3af;font-size:10px'>insufficient data</span>"

    mn, mx = min(valid), max(valid)
    rng    = mx - mn if mx != mn else 0.1
    pad    = 3

    def px(i, v):
        x = pad + (i / (len(clean) - 1)) * (width - 2 * pad)
        y = pad + (1 - (v - mn) / rng) * (height - 2 * pad)
        return x, y

    points = []
    for i, v in enumerate(clean):
        if v is not None:
            points.append(px(i, v))

    path = " ".join(
        f"{'M' if i == 0 else 'L'}{x:.1f},{y:.1f}"
        for i, (x, y) in enumerate(points)
    )

    last_x, last_y = points[-1]

    return (
        f'<svg width="{width}" height="{height}" style="vertical-align:middle">'
        f'<path d="{path}" fill="none" stroke="{color}" stroke-width="1.8" '
        f'stroke-linejoin="round"/>'
        f'<circle cx="{last_x:.1f}" cy="{last_y:.1f}" r="3" fill="{color}"/>'
        f'</svg>'
    )


# ── HTML generation ───────────────────────────────────────────────────────────

def generate(
    skill_csv: str = "data/skill/skill_cumulative.csv",
    alpha_csv: str = "data/skill/alpha_weekly.csv",
    out:       str = "reports/index.html",
) -> None:

    skill_all = load_csv(skill_csv)
    alpha_all = load_csv(alpha_csv)

    # Latest week
    last_skill_week = max((r["week"] for r in skill_all), default="—")
    last_alpha_week = max((r["week"] for r in alpha_all), default="—")

    skill_last  = [r for r in skill_all  if r["week"] == last_skill_week]
    alpha_last  = {r["station_id"]: r for r in alpha_all
                   if r["week"] == last_alpha_week}
    alpha_chart = build_alpha_chart_data(alpha_all)

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # ── Skill table rows ──────────────────────────────────────────────────────
    skill_rows_html = ""
    for r in skill_last:
        sid  = r["station_id"]
        al   = alpha_last.get(sid, {})
        lbl, fg, bg = alpha_badge(al.get("alpha_obs"))

        skill_rows_html += f"""
        <tr>
          <td><b>{r['station_name']}</b></td>
          <td style="color:#9ca3af">{r['country']}</td>
          <td style="color:{rmse_color(r['rmse_ws'])};font-weight:700">{fmt(r['rmse_ws'])}</td>
          <td style="color:{bias_color(r['bias_ws'])}">{fmt(r['bias_ws'],1)}</td>
          <td style="color:{rmse_color(r['rmse_wg'],thresholds=(3,6))};font-weight:700">{fmt(r['rmse_wg'])}</td>
          <td style="color:{rmse_color(r.get('mae_wd',''),thresholds=(20,35))}">{fmt(r.get('mae_wd',''),0)}°</td>
          <td style="color:{hr_color(r['regime_hit_rate'])};font-weight:700">
            {fmt(float(r['regime_hit_rate'])*100 if r['regime_hit_rate'] else None,0,'%')}
          </td>
          <td>
            <span style="background:{bg};color:{fg};padding:2px 7px;border-radius:8px;
                         font-size:9px;font-weight:700;font-family:monospace">
              {fmt(al.get('alpha_obs',''))} {lbl}
            </span>
          </td>
          <td style="color:#6b7280;font-size:11px">{fmt(al.get('alpha_fct',''))}</td>
          <td style="color:{bias_color(al.get('alpha_error',''),neutral=0.03)}">{fmt(al.get('alpha_error',''),3)}</td>
          <td style="color:#9ca3af;font-size:11px">{al.get('dom_regime_obs','—')}</td>
          <td style="color:#9ca3af;font-size:11px">{fmt(al.get('avg_run_obs',''),1)}h</td>
        </tr>"""

    # ── Alpha trend section ───────────────────────────────────────────────────
    trend_rows_html = ""
    for i, (name, history) in enumerate(alpha_chart.items()):
        color  = STATION_COLORS[i % len(STATION_COLORS)]
        values = [r.get("alpha_obs") for r in history]
        weeks  = [r["week"][-5:] for r in history]   # MM-DD
        spark  = sparkline_svg(values, color)
        latest = values[-1] if values else None
        lbl, fg, bg = alpha_badge(latest)
        trend_rows_html += f"""
        <tr>
          <td><span style="color:{color};font-weight:700">●</span> {name}</td>
          <td style="text-align:center">{spark}</td>
          <td><span style="background:{bg};color:{fg};padding:2px 6px;border-radius:8px;
               font-size:9px;font-weight:700">{fmt(latest)} {lbl}</span></td>
          <td style="color:#9ca3af;font-size:10px">{' · '.join(weeks)}</td>
        </tr>"""

    # ── History summary ───────────────────────────────────────────────────────
    n_weeks_total = len(set(r["week"] for r in skill_all))

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Meteo Skill Monitor · PT + Sardegna</title>
<style>
  :root{{--accent:#e85d2f;--border:#e5e7eb;--dim:#9ca3af;--surface:#f9fafb}}
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:system-ui,-apple-system,sans-serif;background:#f0f2f5;
        color:#111827;padding:24px;max-width:1200px;margin:0 auto}}
  h1{{font-size:20px;font-weight:700;color:var(--accent);
      border-bottom:3px solid var(--accent);padding-bottom:10px;margin-bottom:6px}}
  h2{{font-size:11px;font-weight:700;color:var(--dim);text-transform:uppercase;
      letter-spacing:.08em;margin:24px 0 10px}}
  .meta{{font-size:11px;color:var(--dim);margin-bottom:20px}}
  .card{{background:#fff;border:1px solid var(--border);border-radius:8px;
         padding:16px;margin-bottom:16px;box-shadow:0 1px 3px rgba(0,0,0,.06)}}
  table{{width:100%;border-collapse:collapse;font-size:11.5px;font-family:monospace}}
  th{{background:var(--surface);color:var(--dim);padding:6px 10px;
      text-align:left;border-bottom:2px solid var(--border);
      font-size:9px;text-transform:uppercase;letter-spacing:.06em;white-space:nowrap}}
  td{{padding:6px 10px;border-bottom:1px solid var(--border);vertical-align:middle}}
  tr:hover td{{background:#fff7ed}}
  .legend{{display:flex;gap:20px;flex-wrap:wrap;font-size:11px;color:#4b5563;
            margin-top:14px;padding-top:12px;border-top:1px solid var(--border)}}
  .leg-item{{display:flex;align-items:center;gap:5px}}
  .dot{{width:8px;height:8px;border-radius:50%;display:inline-block}}
  .stats-bar{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:16px}}
  .stat-mini{{background:#fff;border:1px solid var(--border);border-radius:6px;
              padding:10px 14px;text-align:center}}
  .sv{{font-size:22px;font-weight:700;font-family:monospace;color:var(--accent)}}
  .sl{{font-size:9px;color:var(--dim);text-transform:uppercase;margin-top:3px}}
</style>
</head>
<body>

<h1>🌬 Meteo Skill Monitor</h1>
<p class="meta">
  Generated: {now_str} &nbsp;·&nbsp;
  Stations: 5 Portugal + 3 Sardegna &nbsp;·&nbsp;
  Source: Open-Meteo IFS forecast vs ERA5-NRT observed &nbsp;·&nbsp;
  History: {n_weeks_total} week{'s' if n_weeks_total != 1 else ''}
</p>

<!-- Summary stats bar -->
<div class="stats-bar">
  <div class="stat-mini">
    <div class="sv">{len(skill_last)}</div>
    <div class="sl">Stations this week</div>
  </div>
  <div class="stat-mini">
    <div class="sv">{last_skill_week or '—'}</div>
    <div class="sl">Latest week</div>
  </div>
  <div class="stat-mini">
    <div class="sv">{n_weeks_total}</div>
    <div class="sl">Weeks collected</div>
  </div>
  <div class="stat-mini">
    <div class="sv">{sum(int(r.get('n_pairs',0)) for r in skill_last):,}</div>
    <div class="sl">Hour pairs compared</div>
  </div>
</div>

<!-- Skill metrics table -->
<div class="card">
  <h2>Forecast Skill · Week {last_skill_week}</h2>
  <table>
    <thead><tr>
      <th>Station</th>
      <th>Country</th>
      <th>RMSE Wind</th>
      <th>Bias Wind</th>
      <th>RMSE Gust</th>
      <th>MAE Dir</th>
      <th>Regime HR</th>
      <th>α observed</th>
      <th>α forecast</th>
      <th>α error</th>
      <th>Dom. regime</th>
      <th>Avg run</th>
    </tr></thead>
    <tbody>{skill_rows_html}</tbody>
  </table>

  <div class="legend">
    <div class="leg-item"><span class="dot" style="background:#15803d"></span> RMSE &lt;2 excellent</div>
    <div class="leg-item"><span class="dot" style="background:#d97706"></span> RMSE 2–4 acceptable</div>
    <div class="leg-item"><span class="dot" style="background:#dc2626"></span> RMSE &gt;4 poor</div>
    <div class="leg-item"><span class="dot" style="background:#1d4ed8"></span> Bias negative (underforecast)</div>
    <div class="leg-item"><span class="dot" style="background:#dc2626"></span> Bias positive (overforecast)</div>
  </div>
</div>

<!-- Alpha trend table -->
<div class="card">
  <h2>α Stability Index · 8-week trend</h2>
  <table>
    <thead><tr>
      <th>Station</th>
      <th>Trend (obs)</th>
      <th>Latest α</th>
      <th>Weeks</th>
    </tr></thead>
    <tbody>{trend_rows_html}</tbody>
  </table>
  <div class="legend">
    <div class="leg-item"><span class="dot" style="background:#15803d"></span> α ≥ 0.55 Stable (single regime dominates)</div>
    <div class="leg-item"><span class="dot" style="background:#d97706"></span> α 0.38–0.55 Moderate (regime transitions)</div>
    <div class="leg-item"><span class="dot" style="background:#dc2626"></span> α &lt; 0.38 Variable (chaotic, multiple regimes)</div>
  </div>
</div>

<!-- Data links -->
<p style="font-size:11px;color:var(--dim);margin-top:10px">
  Raw data:
  <a href="../data/skill/skill_cumulative.csv" style="color:var(--accent)">skill_cumulative.csv</a> ·
  <a href="../data/skill/alpha_weekly.csv"    style="color:var(--accent)">alpha_weekly.csv</a>
</p>

</body>
</html>"""

    Path(out).parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"  Report generated → {out}")


if __name__ == "__main__":
    generate()
