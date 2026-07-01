#!/usr/bin/env python3
"""
CUD 4IR Mobility Innovation Challenge — Synthetic RTA Traffic Data Generator
============================================================================

Generates three full years (2023, 2024, 2025) of realistic, RTA-inspired open
mobility data for Dubai. The data is SYNTHETIC (no real personal data, no
production systems) but is engineered to FEEL real: it carries day-of-week
effects (UAE Sat-Sun weekend), morning/evening rush-hour profiles, Ramadan
shifts, summer lull, year-over-year growth, weather effects, and several
real-world "discoverable" events:

  * 16 Apr 2024  -> historic Dubai rainstorm / flooding (massive disruption)
  * 31 Jan 2025  -> RTA dynamic Salik tolling begins (peak AED 6 / off-peak AED 4)
  * Ramadan each year -> daytime dip + pre-iftar surge + late-night activity
  * Expo / Dubai South corridor grows faster than the rest year over year

All locations are real Dubai roads, bridges, junctions and Salik gates.

Outputs (./datasets):
  locations_reference.csv
  calendar_context.csv
  weather_hourly_2023.csv / _2024.csv / _2025.csv
  traffic_volume_hourly_2023.csv / _2024.csv / _2025.csv
  signal_junctions_reference.csv
  signal_timing_plans.csv
  signal_performance_hourly_2023.csv / _2024.csv / _2025.csv
  incidents_log.csv
  salik_toll_hourly_2023.csv / _2024.csv / _2025.csv
  metro_ridership_daily.csv
"""

import numpy as np
import pandas as pd
from datetime import date, timedelta

RNG = np.random.default_rng(42)
OUT = "datasets"
YEARS = [2023, 2024, 2025]
TZ = "Asia/Dubai"  # UTC+4, no DST

# ---------------------------------------------------------------------------
# 1. CALENDAR CONTEXT  (Ramadan, Eid, holidays, school terms, special events)
# ---------------------------------------------------------------------------
# Ramadan (approx. observed dates in the UAE)
RAMADAN = {
    2023: (date(2023, 3, 23), date(2023, 4, 20)),
    2024: (date(2024, 3, 11), date(2024, 4, 9)),
    2025: (date(2025, 3, 1),  date(2025, 3, 29)),
}
# Public holidays (date -> name).  Eid spans multiple days.
def _span(d0, n):  # helper: n consecutive dates from d0
    return [d0 + timedelta(days=i) for i in range(n)]

PUBLIC_HOLIDAYS = {}
def _add_holiday(days, name):
    for d in days:
        PUBLIC_HOLIDAYS[d] = name

_add_holiday([date(2023,1,1), date(2024,1,1), date(2025,1,1)], "New Year's Day")
# Eid Al Fitr (end of Ramadan, ~3-4 days)
_add_holiday(_span(date(2023,4,21),4), "Eid Al Fitr")
_add_holiday(_span(date(2024,4,10),3), "Eid Al Fitr")
_add_holiday(_span(date(2025,3,30),4), "Eid Al Fitr")
# Arafat Day + Eid Al Adha (~4 days)
_add_holiday(_span(date(2023,6,27),5), "Eid Al Adha")
_add_holiday(_span(date(2024,6,15),5), "Eid Al Adha")
_add_holiday(_span(date(2025,6,5),5),  "Eid Al Adha")
# Islamic New Year
_add_holiday([date(2023,7,21)], "Hijri New Year")
_add_holiday([date(2024,7,7)],  "Hijri New Year")
_add_holiday([date(2025,6,26)], "Hijri New Year")
# Prophet's Birthday (Mawlid)
_add_holiday([date(2023,9,29)], "Prophet's Birthday")
_add_holiday([date(2024,9,15)], "Prophet's Birthday")
_add_holiday([date(2025,9,4)],  "Prophet's Birthday")
# Commemoration Day + UAE National Day (1-3 Dec)
_add_holiday([date(2023,12,1)], "Commemoration Day")
_add_holiday([date(2024,12,1)], "Commemoration Day")
_add_holiday([date(2025,12,1)], "Commemoration Day")
_add_holiday(_span(date(2023,12,2),2), "UAE National Day")
_add_holiday(_span(date(2024,12,2),2), "UAE National Day")
_add_holiday(_span(date(2025,12,2),2), "UAE National Day")

# Notable weather/rain events (date -> (label, severity 1-5, precip_mm peak/day))
RAIN_EVENTS = {
    date(2023,1,15): ("Winter rain",        2, 12),
    date(2023,2,26): ("Winter rain",        2, 9),
    date(2023,11,17):("Early winter rain",  2, 14),
    date(2024,1,1):  ("New Year storm",     3, 28),
    date(2024,3,9):  ("March thunderstorm", 3, 35),
    date(2024,4,16): ("HISTORIC FLOODING",  5, 160),  # record-breaking storm
    date(2024,4,17): ("Flood aftermath",    4, 40),
    date(2024,11,30):("Winter storm",       3, 30),
    date(2024,12,15):("Winter rain",        2, 11),
    date(2025,1,12): ("Winter rain",        2, 13),
    date(2025,2,20): ("Winter storm",       3, 26),
    date(2025,4,2):  ("Spring rain",        2, 10),
}
# Sandstorm / dust events
DUST_EVENTS = {
    date(2023,6,2): 3, date(2023,7,18): 2,
    date(2024,5,28): 3, date(2024,8,5): 2,
    date(2025,6,10): 3, date(2025,3,17): 2,
}
# Dubai Shopping Festival (mall/leisure uplift) and other city events
def _in_dsf(d):
    return (d.month == 12 and d.day >= 8) or (d.month == 1) or (d.month == 2 and d.day <= 5)

def school_term(d):
    # UAE school calendar (approx): summer break Jul-Aug; winter & spring short breaks
    if d.month in (7, 8):
        return "Summer Break"
    if d.month == 12 and d.day >= 10:
        return "Winter Break"
    if d.month == 1 and d.day <= 2:
        return "Winter Break"
    if d.month == 3 and 25 <= d.day <= 31:
        return "Spring Break"
    return "In Session"

def is_ramadan(d):
    s, e = RAMADAN[d.year]
    return s <= d <= e

