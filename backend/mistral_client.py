"""
FlowSync Mistral AI Integration
Uses Mistral AI API to optimize signal timings and reroute fleets
based on real-time traffic simulation frames.
"""

import os
import json
import logging
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Attempt to import mistralai
try:
    from mistralai import Mistral
    HAS_MISTRAL = True
except ImportError:
    HAS_MISTRAL = False
    logger.warning("mistralai package not installed. AI optimization will use fallback heuristics.")

MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
MODEL = os.getenv("MISTRAL_MODEL", "mistral-large-latest")

SYSTEM_PROMPT = """You are FlowSync, an AI traffic orchestration system for RTA Dubai.
You analyze real-time traffic data and signal performance to recommend optimizations.

SAFETY CONSTRAINTS:
1. Green time must stay within [min_green_s, max_green_s] bounds
2. Cycle length changes must be within ±20% of current
3. Never recommend conflicting phase greens simultaneously
4. On uncertainty, recommend maintaining current timing

OUTPUT: Valid JSON only, no markdown, no explanation outside JSON.
Format:
{
  "reasoning": "brief explanation of your analysis",
  "signal_adjustments": [
    {
      "junction_id": "JCT_XXX",
      "phase_id": "P1",
      "green_delta_s": integer (-15 to +15),
      "reason": "why this adjustment"
    }
  ],
  "rerouting_recommendations": [
    {
      "from_location": "LOC_XXX",
      "to_alternative": "road_name",
      "reason": "why reroute"
    }
  ],
  "predicted_improvement": {
    "delay_reduction_pct": float (0-50),
    "throughput_increase_pct": float (0-30)
  }
}"""


