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

function formatValue(value: number): string {
  const abs = Math.abs(value);
  if (abs >= 1_000_000) return (value / 1_000_000).toFixed(1) + "M";
  if (abs >= 10_000) return (value / 1_000).toFixed(1) + "k";
  if (abs >= 1_000) return (value / 1_000).toFixed(1) + "k";
  return String(Math.round(value));
}

const COLOR_STYLES: Record<
  string,
  { text: string; ring: string; glow: string }
> = {
  blue: { text: "text-blue-300", ring: "ring-blue-500/20", glow: "bg-blue-500/5" },
  green: { text: "text-emerald-300", ring: "ring-emerald-500/20", glow: "bg-emerald-500/5" },
  red: { text: "text-red-300", ring: "ring-red-500/20", glow: "bg-red-500/5" },
  orange: { text: "text-orange-300", ring: "ring-orange-500/20", glow: "bg-orange-500/5" },
  purple: { text: "text-purple-300", ring: "ring-purple-500/20", glow: "bg-purple-500/5" },
};

function MetricCard({
  label,
  value,
  unit,
  delta,
  color = "blue",
  invertDelta = false,
}: {
  label: string;
  value: number;
  unit?: string;
  delta?: number;
  color?: "blue" | "green" | "red" | "orange" | "purple";
  invertDelta?: boolean;
}) {
  const c = COLOR_STYLES[color];
  const formatted = formatValue(value);

  // For metrics where lower is better (delay, queue, critical, phase failures),
  // a positive reduction is good. invertDelta flips the sign coloring.
  const shownDelta = delta !== undefined ? (invertDelta ? -delta : delta) : undefined;
  const positive = (shownDelta ?? 0) > 0;
  const negative = (shownDelta ?? 0) < 0;
  const deltaColor = positive
    ? "text-emerald-400"
    : negative
    ? "text-red-400"
    : "text-slate-500";
  const arrow = positive ? "▲" : negative ? "▼" : "—";

  return (
    <div
      className={`relative overflow-hidden rounded-lg ${c.glow} ring-1 ${c.ring} border border-[#2a3550] p-2.5 flex flex-col gap-0.5 min-w-0`}
    >
      <span className="text-[10px] font-medium uppercase tracking-wide text-slate-400 leading-tight truncate">
        {label}
      </span>
      <div className="flex items-baseline gap-1 min-w-0">
        <span className={`text-lg font-bold ${c.text} leading-none truncate`}>
          {formatted}
        </span>
        {unit && (
          <span className="text-[10px] text-slate-400 leading-none truncate">
            {unit}
          </span>
        )}
      </div>
      {shownDelta !== undefined ? (
        <span className={`text-[10px] font-semibold ${deltaColor} leading-tight`}>
          {arrow} {Math.abs(shownDelta).toFixed(1)}%
        </span>
      ) : (
        <span className="text-[10px] text-slate-600 leading-tight">baseline</span>
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
    <div className="grid grid-cols-2 gap-2">
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
        delta={improvements?.delay_reduction_pct}
        invertDelta
        color="red"
      />
      <MetricCard
        label="Queue Length"
        value={optimized?.total_queue_veh ?? baseline.total_queue_veh}
        unit="veh"
        delta={improvements?.queue_reduction_pct}
        invertDelta
        color="orange"
      />
      <MetricCard
        label="Critical Pts"
        value={optimized?.critical_locations ?? baseline.critical_locations}
        delta={improvements ? -improvements.critical_resolved : undefined}
        invertDelta
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
        label="Phase Fails"
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
        label="Rerouted"
        value={improvements?.vehicles_rerouted ?? 0}
        unit="veh"
        color="blue"
      />
    </div>
  );
}
