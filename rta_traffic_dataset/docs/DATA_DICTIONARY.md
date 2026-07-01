# Data Dictionary

All times are **local Dubai time (UTC+4, no daylight saving)**. `datetime` columns are
`YYYY-MM-DD HH:MM:SS` and represent the **start of the hour** (e.g. `08:00:00` = 08:00–09:00).
Join keys: `location_id`, `junction_id`, `gate_id`, `date`, `datetime`.

---

## 1. `locations_reference.csv` — 18 traffic count sites
| Column | Type | Description |
|---|---|---|
| `location_id` | str | Primary key, e.g. `SZR_N1`. Used by traffic & incident files. |
| `location_name` | str | Human-readable site name. |
| `road_code` | str | Official road number (E11, E44, E311, E611, D89…). |
| `road_name` | str | Road name (Sheikh Zayed Road, Al Khail Road…). |
| `area` | str | Dubai district. |
| `direction` | str | Travel direction sampled at this site. |
| `num_lanes` | int | Lanes in that direction. |
| `free_flow_speed_kph` | int | Speed under light traffic. |
| `speed_limit_kph` | int | Posted limit. |
| `capacity_vph` | int | Practical capacity (vehicles/hour) in that direction. |
| `aadt_per_direction` | int | Annual Average Daily Traffic (directional) — the design baseline. |
| `profile_type` | str | Demand shape: `cin` (commuter inbound/AM-heavy), `cout` (commuter outbound/PM-heavy), `mix`, `leis` (leisure), `frgt` (freight). |
| `latitude`,`longitude` | float | Approx coordinates. |
| `growth_key` | str | Which year-on-year growth curve applies (`core`, `south`, `expo`). |

## 2. `traffic_volume_hourly_YYYY.csv` — the core dataset (hourly × 18 sites)
| Column | Type | Description |
|---|---|---|
| `datetime` | datetime | Hour start (local). |
| `date` | date | Calendar date. |
| `hour` | int | 0–23. |
| `location_id` | str | FK → `locations_reference`. |
| `road_code`,`direction` | str | Denormalised for convenience. |
| `volume_vph` | int | **Observed vehicles that passed** in the hour (throughput; saturates near capacity). |
| `demand_vph` | int | **Demand** (vehicles that *wanted* to pass) — can exceed `volume_vph` in congestion. |
| `avg_speed_kph` | float | Mean speed in the hour (reflects congestion, weather, incidents). |
| `free_flow_speed_kph` | int | Reference speed for this site. |
| `vc_ratio` | float | `volume / capacity`. >0.9 = heavy congestion, >1.0 = oversaturated. |
| `occupancy_pct` | float | Loop-detector style occupancy %. |
| `travel_time_index` | float | `free_flow_speed / avg_speed`. 1.0 = free flow, 2.0 = twice as long. |
| `level_of_service` | str | A (free) → F (gridlock), from `vc_ratio`. |
| `incident_affected` | int | 1 if a lane-blocking incident overlapped this site-hour (depresses speed). |

## 3. `signal_junctions_reference.csv` — 10 signalised junctions
| Column | Type | Description |
|---|---|---|
| `junction_id` | str | Primary key, e.g. `JCT_DEF`. |
| `junction_name`,`area` | str | Location. |
| `latitude`,`longitude` | float | Coordinates. |
| `num_approaches` | int | 3 or 4 legs. |
| `peak_approach_demand_vph` | int | Typical peak demand per approach. |
| `control_type` | str | `SCOOT-adaptive` or `Fixed-time`. |

## 4. `signal_timing_plans.csv` — static phasing (junction × time-of-day program × phase)
| Column | Type | Description |
|---|---|---|
| `junction_id` | str | FK → junctions. |
| `program` | str | Time-of-day plan: Early Morning, AM Peak, Midday, PM Peak, Evening. |
| `active_hours` | str | When the program runs (e.g. `06:00-10:00`). |
| `cycle_length_s` | int | Full signal cycle (s). Longer in peaks (140–150), shorter off-peak (70–100). |
| `phase_id` | str | P1…P4. |
| `movement` | str | NS Through, NS Left, EW Through, EW Left. |
| `green_s` | int | Green time for this phase. |
| `yellow_s`,`all_red_s` | int | Inter-green clearance. |
| `min_green_s`,`max_green_s` | int | Bounds an adaptive controller may move within. |
| `coordination_offset_s` | int | Green-wave offset vs upstream junction. |
| `control_type` | str | Adaptive or fixed. |