def build_calendar():
    rows = []
    d = date(YEARS[0], 1, 1)
    end = date(YEARS[-1], 12, 31)
    while d <= end:
        wd = d.weekday()                      # Mon=0 .. Sun=6
        is_weekend = wd in (5, 6)             # UAE weekend = Sat, Sun
        hol = PUBLIC_HOLIDAYS.get(d, "")
        ram = is_ramadan(d)
        rain = RAIN_EVENTS.get(d)
        dust = DUST_EVENTS.get(d, 0)
        rows.append({
            "date": d.isoformat(),
            "year": d.year,
            "month": d.month,
            "day": d.day,
            "day_of_week": d.strftime("%A"),
            "is_weekend": int(is_weekend),
            "is_public_holiday": int(bool(hol)),
            "holiday_name": hol,
            "is_ramadan": int(ram),
            "school_status": school_term(d),
            "is_dsf": int(_in_dsf(d)),
            "rain_event": rain[0] if rain else "",
            "rain_severity": rain[1] if rain else 0,
            "dust_severity": dust,
        })
        d += timedelta(days=1)
    return pd.DataFrame(rows)

# ---------------------------------------------------------------------------
# 2. WEATHER  (hourly, Dubai climate normals + the seeded events)
# ---------------------------------------------------------------------------
# Monthly average temp (C), and approx sunset hour (local) used for Ramadan iftar.
MONTH_TEMP   = {1:19,2:21,3:24,4:28,5:33,6:35,7:37,8:37,9:34,10:31,11:26,12:21}
MONTH_HUMID  = {1:65,2:63,3:60,4:55,5:50,6:55,7:58,8:60,9:60,10:58,11:60,12:64}
SUNSET_HOUR  = {1:17.8,2:18.1,3:18.3,4:18.5,5:18.8,6:19.0,7:19.1,8:18.8,9:18.4,10:18.0,11:17.7,12:17.6}

def build_weather(year, cal):
    idx = pd.date_range(f"{year}-01-01", f"{year}-12-31 23:00", freq="h")
    n = len(idx)
    months = idx.month.to_numpy()
    hours = idx.hour.to_numpy()
    # Diurnal temperature: min ~5-6am, max ~3-4pm
    diurnal = 6.5 * np.sin((hours - 9) / 24 * 2 * np.pi)  # peak near 15:00
    base_t = np.array([MONTH_TEMP[m] for m in months]) + diurnal
    base_t += RNG.normal(0, 1.2, n)
    humid = np.array([MONTH_HUMID[m] for m in months]) + 18*np.sin((hours-3)/24*2*np.pi) + RNG.normal(0,4,n)
    humid = np.clip(humid, 12, 99)
    wind = np.clip(RNG.gamma(2.0, 6.0, n), 2, 60)
    vis = np.full(n, 10.0)
    precip = np.zeros(n)
    cond = np.array(["Clear"] * n, dtype=object)

    # daytime mostly Sunny, some Partly Cloudy / Hazy
    day_mask = (hours >= 7) & (hours <= 18)
    cond[day_mask] = RNG.choice(["Sunny","Partly Cloudy","Hazy"], size=day_mask.sum(), p=[0.7,0.22,0.08])
    cond[~day_mask] = "Clear"

    # Winter-morning fog (Nov-Mar, 03:00-08:00) on a fraction of days
    rain_lookup = {pd.Timestamp(k): v for k, v in RAIN_EVENTS.items()}
    dust_lookup = {pd.Timestamp(k): v for k, v in DUST_EVENTS.items()}
    day0 = idx.normalize().to_numpy()

    for d in pd.unique(day0):
        d_ts = pd.Timestamp(d)
        m = d_ts.month
        day_mask_d = day0 == d
        # Fog
        if m in (11,12,1,2,3) and RNG.random() < 0.16:
            fog_hours = (hours >= 3) & (hours <= 8) & day_mask_d
            cond[fog_hours] = "Fog"
            vis[fog_hours] = np.clip(RNG.uniform(0.2, 1.2, fog_hours.sum()), 0.1, 2.0)
        # Dust
        if d_ts in dust_lookup:
            sev = dust_lookup[d_ts]
            dust_hours = (hours >= 9) & (hours <= 20) & day_mask_d
            cond[dust_hours] = "Dust/Sandstorm"
            vis[dust_hours] = np.clip(3.5 - sev*0.6 + RNG.uniform(-0.5,0.5,dust_hours.sum()), 0.5, 6)
            wind[dust_hours] *= 1.6
        # Rain
        if d_ts in rain_lookup:
            label, sev, peak = rain_lookup[d_ts]
            # rain concentrated in a window; heavier events longer
            start = RNG.integers(2, 12)
            length = int(np.clip(sev*2 + RNG.integers(0,4), 3, 16))
            rain_hours_mask = (hours >= start) & (hours < start+length) & day_mask_d
            k = rain_hours_mask.sum()
            if k > 0:
                shape = np.hanning(k+2)[1:-1] if k > 1 else np.array([1.0])
                shape = shape/shape.sum() if shape.sum()>0 else np.ones(k)/k
                precip[rain_hours_mask] = shape * peak
                if sev >= 4:
                    cond[rain_hours_mask] = "Thunderstorm"
                elif sev >= 3:
                    cond[rain_hours_mask] = "Heavy Rain"
                else:
                    cond[rain_hours_mask] = "Light Rain"
                vis[rain_hours_mask] = np.clip(8 - sev*1.4, 0.3, 8)
                base_t[rain_hours_mask] -= sev*0.8

    df = pd.DataFrame({
        "datetime": idx.strftime("%Y-%m-%d %H:%M:%S"),
        "date": idx.strftime("%Y-%m-%d"),
        "hour": hours,
        "temp_c": np.round(base_t, 1),
        "humidity_pct": np.round(humid).astype(int),
        "wind_kph": np.round(wind, 1),
        "visibility_km": np.round(vis, 1),
        "precip_mm": np.round(precip, 1),
        "condition": cond,
    })
    return df

# weather -> speed/incident multipliers
def weather_speed_factor(cond, precip, vis):
    f = np.ones(len(cond))
    f = np.where(cond == "Hazy", 0.98, f)
    f = np.where(cond == "Light Rain", 0.88, f)
    f = np.where(cond == "Heavy Rain", 0.70, f)
    f = np.where(cond == "Thunderstorm", 0.55, f)
    f = np.where(cond == "Fog", 0.78, f)
    f = np.where(cond == "Dust/Sandstorm", 0.85, f)
    f = np.where(vis < 0.5, f*0.85, f)
    return f

def weather_incident_mult(cond, vis):
    m = np.ones(len(cond))
    m = np.where(cond == "Light Rain", 3.0, m)
    m = np.where(cond == "Heavy Rain", 6.0, m)
    m = np.where(cond == "Thunderstorm", 9.0, m)
    m = np.where(cond == "Fog", 4.0, m)
    m = np.where(cond == "Dust/Sandstorm", 2.5, m)
    m = np.where(vis < 0.4, m*1.5, m)
    return m

