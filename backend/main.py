"""
FlowSync API — FastAPI Backend
Serves simulation frames from RTA dataset with Mistral AI optimization.
"""

import logging
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from simulation import engine
from mistral_client import optimizer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="FlowSync API",
    description="RTA Traffic Simulation with Mistral AI Optimization",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Models ──────────────────────────────────────────────────────────

class FrameResponse(BaseModel):
    timestamp: str
    hour: int
    day_of_week: str
    locations: list
    junctions: list
    weather: dict
    incidents: list
    metrics: dict


class OptimizedFrameResponse(BaseModel):
    baseline: dict
    optimization: dict
    optimized_metrics: dict
    improvements: dict


# ── Routes ──────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "service": "FlowSync API",
        "version": "1.0.0",
        "status": "running",
        "mistral_available": optimizer.is_available,
        "model": "mistral-large-latest" if optimizer.is_available else "heuristic_fallback",
    }


@app.get("/api/health")
async def health():
    return {"status": "ok", "mistral": optimizer.is_available}


@app.get("/api/dates")
async def get_dates():
    """Return all available dates in the dataset."""
    dates = engine.get_available_dates()
    return {"dates": dates, "count": len(dates)}


@app.get("/api/hours")
async def get_hours(date: str):
    """Return available hours for a given date."""
    hours = engine.get_available_hours(date)
    return {"date": date, "hours": hours}


@app.get("/api/frame")
async def get_frame(date: str, hour: int):
    """
    Get a baseline simulation frame for a specific date and hour.
    This is the 'Without Solution' view.
    """
    dt_str = f"{date} {hour:02d}:00:00"
    try:
        frame = engine.get_frame(dt_str)
        return frame
    except Exception as e:
        logger.error(f"Error generating frame for {dt_str}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/optimize")
async def get_optimized(date: str, hour: int):
    """
    Get an optimized simulation frame using Mistral AI.
    This is the 'With Solution' view.
    Returns baseline + optimization + predicted improvements.
    """
    dt_str = f"{date} {hour:02d}:00:00"
    try:
        # Get baseline frame
        baseline = engine.get_frame(dt_str)

        # Get Mistral optimization
        optimization = optimizer.optimize_frame(baseline)

        # Apply optimization to compute optimized metrics
        optimized_metrics, improvements = _compute_optimizations(baseline, optimization)

        return {
            "baseline": baseline,
            "optimization": optimization,
            "optimized_metrics": optimized_metrics,
            "improvements": improvements,
        }
    except Exception as e:
        logger.error(f"Error optimizing frame for {dt_str}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/compare")
async def get_comparison(date: str, hour: int):
    """
    Get a side-by-side comparison of baseline vs optimized.
    """
    dt_str = f"{date} {hour:02d}:00:00"
    try:
        baseline = engine.get_frame(dt_str)
        optimization = optimizer.optimize_frame(baseline)
        optimized_metrics, improvements = _compute_optimizations(baseline, optimization)

        # Build optimized locations (apply signal adjustments to junction states)
        optimized_junctions = _apply_signal_adjustments(
            baseline["junctions"], optimization.get("signal_adjustments", [])
        )

        return {
            "baseline_metrics": baseline["metrics"],
            "optimized_metrics": optimized_metrics,
            "improvements": improvements,
            "reasoning": optimization.get("reasoning", ""),
            "signal_adjustments": optimization.get("signal_adjustments", []),
            "rerouting": optimization.get("rerouting_recommendations", []),
            "baseline_junctions": baseline["junctions"],
            "optimized_junctions": optimized_junctions,
            "locations": baseline["locations"],
            "weather": baseline["weather"],
            "incidents": baseline["incidents"],
            "timestamp": dt_str,
            "source": optimization.get("source", "unknown"),
            "model": optimization.get("model", "unknown"),
        }
    except Exception as e:
        logger.error(f"Error generating comparison for {dt_str}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Helpers ─────────────────────────────────────────────────────────

def _compute_optimizations(baseline: dict, optimization: dict) -> tuple:
    """Compute optimized metrics based on Mistral's recommendations."""
    base_metrics = baseline["metrics"]
    predicted = optimization.get("predicted_improvement", {})
    delay_red = predicted.get("delay_reduction_pct", 0) / 100.0
    throughput_inc = predicted.get("throughput_increase_pct", 0) / 100.0

    # Count adjustments
    num_adjustments = len(optimization.get("signal_adjustments", []))
    num_reroutes = len(optimization.get("rerouting_recommendations", []))

    # Estimate improvements
    optimized = {
        "total_volume_vph": base_metrics["total_volume_vph"],
        "avg_speed_kph": round(
            base_metrics["avg_speed_kph"] * (1 + throughput_inc * 0.5), 1
        ),
        "avg_vc_ratio": round(
            max(0.05, base_metrics["avg_vc_ratio"] * (1 - delay_red * 0.3)), 3
        ),
        "critical_locations": max(
            0, base_metrics["critical_locations"] - num_adjustments
        ),
        "heavy_locations": max(
            0, base_metrics["heavy_locations"] - num_adjustments // 2
        ),
        "total_delay_s": round(
            base_metrics["total_delay_s"] * (1 - delay_red), 1
        ),
        "total_queue_veh": round(
            max(0, base_metrics["total_queue_veh"] * (1 - delay_red * 0.7)), 1
        ),
        "phase_failures": max(
            0, base_metrics["phase_failures"] - num_adjustments
        ),
        "active_incidents": base_metrics["active_incidents"],
    }

    improvements = {
        "delay_reduction_pct": round(delay_red * 100, 1),
        "throughput_increase_pct": round(throughput_inc * 100, 1),
        "critical_resolved": base_metrics["critical_locations"] - optimized["critical_locations"],
        "queue_reduction_pct": round(
            (1 - optimized["total_queue_veh"] / max(base_metrics["total_queue_veh"], 1)) * 100, 1
        ),
        "speed_increase_pct": round(
            (optimized["avg_speed_kph"] / max(base_metrics["avg_speed_kph"], 1) - 1) * 100, 1
        ),
        "vehicles_rerouted": num_reroutes * 150,  # estimate
        "time_saved_min": round(delay_red * 120, 1),  # estimate for 2h peak
        "signal_adjustments": num_adjustments,
    }

    return optimized, improvements


def _apply_signal_adjustments(junctions: list, adjustments: list) -> list:
    """Apply signal adjustments to junction states for the optimized view."""
    import copy
    optimized = copy.deepcopy(junctions)

    # Build lookup
    adj_map = {}
    for adj in adjustments:
        key = (adj["junction_id"], adj.get("phase_id", ""))
        adj_map[key] = adj

    for junc in optimized:
        for phase in junc.get("phases", []):
            key = (junc["junction_id"], phase["phase_id"])
            if key in adj_map:
                delta = adj_map[key]["green_delta_s"]
                new_green = max(
                    phase["min_green_s"],
                    min(phase["max_green_s"], phase["green_s"] + delta),
                )
                phase["green_s"] = new_green
                phase["adjusted"] = True
                phase["delta"] = delta

        # Recompute delay estimate based on adjustments
        total_delta = sum(
            p.get("delta", 0) for p in junc.get("phases", []) if p.get("adjusted")
        )
        if total_delta != 0:
            # Rough: each second of green reduces delay by ~0.3s
            junc["avg_delay_s_per_veh"] = max(
                2.0, junc["avg_delay_s_per_veh"] - total_delta * 0.3
            )
            junc["degree_of_saturation"] = max(
                0.05, junc["degree_of_saturation"] - total_delta * 0.005
            )

    return optimized


# ── Run ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