class MistralOptimizer:
    """Uses Mistral AI to optimize traffic signal timings and routing."""

    def __init__(self):
        self.client = None
        if HAS_MISTRAL and MISTRAL_API_KEY:
            try:
                self.client = Mistral(api_key=MISTRAL_API_KEY)
                logger.info("Mistral AI client initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize Mistral client: {e}")

    @property
    def is_available(self) -> bool:
        return self.client is not None

    def optimize_frame(self, frame: dict) -> dict:
        """
        Send a simulation frame to Mistral AI and get optimization recommendations.
        Falls back to heuristic optimization if Mistral is unavailable.
        """
        if not self.is_available:
            return self._heuristic_optimize(frame)

        try:
            # Build a concise prompt from the frame
            prompt = self._build_prompt(frame)

            response = self.client.chat.complete(
                model=MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                max_tokens=2048,
            )

            raw = response.choices[0].message.content
            # Strip markdown code fences if present
            raw = raw.strip()
            if raw.startswith("```"):
                lines = raw.split("\n")
                raw = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
            result = json.loads(raw)
            result["source"] = "mistral_ai"
            result["model"] = MODEL
            return result

        except Exception as e:
            logger.warning(f"Mistral API call failed: {e}. Falling back to heuristic.")
            return self._heuristic_optimize(frame)

    def _build_prompt(self, frame: dict) -> str:
        """Build a concise prompt from simulation frame data."""
        metrics = frame["metrics"]
        junctions = frame["junctions"]
        incidents = frame["incidents"]
        weather = frame["weather"]

        # Summarize top congested locations
        congested = sorted(
            [l for l in frame["locations"] if l["vc_ratio"] > 0.5],
            key=lambda x: x["vc_ratio"],
            reverse=True,
        )[:5]

        # Summarize worst junctions
        worst_junctions = sorted(
            junctions,
            key=lambda x: x["avg_delay_s_per_veh"],
            reverse=True,
        )[:5]

        prompt_parts = [
            f"Traffic Simulation Frame: {frame['timestamp']}",
            f"Hour: {frame['hour']} ({frame['day_of_week']})",
            f"Weather: {weather['condition']}, {weather['temp_c']}°C, precip {weather['precip_mm']}mm",
            "",
            "AGGREGATE METRICS:",
            f"- Total volume: {metrics['total_volume_vph']} veh/h",
            f"- Average speed: {metrics['avg_speed_kph']} km/h",
            f"- Average v/c ratio: {metrics['avg_vc_ratio']}",
            f"- Critical locations: {metrics['critical_locations']}",
            f"- Heavy locations: {metrics['heavy_locations']}",
            f"- Total delay: {metrics['total_delay_s']} s",
            f"- Total queue: {metrics['total_queue_veh']} veh",
            f"- Phase failures: {metrics['phase_failures']}",
            f"- Active incidents: {metrics['active_incidents']}",
            "",
        ]

        if congested:
            prompt_parts.append("TOP CONGESTED LOCATIONS:")
            for loc in congested:
                prompt_parts.append(
                    f"- {loc['name']} ({loc['location_id']}): "
                    f"v/c={loc['vc_ratio']}, vol={loc['volume_vph']}, "
                    f"speed={loc['avg_speed_kph']}, LOS={loc['level_of_service']}"
                )
            prompt_parts.append("")

        if worst_junctions:
            prompt_parts.append("WORST JUNCTIONS (by delay):")
            for j in worst_junctions:
                prompt_parts.append(
                    f"- {j['name']} ({j['junction_id']}): "
                    f"delay={j['avg_delay_s_per_veh']}s, sat={j['degree_of_saturation']}, "
                    f"queue={j['avg_queue_veh']}, program={j['active_program']}, "
                    f"control={j['control_type']}"
                )
                for p in j.get("phases", []):
                    prompt_parts.append(
                        f"    {p['phase_id']} ({p['movement']}): "
                        f"green={p['green_s']}s, min={p['min_green_s']}s, max={p['max_green_s']}s"
                    )
            prompt_parts.append("")

        if incidents:
            prompt_parts.append("ACTIVE INCIDENTS:")
            for inc in incidents[:3]:
                prompt_parts.append(
                    f"- {inc['type']} ({inc['severity']}) on {inc['road']} in {inc['area']}, "
                    f"lanes blocked: {inc['lanes_blocked']}"
                )
            prompt_parts.append("")

        prompt_parts.append(
            "Recommend signal timing adjustments and rerouting to reduce congestion. "
            "Respect safety constraints. Output JSON only."
        )

        return "\n".join(prompt_parts)

    def _heuristic_optimize(self, frame: dict) -> dict:
        """
        Fallback heuristic optimization when Mistral is unavailable.
        Uses simple rules based on v/c ratio and delay.
        """
        adjustments = []
        rerouting = []
        reasoning_parts = []

        for junc in frame["junctions"]:
            if junc["avg_delay_s_per_veh"] > 15 or junc["degree_of_saturation"] > 0.7:
                # Find the phase with the highest demand and extend green slightly
                for phase in junc.get("phases", []):
                    if "Through" in phase["movement"] and phase["green_s"] < phase["max_green_s"]:
                        delta = min(10, phase["max_green_s"] - phase["green_s"])
                        if delta > 0:
                            adjustments.append({
                                "junction_id": junc["junction_id"],
                                "phase_id": phase["phase_id"],
                                "green_delta_s": delta,
                                "reason": f"High delay ({junc['avg_delay_s_per_veh']}s) and saturation ({junc['degree_of_saturation']}) — extending green on {phase['movement']}",
                            })
                            reasoning_parts.append(
                                f"Extending green at {junc['name']} ({junc['junction_id']}) "
                                f"phase {phase['phase_id']} by {delta}s due to "
                                f"delay={junc['avg_delay_s_per_veh']}s, sat={junc['degree_of_saturation']}"
                            )
                        break

        # Reroute recommendations for critical locations
        for loc in frame["locations"]:
            if loc["congestion"] == "critical":
                # Suggest alternative roads based on area
                alts = {
                    "Trade Centre": "Sheikh Zayed Road → Al Wasl Road",
                    "DIFC": "Sheikh Zayed Road → Financial Centre Road",
                    "Deira": "Al Ittihad Road → Damascus Street",
                    "Al Quoz": "Sheikh Zayed Road → Al Margham Street",
                    "Al Barsha": "Sheikh Zayed Road → Hessa Street",
                    "Al Safa": "Sheikh Zayed Road → Al Wasl Road",
                    "Al Wasl": "Sheikh Zayed Road → Al Hadiqa Street",
                    "Oud Metha": "Sheikh Zayed Road → Al Manara Street",
                    "Bur Dubai": "Al Khail Road → Business Bay Crossing",
                    "Business Bay": "Business Bay Crossing → Al Khail Road",
                }
                alt = alts.get(loc["area"], "Use alternate route")
                rerouting.append({
                    "from_location": loc["location_id"],
                    "to_alternative": alt,
                    "reason": f"Critical congestion (v/c={loc['vc_ratio']}) on {loc['road']}",
                })
                reasoning_parts.append(
                    f"Rerouting traffic from {loc['name']} to {alt} "
                    f"due to critical v/c={loc['vc_ratio']}"
                )

        if not reasoning_parts:
            reasoning_parts.append("Traffic flowing within normal parameters. No adjustments needed.")

        return {
            "reasoning": " | ".join(reasoning_parts[:5]),
            "signal_adjustments": adjustments,
            "rerouting_recommendations": rerouting,
            "predicted_improvement": {
                "delay_reduction_pct": min(25.0, len(adjustments) * 3.5),
                "throughput_increase_pct": min(15.0, len(adjustments) * 2.0),
            },
            "source": "heuristic_fallback",
            "model": "rule_based",
        }


# Singleton
optimizer = MistralOptimizer()