# ---------------------------------------------------------------------------
# 3. LOCATIONS (directional road/segment count sites — real Dubai roads)
# ---------------------------------------------------------------------------
# profile types: cin=commuter inbound (AM heavy), cout=commuter outbound (PM heavy),
#                mix=mixed arterial, leis=leisure, frgt=freight corridor
LOCATIONS = [
    # id, name, road_code, road_name, area, direction, lanes, freeflow, limit, capacity_vph, aadt_dir, profile, lat, lon, growth_key
    ("SZR_N1","Sheikh Zayed Rd @ 1st Interchange (Defence)","E11","Sheikh Zayed Road","Trade Centre","NB (to Deira)",6,105,100,12000,138000,"cin",25.2230,55.2820,"core"),
    ("SZR_S1","Sheikh Zayed Rd @ 1st Interchange (Defence)","E11","Sheikh Zayed Road","Trade Centre","SB (to Abu Dhabi)",6,105,100,12000,132000,"cout",25.2228,55.2832,"core"),
    ("SZR_N2","Sheikh Zayed Rd @ Financial Centre (DIFC)","E11","Sheikh Zayed Road","DIFC","NB (to Deira)",6,105,100,12000,134000,"cin",25.2110,55.2790,"core"),
    ("SZR_S2","Sheikh Zayed Rd @ Financial Centre (DIFC)","E11","Sheikh Zayed Road","DIFC","SB (to Abu Dhabi)",6,105,100,12000,130000,"cout",25.2108,55.2802,"core"),
    ("SZR_N4","Sheikh Zayed Rd @ 4th Interchange (Mall of Emirates)","E11","Sheikh Zayed Road","Al Barsha","NB (to Deira)",7,105,100,13500,142000,"cin",25.1180,55.2000,"core"),
    ("SZR_S4","Sheikh Zayed Rd @ 4th Interchange (Mall of Emirates)","E11","Sheikh Zayed Road","Al Barsha","SB (to Abu Dhabi)",7,105,100,13500,140000,"cout",25.1178,55.2012,"core"),
    ("EKR_N1","Al Khail Rd @ Business Bay","E44","Al Khail Road","Business Bay","NB (to Deira)",5,100,100,10000,98000,"cin",25.1860,55.2700,"core"),
    ("EKR_S1","Al Khail Rd @ Al Quoz","E44","Al Khail Road","Al Quoz","SB (to Jebel Ali)",5,100,100,10000,95000,"cout",25.1490,55.2350,"core"),
    ("MBZ_E1","Mohammed Bin Zayed Rd @ Dubai Investment Park","E311","Mohammed Bin Zayed Road","DIP","Both (sample EB)",6,110,110,11000,86000,"frgt",24.9900,55.1700,"south"),
    ("EMR_E1","Emirates Rd @ Al Awir","E611","Emirates Road","Al Awir","Both (sample EB)",5,110,110,9000,62000,"frgt",25.1700,55.4400,"core"),
    ("ITT_W1","Al Ittihad Rd @ Al Mamzar (Dubai-Sharjah border)","D89","Al Ittihad Road","Al Mamzar","WB (to Dubai)",5,80,80,7000,96000,"cin",25.2950,55.3550,"core"),
    ("ITT_E1","Al Ittihad Rd @ Al Qiyadah","D89","Al Ittihad Road","Al Qiyadah","EB (to Sharjah)",5,80,80,7000,90000,"cout",25.2680,55.3380,"core"),
    ("AIR_W1","Airport Rd @ Al Garhoud","D89","Airport Road","Al Garhoud","WB (to city)",4,80,80,6000,72000,"cin",25.2480,55.3520,"core"),
    ("GAR_N1","Al Garhoud Bridge","D75","Al Garhoud Bridge","Garhoud","NB (to Deira)",5,80,80,7000,82000,"mix",25.2330,55.3300,"core"),
    ("MAK_N1","Al Maktoum Bridge","D75","Al Maktoum Bridge","Bur Dubai","NB (to Deira)",4,60,60,6000,68000,"mix",25.2400,55.3170,"core"),
    ("BBC_S1","Business Bay Crossing","E11","Business Bay Crossing","Business Bay","SB (to Bur Dubai)",5,80,80,8000,86000,"mix",25.1920,55.2900,"core"),
    ("JBR_X1","Jumeirah Beach Rd @ Jumeirah 1","D94","Jumeirah Beach Road","Jumeirah","Both (sample)",3,60,60,4000,34000,"leis",25.2080,55.2480,"core"),
    ("DWC_X1","Expo Rd @ Dubai South / DWC","E77","Expo Road","Dubai South","Both (sample)",4,100,100,6000,29000,"mix",24.8960,55.1610,"expo"),
]
LOC_COLS = ["location_id","location_name","road_code","road_name","area","direction","num_lanes",
            "free_flow_speed_kph","speed_limit_kph","capacity_vph","aadt_per_direction",
            "profile_type","latitude","longitude","growth_key"]

def locations_df():
    return pd.DataFrame(LOCATIONS, columns=LOC_COLS)

# year-over-year growth multipliers per corridor group (2024 = baseline 1.0)
GROWTH = {
    "core":  {2023:0.94, 2024:1.00, 2025:1.06},
    "south": {2023:0.90, 2024:1.00, 2025:1.10},
    "expo":  {2023:0.78, 2024:1.00, 2025:1.20},  # Dubai South growing fast
}
# seasonal monthly factor (Dubai: summer lull, cool-season peak)
MONTH_FACTOR = {1:1.06,2:1.07,3:1.04,4:1.00,5:0.95,6:0.88,7:0.84,8:0.85,9:0.93,10:1.02,11:1.07,12:1.05}

# hourly profiles (raw weights, normalised in code). index 0..23
PROFILES_RAW = {
    "weekday": [0.6,0.4,0.3,0.3,0.5,1.2,3.0,6.5,7.5,5.5,4.5,4.5,5.0,5.0,4.8,5.0,5.8,7.0,7.5,6.5,5.0,3.8,2.5,1.4],
    "weekend": [1.2,0.9,0.6,0.4,0.3,0.4,0.6,1.0,1.8,2.8,3.8,4.6,5.0,5.0,4.8,4.8,5.2,5.8,6.5,6.8,6.5,5.5,4.0,2.2],
    "freight_wd":[2.0,1.8,1.6,1.6,1.8,2.4,3.4,4.6,5.0,5.2,5.2,5.0,4.6,4.6,4.8,5.0,5.2,5.0,4.6,4.0,3.6,3.2,2.8,2.2],
}
def norm(a):
    a = np.array(a, float); return a/a.sum()

