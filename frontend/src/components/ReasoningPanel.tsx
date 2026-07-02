"use client";

import { useEffect, useRef } from "react";
import type { SignalAdjustment, ReroutingRecommendation, Junction, Location } from "@/lib/api";

interface ReasoningPanelProps {
  reasoning: string;
  adjustments: SignalAdjustment[];
  rerouting: ReroutingRecommendation[];
  source: string;
  model: string;
  optimized: boolean;
  junctions?: Junction[];
  locations?: Location[];
  onSelect?: (lat: number, lng: number, label: string) => void;
}

export default function ReasoningPanel({
  reasoning,
  adjustments,
  rerouting,
  source,
  model,
  optimized,
  junctions = [],
  locations = [],
  onSelect,
}: ReasoningPanelProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [reasoning, adjustments, rerouting]);

  if (!optimized) {
    return (
      <div className="bg-[#161d2e] border border-[#2a3550] rounded-xl p-4 h-full flex flex-col">
        <div className="flex items-center gap-2 mb-3">
          <div className="w-2 h-2 rounded-full bg-gray-500" />
          <h3 className="text-sm font-semibold text-[#94a3b8]">
            Mistral AI Reasoning
          </h3>
        </div>
        <div className="flex-1 flex items-center justify-center">
          <p className="text-[#64748b] text-sm text-center">
            Switch to FlowSync view to see Mistral AI optimization reasoning
          </p>
        </div>
      </div>
    );
  }

  // Resolve coordinates for a signal adjustment (junction-based)
  const findJunction = (junctionId: string) =>
    junctions.find((j) => j.junction_id === junctionId);

  // Resolve coordinates for a rerouting card (location-based "from_location")
  const findLocation = (locId: string) =>
    locations.find(
      (l) => l.location_id === locId || l.name === locId || l.area === locId
    );

  const interactive = !!onSelect;

  return (
    <div className="bg-[#161d2e] border border-[#2a3550] rounded-xl p-4 h-full flex flex-col">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          <h3 className="text-sm font-semibold text-white">
            Mistral AI Reasoning
          </h3>
        </div>
        <span className="text-xs px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-300 border border-purple-500/30">
          {source === "mistral_ai" ? "Mistral API" : "Heuristic"}
        </span>
      </div>

      {interactive && (
        <p className="text-[10px] text-slate-500 mb-2 italic">
          Click any card to focus it on the map
        </p>
      )}

      <div ref={scrollRef} className="flex-1 overflow-y-auto space-y-3 pr-1">
        {/* Main reasoning */}
        {reasoning && (
          <div className="bg-[#1a2236] rounded-lg p-3 border border-[#2a3550]">
            <p className="text-sm text-[#e2e8f0] leading-relaxed">{reasoning}</p>
          </div>
        )}

        {/* Signal adjustments */}
        {adjustments.length > 0 && (
          <div className="space-y-2">
            <h4 className="text-xs font-semibold text-orange-400 uppercase tracking-wider">
              Signal Adjustments
            </h4>
            {adjustments.map((adj, i) => {
              const junc = findJunction(adj.junction_id);
              const clickable = interactive && !!junc;
              return (
                <button
                  key={i}
                  type="button"
                  disabled={!clickable}
                  onClick={() =>
                    clickable &&
                    onSelect!(
                      junc!.latitude,
                      junc!.longitude,
                      `${junc!.name} — Phase ${adj.phase_id}`
                    )
                  }
                  className={`w-full text-left bg-[#1a2236] rounded-lg p-3 border border-[#2a3550] flex items-start gap-2 transition-all ${
                    clickable
                      ? "hover:border-orange-500/50 hover:bg-[#1f2940] cursor-pointer"
                      : "opacity-90"
                  }`}
                >
                  <div className="w-6 h-6 rounded-full bg-orange-500/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                    <span className="text-xs">🚦</span>
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm text-[#e2e8f0]">
                      <span className="font-mono text-orange-300">
                        {adj.junction_id}
                      </span>{" "}
                      — Phase {adj.phase_id}
                    </p>
                    <p className="text-xs text-[#94a3b8] mt-0.5 break-words">
                      {adj.reason}
                    </p>
                    <p className="text-xs mt-1">
                      <span
                        className={
                          adj.green_delta_s > 0
                            ? "text-emerald-400"
                            : "text-red-400"
                        }
                      >
                        {adj.green_delta_s > 0 ? "+" : ""}
                        {adj.green_delta_s}s green
                      </span>
                    </p>
                  </div>
                  {clickable && (
                    <span className="text-[10px] text-slate-500 mt-1">📍</span>
                  )}
                </button>
              );
            })}
          </div>
        )}

        {/* Rerouting */}
        {rerouting.length > 0 && (
          <div className="space-y-2">
            <h4 className="text-xs font-semibold text-blue-400 uppercase tracking-wider">
              Rerouting
            </h4>
            {rerouting.map((r, i) => {
              const loc = findLocation(r.from_location);
              const clickable = interactive && !!loc;
              return (
                <button
                  key={i}
                  type="button"
                  disabled={!clickable}
                  onClick={() =>
                    clickable &&
                    onSelect!(
                      loc!.latitude,
                      loc!.longitude,
                      `${loc!.name} → ${r.to_alternative}`
                    )
                  }
                  className={`w-full text-left bg-[#1a2236] rounded-lg p-3 border border-[#2a3550] flex items-start gap-2 transition-all ${
                    clickable
                      ? "hover:border-blue-500/50 hover:bg-[#1f2940] cursor-pointer"
                      : "opacity-90"
                  }`}
                >
                  <div className="w-6 h-6 rounded-full bg-blue-500/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                    <span className="text-xs">🔄</span>
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm text-[#e2e8f0] break-words">
                      {r.from_location} →{" "}
                      <span className="text-blue-300">{r.to_alternative}</span>
                    </p>
                    <p className="text-xs text-[#94a3b8] mt-0.5 break-words">
                      {r.reason}
                    </p>
                  </div>
                  {clickable && (
                    <span className="text-[10px] text-slate-500 mt-1">📍</span>
                  )}
                </button>
              );
            })}
          </div>
        )}

        {/* Model info */}
        <div className="pt-2 border-t border-[#2a3550]">
          <p className="text-xs text-[#64748b]">
            Model: <span className="text-[#94a3b8]">{model}</span>
          </p>
        </div>
      </div>
    </div>
  );
}
