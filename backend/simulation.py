"""
FlowSync Simulation Engine
Replays historical RTA data as time-slice "frames" for the frontend.
Produces both baseline (raw data) and optimized (Mistral-enhanced) views.
"""

import pandas as pd
import numpy as np
from typing import Optional
from data_loader import RTADataloader


class SimulationEngine:
    """Generates simulation frames from RTA dataset."""

    def __init__(self, data_loader: RTADataloader):
        self.loader = data_loader
        self._traffic = None
        self._signals = None
        self._weather = None
        self._locations = None
        self._junctions = None
        self._incidents = None
        self._plans = None

    def _ensure_loaded(self):
        if self._traffic is None:
            self._traffic = self.loader.traffic_volume
            self._signals = self.loader.signal_performance
            self._weather = self.loader.weather
            self._locations = self.loader.locations
            self._junctions = self.loader.junctions
            self._incidents = self.loader.incidents
            self._plans = self.loader.signal_plans

    def get_frame(self, dt_str: str) -> dict:
        """
        Generate a single simulation frame for a given datetime.
        Returns baseline (raw) data for that time-slice.
        """
        self._ensure_loaded()
        dt = pd.Timestamp(dt_str)

        # Traffic volume for this hour
        traffic_rows = self._traffic[self._traffic["datetime"] == dt]
        # Signal performance for this hour
        signal_rows = self._signals[self._signals["datetime"] == dt]
        # Weather
        weather_rows = self._weather[self._weather["datetime"] == dt]
        # Active incidents
        incident_mask = (self._incidents["datetime_reported"] <= dt) & \
                        (self._incidents["datetime_cleared"] >= dt)
        active_incidents = self._incidents[incident_mask]

        # Build location features with coordinates
        location_features = []
        for _, loc in self._locations.iterrows():
            loc_traffic = traffic_rows[traffic_rows["location_id"] == loc["location_id"]]
            if len(loc_traffic) > 0:
                row = loc_traffic.iloc[0]
                volume = int(row["volume_vph"])
                speed = float(row["avg_speed_kph"])
                vc = float(row["vc_ratio"])
                los = row["level_of_service"]
                occupancy = float(row["occupancy_pct"])
                demand = int(row["demand_vph"])
            else:
                # No data for this hour — fall back to location reference capacity
                row = None
                volume = 0
                speed = int(loc["free_flow_speed_kph"])
                vc = 0.0
                los = "A"
                occupancy = 0.0
                demand = 0

            capacity = int(loc["capacity_vph"])
            free_flow = int(loc["free_flow_speed_kph"])

            # Determine congestion level
            if vc > 0.85:
                congestion = "critical"
                color = "#dc2626"  # red
            elif vc > 0.7:
                congestion = "heavy"
                color = "#f97316"  # orange
            elif vc > 0.5:
                congestion = "moderate"
                color = "#eab308"  # yellow
            else:
                congestion = "free_flow"
                color = "#10b981"  # green

            location_features.append({
                "location_id": loc["location_id"],
                "name": loc["location_name"],
                "road": loc["road_name"],
                "area": loc["area"],
                "direction": loc["direction"],
                "latitude": float(loc["latitude"]),
                "longitude": float(loc["longitude"]),
                "num_lanes": int(loc["num_lanes"]),
                "capacity_vph": capacity,
                "free_flow_speed": free_flow,
                "volume_vph": volume,
                "demand_vph": demand,
                "avg_speed_kph": speed,
                "vc_ratio": vc,
                "occupancy_pct": occupancy,
                "level_of_service": los,
                "congestion": congestion,
                "color": color,
            })

        # Build junction features
        junction_features = []
        for _, junc in self._junctions.iterrows():
            junc_signal = signal_rows[signal_rows["junction_id"] == junc["junction_id"]]
            if len(junc_signal) > 0:
                row = junc_signal.iloc[0]
                saturation = float(row["degree_of_saturation"])
                delay = float(row["avg_delay_s_per_veh"])
                queue = float(row["avg_queue_veh"])
                throughput = int(row["throughput_vph"])
                phase_failures = int(row["phase_failures"])
                cycle = int(row["cycle_length_s"])
                program = row["active_program"]
                control = row["control_type"]
                adaptive = bool(row["adaptive_active"])
            else:
                saturation = 0.0
                delay = 0.0
                queue = 0.0
                throughput = 0
                phase_failures = 0
                cycle = 100
                program = "Unknown"
                control = junc["control_type"]
                adaptive = "adaptive" in control.lower()

            # Get timing plan for this junction + program
            plan_rows = self._plans[
                (self._plans["junction_id"] == junc["junction_id"]) &
                (self._plans["program"] == program)
            ]
            phases = []
            for _, p in plan_rows.iterrows():
                phases.append({
                    "phase_id": p["phase_id"],
                    "movement": p["movement"],
                    "green_s": int(p["green_s"]),
                    "yellow_s": int(p["yellow_s"]),
                    "all_red_s": int(p["all_red_s"]),
                    "min_green_s": int(p["min_green_s"]),
                    "max_green_s": int(p["max_green_s"]),
                })

            junction_features.append({
                "junction_id": junc["junction_id"],
                "name": junc["junction_name"],
                "area": junc["area"],
                "latitude": float(junc["latitude"]),
                "longitude": float(junc["longitude"]),
                "num_approaches": int(junc["num_approaches"]),
                "control_type": control,
                "active_program": program,
                "cycle_length_s": cycle,
                "degree_of_saturation": saturation,
                "avg_delay_s_per_veh": delay,
                "avg_queue_veh": queue,
                "throughput_vph": throughput,
                "phase_failures": phase_failures,
                "adaptive_active": adaptive,
                "phases": phases,
            })

        # Weather
        weather = {}
        if len(weather_rows) > 0:
            w = weather_rows.iloc[0]
            weather = {
                "temp_c": float(w["temp_c"]),
                "humidity_pct": float(w["humidity_pct"]),
                "wind_kph": float(w["wind_kph"]),
                "visibility_km": float(w["visibility_km"]),
                "precip_mm": float(w["precip_mm"]),
                "condition": w["condition"],
            }
        else:
            weather = {"temp_c": 25, "humidity_pct": 50, "wind_kph": 10,
                       "visibility_km": 10, "precip_mm": 0, "condition": "Clear"}

        # Incidents
        incident_list = []
        for _, inc in active_incidents.iterrows():
            incident_list.append({
                "incident_id": inc["incident_id"],
                "type": inc["incident_type"],
                "severity": inc["severity"],
                "road": inc["road_name"],
                "area": inc["area"],
                "latitude": float(inc["latitude"]),
                "longitude": float(inc["longitude"]),
                "lanes_blocked": int(inc["lanes_blocked"]),
                "duration_min": int(inc["duration_min"]),
            })

        # Aggregate metrics
        total_volume = sum(lf["volume_vph"] for lf in location_features)
        avg_speed = np.mean([lf["avg_speed_kph"] for lf in location_features]) if location_features else 0
        avg_vc = np.mean([lf["vc_ratio"] for lf in location_features]) if location_features else 0
        critical_count = sum(1 for lf in location_features if lf["congestion"] == "critical")
        heavy_count = sum(1 for lf in location_features if lf["congestion"] == "heavy")
        total_delay = sum(jf["avg_delay_s_per_veh"] * jf["throughput_vph"] / max(jf["throughput_vph"], 1)
                          for jf in junction_features)
        total_queue = sum(jf["avg_queue_veh"] for jf in junction_features)
        total_phase_failures = sum(jf["phase_failures"] for jf in junction_features)

        return {
            "timestamp": dt_str,
            "hour": int(dt.hour),
            "day_of_week": dt.day_name(),
            "locations": location_features,
            "junctions": junction_features,
            "weather": weather,
            "incidents": incident_list,
            "metrics": {
                "total_volume_vph": total_volume,
                "avg_speed_kph": round(float(avg_speed), 1),
                "avg_vc_ratio": round(float(avg_vc), 3),
                "critical_locations": critical_count,
                "heavy_locations": heavy_count,
                "total_delay_s": round(float(total_delay), 1),
                "total_queue_veh": round(float(total_queue), 1),
                "phase_failures": total_phase_failures,
                "active_incidents": len(incident_list),
            },
        }

    def get_available_dates(self) -> list:
        """Return list of unique dates in the dataset."""
        self._ensure_loaded()
        dates = sorted(self._traffic["date"].unique().tolist())
        return [str(d) for d in dates]

    def get_available_hours(self, date_str: str) -> list:
        """Return list of hours available for a given date."""
        self._ensure_loaded()
        day_data = self._traffic[self._traffic["date"] == date_str]
        hours = sorted(day_data["hour"].unique().tolist())
        return [int(h) for h in hours]


# Singleton
engine = SimulationEngine(RTADataloader())
