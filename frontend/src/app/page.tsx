"use client";

import { useState, useEffect, useCallback } from "react";
import dynamic from "next/dynamic";
import {
  fetchDates,
  fetchComparison,
  fetchHealth,
  type Comparison,
} from "@/lib/api";
import MetricsPanel from "@/components/MetricsPanel";
import ReasoningPanel from "@/components/ReasoningPanel";

// Dynamic import for Leaflet map (no SSR)
const TrafficMap = dynamic(() => import("@/components/TrafficMap"), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center h-full w-full bg-[#161d2e] rounded-xl">
      <div className="text-[#94a3b8] text-sm animate-pulse">Loading map...</div>
    </div>
  ),
});

export default function Dashboard() {
  const [dates, setDates] = useState<string[]>([]);
  const [selectedDate, setSelectedDate] = useState<string>("");
  const [selectedHour, setSelectedHour] = useState<number>(8);
  const [view, setView] = useState<"baseline" | "optimized">("baseline");
  const [data, setData] = useState<Comparison | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [mistralAvailable, setMistralAvailable] = useState(false);
  const [autoPlay, setAutoPlay] = useState(false);
  const [playSpeed, setPlaySpeed] = useState<1 | 1.5 | 2>(1);
  const [focus, setFocus] = useState<{
    lat: number;
    lng: number;
    zoom?: number;
    key?: number;
  } | null>(null);

  // Load dates on mount
  useEffect(() => {
    fetchDates()
      .then((d) => {
        setDates(d.dates);
        if (d.dates.length > 0) {
          // Pick a date with interesting data (peak traffic)
          setSelectedDate(d.dates[42]); // Jan 4, 2023 — weekday
        }
      })
      .catch((e) => setError(e.message));

    fetchHealth()
      .then((h) => setMistralAvailable(h.mistral))
      .catch(() => setMistralAvailable(false));
  }, []);

  // Fetch comparison data when date/hour changes
  const loadData = useCallback(async () => {
    if (!selectedDate) return;
    setLoading(true);
    setError(null);
    try {
      const result = await fetchComparison(selectedDate, selectedHour);
      setData(result);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }, [selectedDate, selectedHour]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Auto-play through hours — base interval scales inversely with speed
  useEffect(() => {
    if (!autoPlay) return;
    const interval = setInterval(() => {
      setSelectedHour((h) => (h >= 23 ? 0 : h + 1));
    }, Math.round(2000 / playSpeed));
    return () => clearInterval(interval);
  }, [autoPlay, playSpeed]);

  const hours = Array.from({ length: 24 }, (_, i) => i);

  return (
    <div className="flex flex-col h-screen bg-[#0a0e1a]">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-3 bg-[#0d1220] border-b border-[#1e293b]">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-[#004B87] flex items-center justify-center">
            <span className="text-white font-bold text-sm">FS</span>
          </div>
          <div>
            <h1 className="text-lg font-bold text-white tracking-tight">
              FlowSync
            </h1>
            <p className="text-xs text-[#64748b]">
              RTA Traffic Intelligence × Mistral AI
            </p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          {/* Mistral status */}
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#161d2e] border border-[#2a3550]">
            <div
              className={`w-2 h-2 rounded-full ${
                mistralAvailable ? "bg-emerald-500 pulse-glow" : "bg-orange-500"
              }`}
            />
            <span className="text-xs text-[#94a3b8]">
              {mistralAvailable ? "Mistral AI Connected" : "Heuristic Mode"}
            </span>
          </div>

          {/* View toggle */}
          <div className="flex bg-[#161d2e] rounded-lg border border-[#2a3550] p-0.5">
            <button
              onClick={() => setView("baseline")}
              className={`px-4 py-1.5 rounded-md text-xs font-medium transition-all ${
                view === "baseline"
                  ? "bg-red-500/20 text-red-300 border border-red-500/30"
                  : "text-[#94a3b8] hover:text-white"
              }`}
            >
              Baseline
            </button>
            <button
              onClick={() => setView("optimized")}
              className={`px-4 py-1.5 rounded-md text-xs font-medium transition-all ${
                view === "optimized"
                  ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                  : "text-[#94a3b8] hover:text-white"
              }`}
            >
              FlowSync
            </button>
          </div>
        </div>
      </header>

      {/* Controls bar */}
      <div className="flex items-center gap-4 px-6 py-2 bg-[#0d1220]/50 border-b border-[#1e293b]">
        {/* Date selector */}
        <div className="flex items-center gap-2">
          <label className="text-xs text-[#64748b]">Date:</label>
          <select
            value={selectedDate}
            onChange={(e) => setSelectedDate(e.target.value)}
            className="bg-[#161d2e] border border-[#2a3550] rounded-md px-2 py-1 text-xs text-[#e5e7eb] focus:outline-none focus:border-[#004B87]"
          >
            {dates.slice(0, 60).map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>
        </div>

        {/* Hour selector */}
        <div className="flex items-center gap-2">
          <label className="text-xs text-[#64748b]">Hour:</label>
          <div className="flex gap-0.5">
            {hours.map((h) => (
              <button
                key={h}
                onClick={() => setSelectedHour(h)}
                className={`w-7 h-7 rounded text-xs font-mono transition-all ${
                  selectedHour === h
                    ? "bg-[#004B87] text-white"
                    : h >= 7 && h <= 9
                    ? "bg-red-500/10 text-red-300 hover:bg-red-500/20"
                    : h >= 17 && h <= 20
                    ? "bg-orange-500/10 text-orange-300 hover:bg-orange-500/20"
                    : "bg-[#161d2e] text-[#64748b] hover:text-white"
                }`}
              >
                {h}
              </button>
            ))}
          </div>
        </div>

        {/* Auto-play */}
        <button
          onClick={() => setAutoPlay(!autoPlay)}
          className={`px-3 py-1 rounded-md text-xs font-medium transition-all ${
            autoPlay
              ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
              : "bg-[#161d2e] text-[#94a3b8] border border-[#2a3550] hover:text-white"
          }`}
        >
          {autoPlay ? "⏸ Pause" : "▶ Auto-Play"}
        </button>

        {/* Speed selector */}
        <div className="flex items-center gap-1 bg-[#161d2e] rounded-md border border-[#2a3550] p-0.5">
          {([1, 1.5, 2] as const).map((s) => (
            <button
              key={s}
              onClick={() => setPlaySpeed(s)}
              disabled={!autoPlay}
              className={`px-2 py-1 rounded text-xs font-mono transition-all ${
                playSpeed === s
                  ? "bg-[#004B87] text-white"
                  : autoPlay
                  ? "text-[#94a3b8] hover:text-white"
                  : "text-[#475569] cursor-not-allowed"
              }`}
            >
              {s}x
            </button>
          ))}
        </div>

        {/* Loading indicator */}
        {loading && (
          <div className="flex items-center gap-2 text-xs text-[#94a3b8]">
            <div className="w-3 h-3 border-2 border-[#004B87] border-t-transparent rounded-full animate-spin" />
            Computing...
          </div>
        )}

        {/* Error */}
        {error && (
          <span className="text-xs text-red-400">Error: {error}</span>
        )}

        {/* Timestamp */}
        {data && (
          <div className="ml-auto text-xs text-[#64748b]">
            {data.timestamp} — {data.source === "mistral_ai" ? "Mistral AI" : "Heuristic"} — {data.model}
          </div>
        )}
      </div>

      {/* Main content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Map area */}
        <div className="flex-1 relative">
          {data ? (
            <TrafficMap
              locations={data.locations}
              junctions={
                view === "optimized"
                  ? data.optimized_junctions
                  : data.baseline_junctions
              }
              incidents={data.incidents}
              optimized={view === "optimized"}
              optimizedJunctions={data.optimized_junctions}
              focus={focus}
            />
          ) : (
            <div className="flex items-center justify-center h-full">
              <p className="text-[#64748b]">Loading simulation...</p>
            </div>
          )}

          {/* Map legend */}
          <div className="absolute bottom-4 left-4 bg-[#0d1220]/90 backdrop-blur-sm border border-[#2a3550] rounded-lg p-3 z-[1000]">
            <p className="text-xs font-semibold text-[#94a3b8] mb-2">
              Flow Congestion
            </p>
            <div className="flex flex-col gap-1.5">
              <div className="flex items-center gap-2">
                <div className="w-8 h-1 rounded-full bg-[#10b981]" />
                <span className="text-xs text-[#94a3b8]">Free flow</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-8 h-1 rounded-full bg-[#eab308]" />
                <span className="text-xs text-[#94a3b8]">Moderate</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-8 h-1 rounded-full bg-[#f97316]" />
                <span className="text-xs text-[#94a3b8]">Heavy</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-8 h-1 rounded-full bg-[#dc2626]" />
                <span className="text-xs text-[#94a3b8]">Critical</span>
              </div>
              <p className="text-[10px] text-[#64748b] mt-1 italic">
                Dashes flow in traffic direction
              </p>
            </div>
          </div>

          {/* View indicator */}
          {data && (
            <div
              className={`absolute top-4 left-4 px-3 py-1.5 rounded-lg text-xs font-bold z-[1000] ${
                view === "optimized"
                  ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                  : "bg-red-500/20 text-red-300 border border-red-500/30"
              }`}
            >
              {view === "optimized" ? "✓ FlowSync Optimized" : "⚠ Baseline (No Solution)"}
            </div>
          )}
        </div>

        {/* Right sidebar */}
        <div className="w-[380px] flex flex-col border-l border-[#1e293b] bg-[#0d1220]">
          {/* Metrics */}
          <div className="p-4 border-b border-[#1e293b]">
            <h2 className="text-sm font-semibold text-white mb-3">
              Live Telemetry
            </h2>
            {data && (
              <MetricsPanel
                baseline={data.baseline_metrics}
                optimized={
                  view === "optimized"
                    ? data.optimized_metrics
                    : undefined
                }
                improvements={
                  view === "optimized" ? data.improvements : undefined
                }
              />
            )}
          </div>

          {/* Reasoning panel */}
          <div className="flex-1 p-4 overflow-hidden">
            {data && (
              <ReasoningPanel
                reasoning={data.reasoning}
                adjustments={data.signal_adjustments}
                rerouting={data.rerouting}
                source={data.source}
                model={data.model}
                optimized={view === "optimized"}
                junctions={data.baseline_junctions}
                locations={data.locations}
                onSelect={(lat, lng) =>
                  setFocus({
                    lat,
                    lng,
                    zoom: 15,
                    key: Date.now(),
                  })
                }
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
