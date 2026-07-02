"use client";

import dynamic from "next/dynamic";

// Dynamically import the map to avoid SSR issues with Leaflet
const TrafficMap = dynamic(() => import("./TrafficMap"), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center h-full w-full bg-[#161d2e] rounded-xl">
      <div className="text-[#94a3b8] text-sm animate-pulse">Loading map...</div>
    </div>
  ),
});

export default TrafficMap;
