# Patterns & "Answer Key" — for Mentors & Judges (not for hand-out)

This note documents the structure deliberately built into the synthetic data, so mentors can
steer teams and judges can recognise strong insight. None of this is random noise — every pattern
below is reproducible and discoverable from the CSVs.

> Keep this doc for the organising team. Students should *discover* these; that's the exercise.

---

## A. Temporal patterns (the bread and butter)

| Pattern | Where to see it | Expected signature |
|---|---|---|
| **AM peak** | `traffic_volume_hourly_*`, inbound sites (`SZR_N1`, `ITT_W1`, `AIR_W1`) | 07:00–09:00, `vc_ratio`→~1.0, speed on SZR_N1 falls from ~105 to ~60 kph |
| **PM peak** | outbound sites (`SZR_S1`, `EKR_S1`, `ITT_E1`) | 17:00–20:00 surge |
| **UAE weekend** | any commuter site, group by `day_of_week` | Sat & Sun ~20% below mid-week; Friday a notch lower than Tue–Wed |
| **Leisure inversion** | `JBR_X1` (Jumeirah Beach Rd) | Higher on weekends/evenings — opposite of commuter corridors |
| **Freight flatness** | `MBZ_E1`, `EMR_E1` | Flatter all-day profile, lower weekend drop, dips hardest on holidays |

## B. Seasonal & cultural

| Pattern | Where | Signature |
|---|---|---|
| **Summer lull** | monthly mean volume | Jun–Aug ~12–15% below cool-season; cool season Oct–Mar peaks |
| **Ramadan** | `is_ramadan` days (2023 Mar23–Apr20 · 2024 Mar11–Apr9 · 2025 Mar1–29) | Daytime dip, sharp **pre-iftar surge ~17:00–18:00**, near-empty roads at iftar, busy 21:00–01:00 |
| **Public holidays** | `is_public_holiday` | Commuter volume collapses ~45%; leisure & Metro patterns shift |
| **School breaks** | `school_status` | Lighter AM peaks in Summer Break |

## C. Year-on-year growth (trend)

- Overall traffic **+~6%/yr** (2023 → 2025). Mean `volume_vph`: ~3,320 → ~3,535 → ~3,745.
- **Expo / Dubai South corridor (`DWC_X1`)** grows **~20%/yr** — the fastest-growing site, reflecting
  Dubai South / Expo legacy development. A team doing trend analysis should single this out.

## D. Weather coupling

- Rain/fog **cut speeds** (Heavy Rain ×0.70, Thunderstorm ×0.55, Fog ×0.78) and **multiply incident
  risk** (Heavy Rain ×6, Thunderstorm ×9, Fog ×4).
- **Winter-morning fog** (Nov–Mar, 03:00–08:00) on scattered days → low `visibility_km`, speed dips, incident bumps.
- Heavy rain days show **Metro ridership rising** (mode shift) while road volume dips.

## E. The two marquee "discoverable events" (great for demos)

1. **16 April 2024 — historic Dubai rainstorm / flooding.**
   - `incidents_log`: **~60 incidents on 16 Apr + ~35 on 17 Apr** (by far the top days; mostly Flooding /
     Road Closure / accidents, High severity, long durations, **delayed response times ~28 min**).
   - `traffic_volume_hourly_2024`: speeds collapse city-wide that day (SZR_N1 daily-mean ~78 vs ~96 kph normal).
   - `weather_hourly_2024`: `Thunderstorm`, `precip_mm` spikes (peak day total ~160 mm).
   - `metro_ridership_daily`: Red Line jumps to ~680k (vs ~490k normal) — mode shift to rail.
   - Cross-dataset storytelling here is a strong differentiator for a winning pitch.

2. **31 January 2025 — RTA dynamic Salik tolling begins.**
   - `salik_toll_hourly_*`: `toll_rate_aed` is flat **4** for all of 2023–2024 and Jan 2025, then becomes
     **6 (peak) / 4 (off-peak) / 0 (01:00–06:00)** from 31 Jan 2025.
   - Revenue per crossing rises in peaks; a business/marketing team can analyse congestion-pricing impact.

## F. Signal-control insights (for the Adaptive Signal Control direction)

- `signal_performance_hourly_*`: `avg_delay_s_per_veh` and `degree_of_saturation` are **worst in AM/PM
  peaks** (mean delay ~24–25 s vs ~11 s early morning). `phase_failures` only appear when `x > 1.0`.
- **Adaptive (SCOOT) junctions** run a little better than **fixed-time** ones at equal demand
  (lower mean delay). Junctions `JCT_WASL`, `JCT_MAMZ`, `JCT_QUOZ`, `JCT_DEIRA` are fixed-time — prime
  candidates for a student "retime these" proposal.
- The static green splits in `signal_timing_plans` can be compared against realised saturation to argue
  for re-allocating green time.

## G. Routing insights (for the Smart Routing direction)

- Three **Creek crossings** (`GAR_N1` Garhoud, `MAK_N1` Maktoum, `BBC_S1` Business Bay) carry overlapping
  demand — when one is congested or has an incident, a router should shift to the others.
- `incident_affected = 1` rows mark where a live incident is suppressing speed — exactly the signal a
  routing engine should react to.

## H. Good evaluation "tells" (what strong teams will surface)

- Joins across ≥3 datasets (e.g. traffic × weather × calendar) rather than one table in isolation.
- Explicitly handling the **Sat–Sun weekend** and **Ramadan** instead of a generic Mon–Fri assumption.
- Treating `demand_vph` vs `volume_vph` correctly (oversaturation ≠ throughput).
- Forecasting that degrades gracefully on the **April 2024 anomaly** — or flags it as an outlier.
- A business case that uses the **Salik pricing change** or **incident response times** for ROI.

---

*All values reproducible from `scripts/generate_data.py` (seed = 42). If you regenerate with a
different seed, the qualitative patterns hold but exact counts shift.*