## 5. `signal_performance_hourly_YYYY.csv` — operations (hourly × 10 junctions)
| Column | Type | Description |
|---|---|---|
| `datetime`,`date`,`hour` | — | Hour start. |
| `junction_id` | str | FK → junctions. |
| `control_type` | str | Adaptive / fixed. |
| `active_program` | str | Which TOD plan was running. |
| `cycle_length_s` | int | Cycle in force that hour. |
| `approach_demand_vph` | int | Demand arriving at the junction. |
| `degree_of_saturation` | float | `x` = demand / capacity served. >1.0 = the junction is failing. |
| `avg_delay_s_per_veh` | float | Average control delay (Webster-style). |
| `avg_queue_veh` | int | Typical standing queue length. |
| `throughput_vph` | int | Vehicles actually discharged. |
| `phase_failures` | int | Cycles where the queue didn't clear (only when oversaturated). |
| `pedestrian_calls` | int | Pedestrian crossing demands. |
| `adaptive_active` | int | 1 if the junction runs adaptive control. |

## 6. `incidents_log.csv` — event log (one row per incident)
| Column | Type | Description |
|---|---|---|
| `incident_id` | str | Primary key, `INC####`. |
| `datetime_reported` | datetime | When logged. |
| `datetime_cleared` | datetime | When cleared. |
| `duration_min` | int | Minutes blocked. |
| `location_id` | str | FK → `locations_reference`. |
| `road_code`,`road_name`,`area`,`direction` | str | Denormalised location. |
| `latitude`,`longitude` | float | Incident point (jittered around the site). |
| `incident_type` | str | Vehicle Breakdown, Minor/Major Accident, Debris on Road, Vehicle Fire, Road Closure (Planned), Flooding, Stalled Vehicle. |
| `severity` | str | Low / Medium / High. |
| `lanes_blocked` / `total_lanes` | int | Blockage extent. |
| `response_time_min` | int | Time to first responder (worse in storms / on freight roads). |
| `weather_condition` | str | Condition at the time. |
| `precip_mm` | float | Rain at the time. |
| `is_peak_hour` | int | 1 if within AM/PM peak. |
| `source` | str | RTA Control Room / Police Report / CCTV Detection / Public Report (app). |

## 7. `weather_hourly_YYYY.csv` — hourly weather (city-wide)
| Column | Type | Description |
|---|---|---|
| `datetime`,`date`,`hour` | — | Hour start. |
| `temp_c` | float | Air temperature (°C). |
| `humidity_pct` | int | Relative humidity. |
| `wind_kph` | float | Wind speed. |
| `visibility_km` | float | Visibility (drops in fog/dust/rain). |
| `precip_mm` | float | Rainfall in the hour. |
| `condition` | str | Clear, Sunny, Partly Cloudy, Hazy, Fog, Light Rain, Heavy Rain, Thunderstorm, Dust/Sandstorm. |

## 8. `salik_toll_hourly_YYYY.csv` — toll gates (hourly × 7 gates)
| Column | Type | Description |
|---|---|---|
| `datetime`,`date`,`hour` | — | Hour start. |
| `gate_id`,`gate_name` | str | Salik gate. |
| `latitude`,`longitude` | float | Gate location. |
| `crossings` | int | Vehicles through the gate that hour. |
| `toll_rate_aed` | int | Charge per crossing. **Flat AED 4 until 30 Jan 2025**; from **31 Jan 2025** dynamic: AED 6 peak (06–10, 16–20), AED 4 off-peak, **AED 0 between 01:00–06:00**. |
| `revenue_aed` | int | `crossings × toll_rate_aed`. |

## 9. `metro_ridership_daily.csv` — Metro (daily × 2 lines)
| Column | Type | Description |
|---|---|---|
| `date` | date | Day. |
| `line` | str | Red Line / Green Line. |
| `ridership` | int | Daily passengers. |
| `is_weekend`,`is_public_holiday`,`is_ramadan` | int | Flags. |
| `rain_mm` | float | Day's rainfall (rain pushes riders onto the Metro). |

## 10. `calendar_context.csv` — daily context / feature store
| Column | Type | Description |
|---|---|---|
| `date` | date | Day. |
| `year`,`month`,`day` | int | Parts. |
| `day_of_week` | str | Monday…Sunday. |
| `is_weekend` | int | 1 for **Saturday & Sunday** (UAE weekend). |
| `is_public_holiday` | int | 1 on a UAE public holiday. |
| `holiday_name` | str | e.g. Eid Al Fitr, UAE National Day. |
| `is_ramadan` | int | 1 during Ramadan. |
| `school_status` | str | In Session / Summer Break / Winter Break / Spring Break. |
| `is_dsf` | int | 1 during Dubai Shopping Festival window. |
| `rain_event` | str | Label if a notable rain event occurred. |
| `rain_severity` | int | 0–5. |
| `dust_severity` | int | 0–3. |

---

### Notes on realism / modelling
- **Speeds** come from a BPR speed-flow curve (speed falls as `vc_ratio` rises), then multiplied
  by weather and incident factors.
- **Signal delay** uses a simplified Webster delay formula with an oversaturation penalty.
- Files are split by year only to keep each CSV a manageable size; schemas are identical across years.
- Everything is reproducible from `scripts/generate_data.py` (RNG seed = 42).