def hourly_profile(profile_type, is_weekend, ramadan, month):
    if profile_type == "frgt":
        base = norm(PROFILES_RAW["freight_wd"]) if not is_weekend else norm(PROFILES_RAW["weekend"])
    elif is_weekend:
        base = norm(PROFILES_RAW["weekend"]).copy()
        if profile_type == "leis":
            w = norm(PROFILES_RAW["weekend"]).copy()
            for h in range(16,24): w[h]*=1.4
            for h in range(10,16): w[h]*=1.2
            base = norm(w)
    else:
        w = np.array(PROFILES_RAW["weekday"], float)
        if profile_type == "cin":      # boost AM peak
            for h in (6,7,8,9): w[h]*=1.35
            for h in (17,18,19): w[h]*=0.85
        elif profile_type == "cout":   # boost PM peak
            for h in (6,7,8): w[h]*=0.85
            for h in (16,17,18,19,20): w[h]*=1.30
        elif profile_type == "leis":
            for h in range(11,23): w[h]*=1.25
            for h in (7,8,9): w[h]*=0.7
        base = norm(w)
    if ramadan:
        w = base.copy()
        ss = SUNSET_HOUR[month]
        for h in range(24):
            if 10 <= h <= 15: w[h]*=0.62          # working-day dip, shorter hours
            if int(ss)-1 <= h <= int(ss): w[h]*=1.9 # pre-iftar surge
            if int(ss)+1 <= h <= int(ss)+1: w[h]*=0.45  # iftar lull (roads empty)
            if 21 <= h <= 23: w[h]*=1.5           # post-taraweeh nightlife
            if 0 <= h <= 2:   w[h]*=1.7
        base = norm(w)
    return base

# day-of-week factor for commuter vs leisure
DOW_COMMUTER = {0:1.00,1:1.04,2:1.05,3:1.03,4:0.86,5:0.80,6:0.84}   # Mon..Sun
DOW_LEISURE  = {0:0.85,1:0.88,2:0.90,3:0.95,4:1.15,5:1.20,6:1.05}
DOW_FREIGHT  = {0:1.02,1:1.05,2:1.05,3:1.04,4:0.80,5:0.62,6:0.78}

def dow_factor(profile_type, wd):
    if profile_type == "leis": return DOW_LEISURE[wd]
    if profile_type == "frgt": return DOW_FREIGHT[wd]
    return DOW_COMMUTER[wd]

# ---------------------------------------------------------------------------
# 4. TRAFFIC VOLUME & SPEED (hourly per location)
# ---------------------------------------------------------------------------
def bpr_speed(freeflow, vc):
    # BPR: travel time multiplier 1 + a*vc^b ; speed = freeflow / mult
    a, b = 0.62, 4.0
    mult = 1 + a*np.power(np.clip(vc,0,2.5), b)
    spd = freeflow/mult
    return np.clip(spd, 6, freeflow)

def los_from_vc(vc):
    bins = [0.35,0.55,0.75,0.90,1.00]
    labels = ["A","B","C","D","E","F"]
    out = np.array(["A"]*len(vc), dtype=object)
    for i,t in enumerate(bins):
        out = np.where(vc>t, labels[i+1], out)
    return out

def build_traffic(year, cal, weather):
    cal_y = cal[cal.year==year].set_index("date")
    wx = weather.set_index("datetime")
    locs = locations_df()
    idx = pd.date_range(f"{year}-01-01", f"{year}-12-31 23:00", freq="h")
    dates = idx.strftime("%Y-%m-%d").to_numpy()
    hours = idx.hour.to_numpy()
    months = idx.month.to_numpy()
    wd = idx.weekday.to_numpy()
    dstr = idx.strftime("%Y-%m-%d %H:%M:%S").to_numpy()

    # daily context arrays
    uniq_dates = pd.unique(dates)
    is_we   = {d:int(cal_y.loc[d,"is_weekend"]) for d in uniq_dates}
    is_ram  = {d:int(cal_y.loc[d,"is_ramadan"]) for d in uniq_dates}
    is_hol  = {d:int(cal_y.loc[d,"is_public_holiday"]) for d in uniq_dates}
    is_dsf  = {d:int(cal_y.loc[d,"is_dsf"]) for d in uniq_dates}

    # weather aligned to this year's hourly index
    wxy = wx.loc[dstr]
    w_cond = wxy["condition"].to_numpy()
    w_precip = wxy["precip_mm"].to_numpy()
    w_vis = wxy["visibility_km"].to_numpy()
    wsf = weather_speed_factor(w_cond, w_precip, w_vis)

    frames = []
    for _, L in locs.iterrows():
        g = GROWTH[L.growth_key][year]
        cap = L.capacity_vph
        aadt = L.aadt_per_direction
        ff = L.free_flow_speed_kph
        prof = L.profile_type
        vol = np.zeros(len(idx))
        # build per-hour volume
        # group by date to reuse profile arrays
        for d in uniq_dates:
            sel = dates == d
            h = hours[sel]
            m = months[sel][0]
            wday = wd[sel][0]
            we = is_we[d]; ram = is_ram[d]; hol = is_hol[d]; dsf = is_dsf[d]
            p = hourly_profile(prof, bool(we), bool(ram), m)
            daily = aadt * g * MONTH_FACTOR[m] * dow_factor(prof, wday)
            if ram: daily *= 0.90
            if hol:
                daily *= (1.35 if prof=="leis" else 0.55)   # commute collapses, leisure up
            if dsf and prof=="leis": daily *= 1.12
            vol[sel] = daily * p[h]
        # weather depresses volume modestly (people delay/cancel trips in heavy rain)
        wx_volf = np.ones(len(idx))
        wx_volf = np.where(w_cond=="Heavy Rain", 0.80, wx_volf)
        wx_volf = np.where(w_cond=="Thunderstorm", 0.60, wx_volf)
        wx_volf = np.where(w_cond=="Light Rain", 0.93, wx_volf)
        wx_volf = np.where(w_cond=="Fog", 0.92, wx_volf)
        vol *= wx_volf
        # noise
        vol *= RNG.normal(1.0, 0.05, len(idx))
        vol = np.clip(vol, 0, None)
        # throughput saturates near capacity
        demand = vol.copy()
        vol = np.minimum(vol, cap*1.05)
        vc = vol/cap
        speed = bpr_speed(ff, vc) * wsf
        speed *= RNG.normal(1.0, 0.03, len(idx))
        speed = np.clip(speed, 5, ff)
        occ = np.clip(vc*0.78 + RNG.normal(0,0.02,len(idx)), 0, 0.98)  # loop occupancy
        tti = (ff/np.clip(speed,5,None))                                 # travel time index
        los = los_from_vc(vc)
        frames.append(pd.DataFrame({
            "datetime": dstr,
            "date": dates,
            "hour": hours,
            "location_id": L.location_id,
            "road_code": L.road_code,
            "direction": L.direction,
            "volume_vph": np.round(vol).astype(int),
            "demand_vph": np.round(demand).astype(int),
            "avg_speed_kph": np.round(speed,1),
            "free_flow_speed_kph": ff,
            "vc_ratio": np.round(vc,3),
            "occupancy_pct": np.round(occ*100,1),
            "travel_time_index": np.round(tti,2),
            "level_of_service": los,
        }))
    df = pd.concat(frames, ignore_index=True)
    return df

