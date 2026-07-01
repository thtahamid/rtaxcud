# CUD 4IR Mobility Innovation Challenge — RTA-Inspired Dataset

**Theme:** *Solving Traffic Congestion with AI* — Dubai
**Prepared for:** Canadian University Dubai × RTA · 4IR Mobility Lab (Emerging Innovative Technologies Section, TSG)
**Coverage:** 1 January 2023 → 31 December 2025 (3 full years, hourly)

> ⚠️ **This is synthetic, RTA-*inspired* data.** It contains **no real personal data** and was **not** taken from any production system. It is engineered to be statistically realistic — it carries genuine Dubai patterns (rush hours, the UAE Saturday–Sunday weekend, Ramadan, summer lull, weather, year-on-year growth and real-world events) so your AI prototypes behave the way they would on real data. Use it freely inside the challenge sandbox.

---

## What's in the box

Almost **1 million rows** across 18 CSV files, all join-able on a few shared keys
(`location_id`, `junction_id`, `gate_id`, `date`, `datetime`).

| # | Dataset | Grain | Files | What it gives you |
|---|---------|-------|-------|-------------------|
| 1 | **Traffic flow & volume** | hourly × 18 sites | `traffic_volume_hourly_2023/24/25.csv` | Vehicle counts, speeds, congestion (v/c, LOS) on real Dubai corridors |
| 2 | **Signal timing — plans** | static | `signal_timing_plans.csv` | Phasing, cycle lengths, green splits per junction & time-of-day program |
| 3 | **Signal timing — performance** | hourly × 10 junctions | `signal_performance_hourly_2023/24/25.csv` | Saturation, delay, queues, phase failures (adaptive vs fixed) |
| 4 | **Incident & event log** | one row per event | `incidents_log.csv` | Accidents, breakdowns, closures, flooding — with location, severity, duration |
| 5 | **Weather** | hourly | `weather_hourly_2023/24/25.csv` | Temp, humidity, wind, visibility, rain, condition |
| 6 | **Salik toll gates** | hourly × 7 gates | `salik_toll_hourly_2023/24/25.csv` | Crossings, toll rate, revenue (incl. 2025 dynamic pricing) |
| 7 | **Metro ridership** | daily × 2 lines | `metro_ridership_daily.csv` | Red/Green line daily riders (a demand-shift signal) |
| 8 | **Locations reference** | 18 rows | `locations_reference.csv` | Master of every count site — lat/long, lanes, capacity, road |
| 9 | **Junctions reference** | 10 rows | `signal_junctions_reference.csv` | Master of every signalised junction |
| 10 | **Calendar context** | daily | `calendar_context.csv` | Weekend / holiday / Ramadan / school term / DSF / weather-event flags |

Full column-by-column definitions: **[docs/DATA_DICTIONARY.md](docs/DATA_DICTIONARY.md)**

---

## The three challenge directions → which data to start with

The brief invites four solution directions. Here's the fastest path into the data for each:

**🔮 Predictive Analytics — *forecast traffic spikes before they happen***
Start: `traffic_volume_hourly_*` + `weather_hourly_*` + `calendar_context`.
Predict next-hour/next-day `volume_vph` or `avg_speed_kph` per `location_id`. The calendar
and weather files are your feature store (day-of-week, Ramadan, rain, holidays…).

**🚦 Adaptive Signal Control — *retime lights to real flow***
Start: `signal_performance_hourly_*` + `signal_timing_plans` + `signal_junctions_reference`.
Compare `degree_of_saturation` / `avg_delay_s_per_veh` against the static green splits, and
propose better cycle/green allocations. Adaptive (`SCOOT`) vs fixed-time junctions are flagged.

**🧭 Smart Routing — *steer drivers away from building congestion***
Start: `traffic_volume_hourly_*` (speeds + LOS) + `incidents_log`.
Use live speed/LOS per corridor and active incidents to recommend alternates
(e.g. Garhoud Bridge vs Maktoum Bridge vs Business Bay Crossing across the Creek).

**👁 Computer Vision** — note this dataset has **no images** (by design). If your team picks the
vision direction, you can still use `incidents_log` as the *labels/ground-truth* an
incident-detection model would produce, and simulate detections feeding the routing/signal logic.

---

## Quick start

```python
import pandas as pd

# Load one year of traffic and join the reference + calendar + weather
traffic  = pd.read_csv("datasets/traffic_volume_hourly_2024.csv", parse_dates=["datetime"])
locs     = pd.read_csv("datasets/locations_reference.csv")
calendar = pd.read_csv("datasets/calendar_context.csv", parse_dates=["date"])
weather  = pd.read_csv("datasets/weather_hourly_2024.csv", parse_dates=["datetime"])

calendar["date"] = calendar["date"].dt.strftime("%Y-%m-%d")
df = (traffic
      .merge(locs, on="location_id", suffixes=("", "_ref"))
      .merge(weather[["datetime", "temp_c", "precip_mm", "condition", "visibility_km"]], on="datetime")
      .merge(calendar[["date", "is_weekend", "is_public_holiday", "is_ramadan", "school_status"]],
             on="date", how="left"))

# Morning peak on Sheikh Zayed Road, northbound
szr = df[df.location_id == "SZR_N1"]
print(szr.groupby(szr.datetime.dt.hour)["volume_vph"].mean().round())
```

To regenerate everything from scratch (reproducible, seed = 42):

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install numpy pandas
python scripts/generate_data.py
```

---

## What makes this data *feel real* (patterns built in)

- **Rush hours** — AM peak 07:00–09:00 (inbound corridors saturate near capacity), PM peak 17:00–20:00.
- **UAE weekend** — Saturday & Sunday are the weekend; Friday is a lighter work day. Commuter
  corridors drop on weekends; **leisure** corridors (Jumeirah Beach Rd) rise.
- **Ramadan** (different dates each year) — quieter daytime, a sharp **pre-iftar surge**, an
  empty-roads **iftar lull**, then busy late nights.
- **Summer lull** — June–August dip (heat + school break + travel); cool-season peak Oct–Mar.
- **Year-on-year growth** — traffic grows ~6%/yr overall; the **Expo / Dubai South** corridor grows ~20%/yr.
- **Weather** — rain and fog cut speeds and **multiply incident risk**; heavy rain pushes riders onto the Metro.
- **Real events you can *discover*** (great demo material):
  - **16 April 2024** — the historic Dubai rainstorm: speeds collapse, 60+ incidents in a day, Metro spikes.
  - **31 January 2025** — RTA **dynamic Salik tolling** begins (peak AED 6 / off-peak AED 4 / free 01:00–06:00).

A fuller "what's hidden in here" guide for mentors & judges is in
**[docs/PATTERNS_AND_ANSWER_KEY.md](docs/PATTERNS_AND_ANSWER_KEY.md)**.

---

## Locations covered (all real Dubai)

Sheikh Zayed Road (E11) at Defence / DIFC / Mall of the Emirates interchanges · Al Khail Road (E44) ·
Mohammed Bin Zayed Road (E311) · Emirates Road (E611) · Al Ittihad Road (Dubai–Sharjah) ·
Airport Road · Al Garhoud, Al Maktoum & Business Bay Creek crossings · Jumeirah Beach Road ·
Expo / Dubai South. Signalised junctions at Defence, Al Safa, Al Wasl, Oud Metha, Garhoud, Al Mamzar,
Al Quoz, Al Barsha, Karama and Deira. Salik gates: Al Garhoud, Al Maktoum, Al Barsha, Al Safa,
Airport Tunnel, Al Mamzar, Jebel Ali.
