"use client";

import type { Metrics } from "@/lib/api";

interface MetricsPanelProps {
  baseline: Metrics;
  optimized?: Metrics;
  improvements?: {
    delay_reduction_pct: number;
    throughput_increase_pct: number;
    critical_resolved: number;
    queue_reduction_pct: number;
    speed_increase_pct: number;
    vehicles_rerouted: number;
    time_saved_min: number;
    signal_adjustments: number;
  };
}

function MetricCard({
  label,
  value,
  unit,
  delta,
  color = "blue",
}: {
  label: string;
  value: string | number;
  unit?: string;
  delta?: number;
  color?: "blue" | "green" | "red" | "orange" | "purple";
}) {
  const colorMap = {
    blue: "text-blue-400",
    green: "text-emerald-400",
    red: "text-red-400",
    orange: "text-orange-400",
    purple: "text-purple-400",
  };

  return (
    <div className="bg-[#1a2236] border border-[#2a3550] rounded-xl p-4 flex flex-col gap-1">
      <span className="text-[#94a3b8] text-xs font-medium uppercase tracking-wider">
        {label}
      </span>
      <div className="flex items-baseline gap-1">
        <span className={`text-2xl font-bold ${colorMap[color]}`}>{value}</span>
        {unit && <span className="text-[#94a3b8] text-xs">{unit}</span>}
      </div>
      {delta !== undefined && (
        <span
          className={`text-xs font-medium ${
            delta > 0 ? "text-emerald-400" : delta < 0 ? "text-red-400" : "text-[#94a3b8]"
          }`}
        >
          {delta > 0 ? "↓" : delta < 0 ? "↑" : "—"} {Math.abs(delta)}%
        </span>
      )}
    </div>
  );
}

export default function MetricsPanel({
  baseline,
  optimized,
  improvements,
}: MetricsPanelProps) {
  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
      <MetricCard
        label="Avg Speed"
        value={optimized?.avg_speed_kph ?? baseline.avg_speed_kph}
        unit="km/h"
        delta={improvements?.speed_increase_pct}
        color="blue"
      />
      <MetricCard
        label="Total Delay"
        value={optimized?.total_delay_s ?? baseline.total_delay_s}
        unit="s"
        delta={improvements ? -improvements.delay_reduction_pct : undefined}
        color="red"
      />
      <MetricCard
        label="Queue Length"
        value={optimized?.total_queue_veh ?? baseline.total_queue_veh}
        unit="veh"
        delta={improvements ? -improvements.queue_reduction_pct : undefined}
        color="orange"
      />
      <MetricCard
        label="Critical Points"
        value={optimized?.critical_locations ?? baseline.critical_locations}
        delta={
          improvements
            ? -(improvements.critical_resolved * 10)
            : undefined
        }
        color="red"
      />
      <MetricCard
        label="Throughput"
        value={optimized?.total_volume_vph ?? baseline.total_volume_vph}
        unit="vph"
        delta={improvements?.throughput_increase_pct}
        color="green"
      />
      <MetricCard
        label="Phase Failures"
        value={optimized?.phase_failures ?? baseline.phase_failures}
        color="orange"
      />
      <MetricCard
        label="Time Saved"
        value={improvements?.time_saved_min ?? 0}
        unit="min"
        color="purple"
      />
      <MetricCard
        label="Vehicles Rerouted"
        value={improvements?.vehicles_rerouted ?? 0}
        color="blue"
      />
    </div>
  );
}