# ---------------------------------------------------------------------------
# 5. SIGNALISED JUNCTIONS  (reference, timing plans, hourly performance)
# ---------------------------------------------------------------------------
JUNCTIONS = [
    # id, name, area, lat, lon, approaches, base_demand_per_approach (peak vph), control
    ("JCT_DEF","Defence Roundabout Signals","Trade Centre",25.2235,55.2845,4,1500,"SCOOT-adaptive"),
    ("JCT_SAFA","Al Safa Junction","Al Safa",25.1880,55.2520,4,1200,"SCOOT-adaptive"),
    ("JCT_WASL","Al Wasl / Al Hadiqa Junction","Al Wasl",25.1960,55.2440,4,1000,"Fixed-time"),
    ("JCT_OUD","Oud Metha Junction","Oud Metha",25.2350,55.3120,4,1100,"SCOOT-adaptive"),
    ("JCT_GARH","Al Garhoud Junction","Garhoud",25.2410,55.3460,4,1300,"SCOOT-adaptive"),
    ("JCT_MAMZ","Al Mamzar Junction","Al Mamzar",25.2940,55.3500,4,1400,"Fixed-time"),
    ("JCT_QUOZ","Al Quoz Junction","Al Quoz",25.1430,55.2330,3,900,"Fixed-time"),
    ("JCT_BARSHA","Al Barsha Junction","Al Barsha",25.1120,55.1980,4,1150,"SCOOT-adaptive"),
    ("JCT_KARAMA","Karama / Trade Centre Junction","Karama",25.2470,55.3040,4,1250,"SCOOT-adaptive"),
    ("JCT_DEIRA","Deira / Al Ittihad Junction","Deira",25.2710,55.3340,4,1350,"Fixed-time"),
]
JCT_COLS = ["junction_id","junction_name","area","latitude","longitude","num_approaches","peak_approach_demand_vph","control_type"]

def junctions_df():
    return pd.DataFrame(JUNCTIONS, columns=JCT_COLS)

# TOD programs: program, hours, cycle length, phase split character
TOD_PROGRAMS = [
    # program, start_h, end_h, cycle_s
    ("Early Morning", 0, 6, 70),
    ("AM Peak", 6, 10, 140),
    ("Midday", 10, 16, 100),
    ("PM Peak", 16, 20, 150),
    ("Evening", 20, 24, 90),
]
def program_for_hour(h):
    for name, s, e, c in TOD_PROGRAMS:
        if s <= h < e:
            return name, c
    return "Evening", 90

def build_signal_plans():
    """Static phasing plan: one row per junction x program x phase."""
    rows = []
    for J in JUNCTIONS:
        jid, jname, area, lat, lon, n_app, peak, ctrl = J
        for prog, s, e, cyc in TOD_PROGRAMS:
            # phases: NS through, NS left, EW through, EW left (4-phase) or 3-phase
            if n_app == 3:
                phases = [("P1","NS Through",0.42),("P2","EW Through",0.34),("P3","EW Left",0.24)]
            else:
                phases = [("P1","NS Through",0.34),("P2","NS Left",0.16),
                          ("P3","EW Through",0.34),("P4","EW Left",0.16)]
            yellow, allred = 3, 2
            lost = (yellow+allred)*len(phases)
            eff = cyc - lost
            for pid, mv, frac in phases:
                green = round(eff*frac)
                rows.append({
                    "junction_id": jid,
                    "junction_name": jname,
                    "program": prog,
                    "active_hours": f"{s:02d}:00-{e:02d}:00",
                    "cycle_length_s": cyc,
                    "phase_id": pid,
                    "movement": mv,
                    "green_s": green,
                    "yellow_s": yellow,
                    "all_red_s": allred,
                    "min_green_s": max(7, round(green*0.5)),
                    "max_green_s": round(green*1.6),
                    "coordination_offset_s": {"AM Peak":12,"PM Peak":18,"Midday":8}.get(prog,0),
                    "control_type": ctrl,
                })
    return pd.DataFrame(rows)

def webster_delay(cyc, g_ratio, x):
    # simplified Webster's average delay (s/veh)
    x = np.clip(x, 0, 1.25)
    term1 = 0.5*cyc*(1-g_ratio)**2 / np.clip(1 - np.minimum(x,0.99)*g_ratio, 0.05, None)
    term2 = np.where(x>0.5, 90*(x-0.5)**2, 0)  # oversaturation penalty
    return term1 + term2

def build_signal_perf(year, cal, weather):
    cal_y = cal[cal.year==year].set_index("date")
    wx = weather.set_index("datetime")
    idx = pd.date_range(f"{year}-01-01", f"{year}-12-31 23:00", freq="h")
    dates = idx.strftime("%Y-%m-%d").to_numpy()
    hours = idx.hour.to_numpy()
    months = idx.month.to_numpy()
    wd = idx.weekday.to_numpy()
    dstr = idx.strftime("%Y-%m-%d %H:%M:%S").to_numpy()
    uniq_dates = pd.unique(dates)
    is_we   = {d:int(cal_y.loc[d,"is_weekend"]) for d in uniq_dates}
    is_ram  = {d:int(cal_y.loc[d,"is_ramadan"]) for d in uniq_dates}
    is_hol  = {d:int(cal_y.loc[d,"is_public_holiday"]) for d in uniq_dates}
    wxy = wx.loc[dstr]
    w_cond = wxy["condition"].to_numpy(); w_vis = wxy["visibility_km"].to_numpy()
    wsf = weather_speed_factor(w_cond, w_vis*0+1, w_vis)  # use as delay degrade proxy

    frames=[]
    for J in JUNCTIONS:
        jid, jname, area, lat, lon, n_app, peak, ctrl = J
        adaptive = ctrl.startswith("SCOOT")
        g = GROWTH["core"][year]
        prog_name = np.empty(len(idx), dtype=object)
        cyc_arr = np.zeros(len(idx))
        for i,h in enumerate(hours):
            pn,cc = program_for_hour(h)
            prog_name[i]=pn; cyc_arr[i]=cc
        # approach demand profile (use commuter weekday/weekend profile)
        demand = np.zeros(len(idx))
        for d in uniq_dates:
            sel = dates==d
            h = hours[sel]; m = months[sel][0]; wday=wd[sel][0]
            we=is_we[d]; ram=is_ram[d]; hol=is_hol[d]
            p = hourly_profile("cin", bool(we), bool(ram), m)
            daily = peak/0.09 * g * MONTH_FACTOR[m] * dow_factor("cin", wday)  # back out daily from peak
            if ram: daily*=0.90
            if hol: daily*=0.55
            demand[sel] = daily*p[h]
        demand*=RNG.normal(1.0,0.06,len(idx))
        demand=np.clip(demand,0,None)
        # green ratio depends on program (more green to major in peak)
        g_ratio = np.where(np.isin(prog_name,["AM Peak","PM Peak"]),0.50,0.45)
        sat_flow = 1800*(n_app/2)  # rough lane capacity served per cycle stream
        x = demand/ (sat_flow*g_ratio)
        # adaptive signals shave saturation a bit
        if adaptive:
            x *= 0.90
        x = np.clip(x,0,1.4)
        delay = webster_delay(cyc_arr, g_ratio, x)
        # weather worsens delay
        delay = delay / np.clip(wsf,0.4,1.0)
        delay *= RNG.normal(1.0,0.05,len(idx))
        queue = np.round(np.clip(x* (cyc_arr/60.0) * (sat_flow/3600.0) * 1.4, 0, None)).astype(int)
        throughput = np.round(np.minimum(demand, sat_flow*g_ratio)).astype(int)
        phase_fail = np.where(x>1.0, RNG.integers(1,5,len(idx)), 0)
        ped = np.round(np.clip(RNG.normal(8,4,len(idx))*(1+ (np.isin(prog_name,["Midday","PM Peak"]).astype(int))),0,None)).astype(int)
        frames.append(pd.DataFrame({
            "datetime":dstr,"date":dates,"hour":hours,
            "junction_id":jid,"control_type":ctrl,
            "active_program":prog_name,"cycle_length_s":cyc_arr.astype(int),
            "approach_demand_vph":np.round(demand).astype(int),
            "degree_of_saturation":np.round(x,3),
            "avg_delay_s_per_veh":np.round(delay,1),
            "avg_queue_veh":queue,
            "throughput_vph":throughput,
            "phase_failures":phase_fail,
            "pedestrian_calls":ped,
            "adaptive_active":int(adaptive),
        }))
    return pd.concat(frames, ignore_index=True)

# ---------------------------------------------------------------------------
# 6. INCIDENTS  (event log; driven by volume, weather, time-of-day)
# ---------------------------------------------------------------------------
INC_TYPES = ["Vehicle Breakdown","Minor Accident","Major Accident","Debris on Road",
             "Vehicle Fire","Road Closure (Planned)","Flooding","Stalled Vehicle"]
INC_TYPE_P = [0.40,0.30,0.06,0.08,0.01,0.04,0.01,0.10]

def build_incidents(traffic_all, weather_all):
    wx = weather_all.set_index("datetime")
    locs = locations_df().set_index("location_id")
    rows=[]
    inc_id=1000
    # iterate per location-hour using traffic table (already has vc & datetime)
    t = traffic_all
    # join weather condition
    w = wx[["condition","visibility_km","precip_mm","temp_c"]]
    t = t.merge(w, left_on="datetime", right_index=True, how="left")
    vc = t["vc_ratio"].to_numpy()
    cond = t["condition"].to_numpy()
    vis = t["visibility_km"].to_numpy()
    hours = t["hour"].to_numpy()
    # base hourly incident rate per cell (calibrated to ~2,500-3,000 incidents
    # over the 3-year period across all count sites)
    base = 0.0085
    expo = (0.25 + vc**2.2)                       # more flow/congestion -> more incidents
    wmult = weather_incident_mult(cond, vis)
    tod = np.where((hours>=7)&(hours<=9),1.4, np.where((hours>=16)&(hours<=20),1.5, np.where((hours>=0)&(hours<=4),0.7,1.0)))
    lam = base*expo*wmult*tod
    counts = RNG.poisson(lam)
    sel_idx = np.where(counts>0)[0]
    dt = t["datetime"].to_numpy()
    loc = t["location_id"].to_numpy()
    precip = t["precip_mm"].to_numpy()
    for i in sel_idx:
        for _ in range(int(counts[i])):
            inc_id += 1
            ts = pd.Timestamp(dt[i])
            lid = loc[i]
            Lrow = locs.loc[lid]
            c = cond[i]
            # heavy rain/flood biases type toward accidents/flooding
            p = np.array(INC_TYPE_P, float)
            if c in ("Heavy Rain","Thunderstorm"):
                p = p*np.array([0.8,1.6,2.2,1.2,1.0,1.0,8.0,1.2]);
            if c=="Fog":
                p = p*np.array([0.9,1.8,2.5,1.0,1.0,1.0,0.2,1.1])
            p=p/p.sum()
            itype = RNG.choice(INC_TYPES, p=p)
            # severity & duration
            if itype=="Major Accident":
                sev="High"; dur=int(RNG.normal(95,35)); lanes=RNG.integers(2,4)
            elif itype=="Minor Accident":
                sev="Medium"; dur=int(RNG.normal(38,15)); lanes=RNG.integers(1,3)
            elif itype in ("Vehicle Breakdown","Stalled Vehicle"):
                sev="Low"; dur=int(RNG.normal(28,12)); lanes=1
            elif itype=="Flooding":
                sev="High"; dur=int(RNG.normal(180,90)); lanes=RNG.integers(2,Lrow.num_lanes+1)
            elif itype=="Road Closure (Planned)":
                sev="Medium"; dur=int(RNG.normal(240,120)); lanes=RNG.integers(1,Lrow.num_lanes+1)
            elif itype=="Vehicle Fire":
                sev="High"; dur=int(RNG.normal(70,30)); lanes=RNG.integers(1,3)
            else:
                sev="Low"; dur=int(RNG.normal(25,10)); lanes=1
            dur=max(5,dur)
            resp=int(np.clip(RNG.normal(9 if Lrow.profile_type!="frgt" else 13, 4),3,40))
            cleared = ts + pd.Timedelta(minutes=dur)
            rows.append({
                "incident_id": f"INC{inc_id}",
                "datetime_reported": ts.strftime("%Y-%m-%d %H:%M:%S"),
                "datetime_cleared": cleared.strftime("%Y-%m-%d %H:%M:%S"),
                "duration_min": dur,
                "location_id": lid,
                "road_code": Lrow.road_code,
                "road_name": Lrow.road_name,
                "area": Lrow.area,
                "direction": Lrow.direction,
                "latitude": round(Lrow.latitude + RNG.normal(0,0.002),5),
                "longitude": round(Lrow.longitude + RNG.normal(0,0.002),5),
                "incident_type": itype,
                "severity": sev,
                "lanes_blocked": int(lanes),
                "total_lanes": int(Lrow.num_lanes),
                "response_time_min": resp,
                "weather_condition": c,
                "precip_mm": float(precip[i]),
                "is_peak_hour": int((7<=ts.hour<=9) or (16<=ts.hour<=20)),
                "source": RNG.choice(["RTA Control Room","Police Report","CCTV Detection","Public Report (app)"],
                                     p=[0.45,0.2,0.2,0.15]),
            })
    # ---- Inject the historic 16 Apr 2024 storm cluster (city-wide flooding) ----
    storm_plan = [  # (date, hour_start, hour_end, n_incidents)
        (date(2024,4,15), 18, 23, 10),
        (date(2024,4,16), 0, 23, 55),
        (date(2024,4,17), 0, 20, 28),
    ]
    loc_ids = list(locs.index)
    for sd, h0, h1, n in storm_plan:
        for _ in range(n):
            inc_id += 1
            lid = RNG.choice(loc_ids)
            Lrow = locs.loc[lid]
            hr = int(RNG.integers(h0, h1+1))
            mn = int(RNG.integers(0,60))
            ts = pd.Timestamp(f"{sd.isoformat()} {hr:02d}:{mn:02d}:00")
            itype = RNG.choice(
                ["Flooding","Road Closure (Planned)","Major Accident","Minor Accident","Stalled Vehicle","Vehicle Breakdown"],
                p=[0.40,0.22,0.10,0.12,0.10,0.06])
            if itype=="Flooding":
                sev="High"; dur=int(RNG.normal(300,140)); lanes=int(RNG.integers(2,Lrow.num_lanes+1))
            elif itype=="Road Closure (Planned)":
                sev="High"; dur=int(RNG.normal(360,150)); lanes=int(Lrow.num_lanes)
            elif itype=="Major Accident":
                sev="High"; dur=int(RNG.normal(120,50)); lanes=int(RNG.integers(2,4))
            elif itype=="Minor Accident":
                sev="Medium"; dur=int(RNG.normal(55,25)); lanes=int(RNG.integers(1,3))
            else:
                sev="Medium"; dur=int(RNG.normal(60,30)); lanes=1
            dur=max(20,dur)
            resp=int(np.clip(RNG.normal(28,12),8,90))   # response badly delayed in the storm
            cleared=ts+pd.Timedelta(minutes=dur)
            rows.append({
                "incident_id": f"INC{inc_id}",
                "datetime_reported": ts.strftime("%Y-%m-%d %H:%M:%S"),
                "datetime_cleared": cleared.strftime("%Y-%m-%d %H:%M:%S"),
                "duration_min": dur, "location_id": lid,
                "road_code": Lrow.road_code, "road_name": Lrow.road_name,
                "area": Lrow.area, "direction": Lrow.direction,
                "latitude": round(Lrow.latitude+RNG.normal(0,0.002),5),
                "longitude": round(Lrow.longitude+RNG.normal(0,0.002),5),
                "incident_type": itype, "severity": sev,
                "lanes_blocked": lanes, "total_lanes": int(Lrow.num_lanes),
                "response_time_min": resp,
                "weather_condition": "Thunderstorm" if sd==date(2024,4,16) else "Heavy Rain",
                "precip_mm": float(RNG.uniform(20,60)),
                "is_peak_hour": int((7<=hr<=9) or (16<=hr<=20)),
                "source": RNG.choice(["RTA Control Room","Police Report","CCTV Detection","Public Report (app)"],
                                     p=[0.5,0.2,0.15,0.15]),
            })

    df = pd.DataFrame(rows).sort_values("datetime_reported").reset_index(drop=True)
    return df

def apply_incident_speed_penalty(traffic_all, incidents):
    """Depress speed (and slightly volume) on location-hours overlapping a
    lane-blocking incident. Vectorised via per-(location,hour) penalty maps that
    keep the WORST overlapping penalty."""
    if incidents.empty:
        return traffic_all
    spd_pen = {}   # (location_id, datetime_str) -> min speed multiplier
    vol_pen = {}   # (location_id, datetime_str) -> min volume multiplier
    for r in incidents.itertuples(index=False):
        start = pd.Timestamp(r.datetime_reported).floor("h")
        end = pd.Timestamp(r.datetime_cleared)
        frac_blocked = r.lanes_blocked / max(r.total_lanes, 1)
        s_mult = 1 - min(0.75, 0.15 + frac_blocked*0.6)
        v_mult = 1 - frac_blocked*0.3
        h = start
        while h <= end:
            key = (r.location_id, h.strftime("%Y-%m-%d %H:%M:%S"))
            if key not in spd_pen or s_mult < spd_pen[key]:
                spd_pen[key] = s_mult
            if key not in vol_pen or v_mult < vol_pen[key]:
                vol_pen[key] = v_mult
            h += pd.Timedelta(hours=1)
    keys = list(zip(traffic_all["location_id"], traffic_all["datetime"]))
    sfac = np.array([spd_pen.get(k, 1.0) for k in keys])
    vfac = np.array([vol_pen.get(k, 1.0) for k in keys])
    traffic_all = traffic_all.copy()
    traffic_all["avg_speed_kph"] = np.round(np.clip(traffic_all["avg_speed_kph"].to_numpy()*sfac, 4, None), 1)
    traffic_all["volume_vph"] = np.round(traffic_all["volume_vph"].to_numpy()*vfac).astype(int)
    # recompute dependent fields where speed changed
    ff = traffic_all["free_flow_speed_kph"].to_numpy()
    traffic_all["travel_time_index"] = np.round(ff/np.clip(traffic_all["avg_speed_kph"].to_numpy(),4,None), 2)
    traffic_all["incident_affected"] = (sfac < 1.0).astype(int)
    return traffic_all

# ---------------------------------------------------------------------------
# 7. SALIK TOLL GATES (hourly crossings + dynamic pricing from 2025-01-31)
# ---------------------------------------------------------------------------
SALIK_GATES = [
    # id, name, lat, lon, peak_hourly_crossings, profile
    ("SLK_GARHOUD","Al Garhoud Bridge",25.2330,55.3300,6500,"cin"),
    ("SLK_MAKTOUM","Al Maktoum Bridge",25.2400,55.3170,5200,"cin"),
    ("SLK_BARSHA","Al Barsha (SZR @ MoE)",25.1180,55.2000,7800,"cout"),
    ("SLK_SAFA","Al Safa (SZR)",25.1880,55.2520,7200,"cin"),
    ("SLK_AIRTUN","Airport Tunnel",25.2470,55.3530,4800,"mix"),
    ("SLK_MAMZAR","Al Mamzar",25.2950,55.3550,6000,"cin"),
    ("SLK_JEBALI","Jebel Ali",25.0100,55.1300,4200,"frgt"),
]
def salik_toll_rate(ts):
    """AED per crossing. Flat 4 until 30 Jan 2025; then dynamic pricing."""
    if ts.date() < date(2025,1,31):
        return 4
    h = ts.hour
    if 1 <= h < 6:
        return 0          # free overnight window
    if (6 <= h < 10) or (16 <= h < 20):
        return 6          # peak
    return 4              # off-peak

def build_salik(year, cal, weather):
    cal_y = cal[cal.year==year].set_index("date")
    idx = pd.date_range(f"{year}-01-01", f"{year}-12-31 23:00", freq="h")
    dates = idx.strftime("%Y-%m-%d").to_numpy(); hours=idx.hour.to_numpy()
    months=idx.month.to_numpy(); wd=idx.weekday.to_numpy()
    dstr=idx.strftime("%Y-%m-%d %H:%M:%S").to_numpy()
    uniq=pd.unique(dates)
    is_we={d:int(cal_y.loc[d,"is_weekend"]) for d in uniq}
    is_ram={d:int(cal_y.loc[d,"is_ramadan"]) for d in uniq}
    is_hol={d:int(cal_y.loc[d,"is_public_holiday"]) for d in uniq}
    frames=[]
    for gid,name,lat,lon,peak,prof in SALIK_GATES:
        g=GROWTH["core"][year]
        cross=np.zeros(len(idx))
        for d in uniq:
            sel=dates==d; h=hours[sel]; m=months[sel][0]; wday=wd[sel][0]
            we=is_we[d]; ram=is_ram[d]; hol=is_hol[d]
            p=hourly_profile(prof,bool(we),bool(ram),m)
            daily=peak/0.09*g*MONTH_FACTOR[m]*dow_factor(prof,wday)
            if ram: daily*=0.90
            if hol: daily*=0.5
            cross[sel]=daily*p[h]
        cross*=RNG.normal(1.0,0.05,len(idx))
        cross=np.round(np.clip(cross,0,None)).astype(int)
        rate=np.array([salik_toll_rate(pd.Timestamp(x)) for x in dstr])
        rev=cross*rate
        frames.append(pd.DataFrame({
            "datetime":dstr,"date":dates,"hour":hours,
            "gate_id":gid,"gate_name":name,"latitude":lat,"longitude":lon,
            "crossings":cross,"toll_rate_aed":rate,"revenue_aed":rev,
        }))
    return pd.concat(frames,ignore_index=True)

# ---------------------------------------------------------------------------
# 8. METRO RIDERSHIP (daily, Red & Green lines)
# ---------------------------------------------------------------------------
def build_metro(cal, weather):
    wd_day = weather.groupby("date").agg(
        precip_mm=("precip_mm","sum"),
        max_condition=("condition", lambda s: "Heavy Rain" if (s=="Heavy Rain").any() or (s=="Thunderstorm").any() else "Normal")
    ).reset_index()
    rows=[]
    lines=[("Red Line",560000),("Green Line",230000)]
    for _,c in cal.iterrows():
        d=pd.Timestamp(c.date)
        g=GROWTH["core"][d.year]
        wf=1.0
        wrow=wd_day[wd_day.date==c.date]
        rain=float(wrow.precip_mm.iloc[0]) if len(wrow) else 0
        if rain>20: wf=1.15        # heavy rain pushes riders to metro
        elif rain>5: wf=1.06
        dow_m = {0:1.0,1:1.03,2:1.04,3:1.02,4:0.92,5:0.85,6:0.80}[d.weekday()]
        if c.is_weekend and c.is_dsf: dow_m*=1.18   # weekend DSF leisure trips
        for line,base in lines:
            r=base*g*MONTH_FACTOR[d.month]*dow_m*wf
            if c.is_ramadan: r*=0.88
            if c.is_public_holiday: r*=0.7
            r*=RNG.normal(1.0,0.04)
            rows.append({"date":c.date,"line":line,"ridership":int(max(0,r)),
                         "is_weekend":c.is_weekend,"is_public_holiday":c.is_public_holiday,
                         "is_ramadan":c.is_ramadan,"rain_mm":round(rain,1)})
    return pd.DataFrame(rows)

# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main():
    import os
    os.makedirs(OUT, exist_ok=True)
    print("Building calendar ...")
    cal = build_calendar()
    cal.to_csv(f"{OUT}/calendar_context.csv", index=False)

    print("Building locations & junction reference ...")
    locations_df().to_csv(f"{OUT}/locations_reference.csv", index=False)
    junctions_df().to_csv(f"{OUT}/signal_junctions_reference.csv", index=False)
    build_signal_plans().to_csv(f"{OUT}/signal_timing_plans.csv", index=False)

    weather_years={}
    traffic_years={}
    for y in YEARS:
        print(f"Building weather {y} ...")
        wx=build_weather(y, cal); weather_years[y]=wx
        wx.to_csv(f"{OUT}/weather_hourly_{y}.csv", index=False)
    weather_all=pd.concat(weather_years.values(), ignore_index=True)

    for y in YEARS:
        print(f"Building traffic volume/speed {y} ...")
        t=build_traffic(y, cal, weather_years[y]); traffic_years[y]=t
    traffic_all=pd.concat(traffic_years.values(), ignore_index=True)

    print("Building incidents (whole period) ...")
    incidents=build_incidents(traffic_all, weather_all)
    incidents.to_csv(f"{OUT}/incidents_log.csv", index=False)

    print("Applying incident speed penalties back to traffic ...")
    traffic_all=apply_incident_speed_penalty(traffic_all, incidents)
    for y in YEARS:
        sub=traffic_all[traffic_all["datetime"].str.startswith(str(y))]
        sub.to_csv(f"{OUT}/traffic_volume_hourly_{y}.csv", index=False)

    for y in YEARS:
        print(f"Building signal performance {y} ...")
        build_signal_perf(y, cal, weather_years[y]).to_csv(f"{OUT}/signal_performance_hourly_{y}.csv", index=False)

    for y in YEARS:
        print(f"Building Salik toll {y} ...")
        build_salik(y, cal, weather_years[y]).to_csv(f"{OUT}/salik_toll_hourly_{y}.csv", index=False)

    print("Building metro ridership ...")
    build_metro(cal, weather_all).to_csv(f"{OUT}/metro_ridership_daily.csv", index=False)

    print("\nDONE. Files in ./datasets")

if __name__ == "__main__":
    main()
