"use client";

import { useEffect, useRef } from "react";
import {
  MapContainer,
  TileLayer,
  CircleMarker,
  Popup,
  Marker,
  Tooltip,
  useMap,
} from "react-leaflet";
import L from "leaflet";
import type { Location, Junction, Incident } from "@/lib/api";

// Fix default marker icons
const icon = L.icon({
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

interface TrafficMapProps {
  locations: Location[];
  junctions: Junction[];
  incidents: Incident[];
  optimized?: boolean;
  optimizedJunctions?: Junction[];
  focus?: { lat: number; lng: number; zoom?: number; key?: number } | null;
}

// UAE bounds — restrict panning/zoom to keep the map fast and focused
const UAE_BOUNDS = L.latLngBounds([24.7, 54.5], [26.1, 56.6]);

// Congestion → color map
const CONGESTION_COLOR: Record<string, string> = {
  free_flow: "#10b981", // emerald
  moderate: "#eab308", // yellow
  heavy: "#f97316", // orange
  critical: "#dc2626", // red
};

function colorForLocation(loc: Location, optimized: boolean): string {
  if (optimized) {
    if (loc.vc_ratio > 0.85) return CONGESTION_COLOR.critical;
    if (loc.vc_ratio > 0.7) return CONGESTION_COLOR.heavy;
    if (loc.vc_ratio > 0.5) return CONGESTION_COLOR.moderate;
    return CONGESTION_COLOR.free_flow;
  }
  return loc.color || CONGESTION_COLOR.free_flow;
}

// Extract a directional axis token from the `direction` field, e.g. "NB (to Deira)" → "NB"
function dirToken(direction: string): string {
  const m = direction.match(/([NSEW])B/i);
  return m ? m[1].toUpperCase() + "B" : "BOTH";
}

// Build network edges: group locations by road+direction, sort along the road axis,
// and connect consecutive points into flow segments.
interface FlowSegment {
  points: [number, number][];
  color: string;
  weight: number;
  label: string;
  volume: number;
  speed: number;
  vc: number;
  los: string;
  congestion: string;
  // direction the dash animation should travel: +1 = first→last, -1 = last→first
  flowSign: 1 | -1;
}

function buildFlowSegments(locations: Location[], optimized: boolean): FlowSegment[] {
  const groups = new Map<string, Location[]>();
  for (const loc of locations) {
    const key = `${loc.road}__${dirToken(loc.direction)}`;
    const arr = groups.get(key) ?? [];
    arr.push(loc);
    groups.set(key, arr);
  }

  const segments: FlowSegment[] = [];

  for (const [, group] of groups) {
    if (group.length < 1) continue;

    // Determine dominant axis: lat-spread vs lng-spread
    const lats = group.map((g) => g.latitude);
    const lngs = group.map((g) => g.longitude);
    const latSpread = Math.max(...lats) - Math.min(...lats);
    const lngSpread = Math.max(...lngs) - Math.min(...lngs);
    const axisIsLat = latSpread >= lngSpread;

    const sorted = [...group].sort((a, b) =>
      axisIsLat ? a.latitude - b.latitude : a.longitude - b.longitude
    );

    // Determine flow sign from direction token.
    // NB/EB → increasing lat/lng → first→last (sign +1)
    // SB/WB → decreasing → last→first (sign -1)
    const tok = dirToken(group[0].direction);
    const sign: 1 | -1 = tok === "SB" || tok === "WB" ? -1 : 1;

    // Connect consecutive points. Each segment takes the congestion color of its
    // downstream endpoint so the flow visually represents arriving conditions.
    for (let i = 0; i < sorted.length - 1; i++) {
      const a = sorted[i];
      const b = sorted[i + 1];
      const downstream = sign === 1 ? b : a;
      const color = colorForLocation(downstream, optimized);
      const volume = (a.volume_vph + b.volume_vph) / 2;
      const weight = Math.max(3, Math.min(10, Math.round(volume / 800)));
      segments.push({
        points: [
          [a.latitude, a.longitude],
          [b.latitude, b.longitude],
        ],
        color,
        weight,
        label: `${a.road} — ${a.direction}`,
        volume: Math.round(volume),
        speed: Math.round((a.avg_speed_kph + b.avg_speed_kph) / 2),
        vc: Math.round(((a.vc_ratio + b.vc_ratio) / 2) * 100) / 100,
        los: downstream.level_of_service,
        congestion: downstream.congestion,
        flowSign: sign,
      });
    }

    // Standalone locations (no neighbor on the same road) — render as a tiny
    // self-segment so they still appear on the network.
    if (sorted.length === 1) {
      const loc = sorted[0];
      segments.push({
        points: [
          [loc.latitude, loc.longitude],
          [loc.latitude, loc.longitude],
        ],
        color: colorForLocation(loc, optimized),
        weight: Math.max(3, Math.min(10, Math.round(loc.volume_vph / 800))),
        label: `${loc.road} — ${loc.direction}`,
        volume: loc.volume_vph,
        speed: Math.round(loc.avg_speed_kph),
        vc: loc.vc_ratio,
        los: loc.level_of_service,
        congestion: loc.congestion,
        flowSign: 1,
      });
    }
  }

  return segments;
}

// Imperative flow-network renderer. Animates dashOffset for a marching-ants
// effect that travels in the direction of traffic flow. Uses raw Leaflet
// polylines so the animation runs in a single rAF loop without React re-renders.
function FlowNetwork({
  segments,
}: {
  segments: FlowSegment[];
}) {
  const map = useMap();
  const layerRef = useRef<L.LayerGroup | null>(null);

  useEffect(() => {
    const group = L.layerGroup();
    layerRef.current = group;
    group.addTo(map);

    const animated: { line: L.Polyline; sign: 1 | -1; speed: number }[] = [];

    for (const seg of segments) {
      if (seg.points[0][0] === seg.points[1][0] && seg.points[0][1] === seg.points[1][1]) {
        // Degenerate single point — draw a small dot
        const dot = L.circleMarker(seg.points[0], {
          radius: 5,
          fillColor: seg.color,
          fillOpacity: 0.8,
          color: seg.color,
          weight: 2,
        });
        dot.bindTooltip(
          `<div style="font-size:11px"><b>${seg.label}</b><br/>Vol: ${seg.volume} vph<br/>Speed: ${seg.speed} km/h<br/>v/c: ${seg.vc}<br/>LOS: ${seg.los}</div>`
        );
        dot.addTo(group);
        continue;
      }

      // Base road casing (dark, wide) for readability
      const base = L.polyline(seg.points, {
        color: "#0b1220",
        weight: seg.weight + 3,
        opacity: 0.6,
        lineCap: "round",
        lineJoin: "round",
      });
      base.addTo(group);

      // Animated flow line
      const line = L.polyline(seg.points, {
        color: seg.color,
        weight: seg.weight,
        opacity: 0.95,
        lineCap: "round",
        lineJoin: "round",
        dashArray: "14 18",
        dashOffset: "0",
      });
      line.bindTooltip(
        `<div style="font-size:11px"><b>${seg.label}</b><br/>Vol: ${seg.volume} vph<br/>Speed: ${seg.speed} km/h<br/>v/c: ${seg.vc}<br/>LOS: ${seg.los}<br/>Status: ${seg.congestion}</div>`
      );
      line.addTo(group);

      // Animation speed scales with traffic speed (faster flow = faster dashes)
      const animSpeed = Math.max(0.4, Math.min(2.4, seg.speed / 50));
      animated.push({ line, sign: seg.flowSign, speed: animSpeed });
    }

    let raf = 0;
    let last = performance.now();
    const tick = (now: number) => {
      const dt = Math.min(64, now - last);
      last = now;
      for (const { line, sign, speed } of animated) {
        const opts = (line as unknown as { options: { dashOffset: string } }).options;
        let off = parseFloat(opts.dashOffset) || 0;
        // Negative dashOffset moves dashes forward along the polyline direction.
        // Multiply by sign to flip for SB/WB flows.
        off -= sign * speed * dt * 0.06;
        // Keep in a sane range
        if (off > 1000) off -= 1000;
        if (off < -1000) off += 1000;
        line.setStyle({ dashOffset: String(off) } as L.PathOptions);
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);

    return () => {
      cancelAnimationFrame(raf);
      map.removeLayer(group);
    };
  }, [map, segments]);

  return null;
}

// Component that imperatively moves the map when `focus` changes
function MapFocusController({
  focus,
}: {
  focus?: { lat: number; lng: number; zoom?: number; key?: number } | null;
}) {
  const map = useMap();
  const key = focus?.key;
  const lat = focus?.lat;
  const lng = focus?.lng;
  const zoom = focus?.zoom ?? 14;
  useEffect(() => {
    if (lat == null || lng == null) return;
    map.flyTo([lat, lng], zoom, { duration: 0.8 });
  }, [key, lat, lng, zoom, map]);
  return null;
}

const TrafficMap = function TrafficMap({
  locations,
  junctions,
  incidents,
  optimized = false,
  optimizedJunctions,
  focus,
}: TrafficMapProps) {
  const dubaiCenter: [number, number] = [25.2048, 55.2708];
  const displayJunctions =
    optimized && optimizedJunctions ? optimizedJunctions : junctions;

  const segments = buildFlowSegments(locations, optimized);

  return (
    <MapContainer
      center={dubaiCenter}
      zoom={11}
      minZoom={9}
      maxZoom={16}
      maxBounds={UAE_BOUNDS}
      maxBoundsViscosity={1.0}
      style={{ height: "100%", width: "100%", borderRadius: "12px" }}
      scrollWheelZoom={true}
      preferCanvas={true}
    >
      {/* English-language basemap (CARTO Voyager) */}
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>'
        url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png"
        subdomains="abcd"
      />

      <MapFocusController focus={focus} />
      <FlowNetwork segments={segments} />

      {/* Junction markers — small signal nodes */}
      {displayJunctions.map((junc) => {
        const color =
          junc.avg_delay_s_per_veh > 15
            ? "#dc2626"
            : junc.avg_delay_s_per_veh > 10
            ? "#f97316"
            : junc.avg_delay_s_per_veh > 5
            ? "#eab308"
            : "#10b981";

        return (
          <CircleMarker
            key={junc.junction_id}
            center={[junc.latitude, junc.longitude]}
            radius={6}
            fillColor={color}
            fillOpacity={0.95}
            color="#fff"
            weight={2}
          >
            <Popup>
              <div className="text-xs">
                <strong>{junc.name}</strong>
                <br />
                Control: {junc.control_type}
                <br />
                Program: {junc.active_program}
                <br />
                Delay: {junc.avg_delay_s_per_veh} s/veh
                <br />
                Saturation: {junc.degree_of_saturation}
                <br />
                Queue: {junc.avg_queue_veh} veh
                <br />
                Phase failures: {junc.phase_failures}
                {junc.phases.map((p) => (
                  <div key={p.phase_id} className="mt-1">
                    {p.phase_id} ({p.movement}): {p.green_s}s
                    {p.adjusted && (
                      <span className="text-green-600 font-bold">
                        {" "}
                        → {p.green_s + (p.delta || 0)}s
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </Popup>
            <Tooltip direction="top" offset={[0, -5]} opacity={0.9}>
              {junc.name} — {junc.avg_delay_s_per_veh}s delay
            </Tooltip>
          </CircleMarker>
        );
      })}

      {/* Incident markers */}
      {incidents.map((inc) => (
        <Marker
          key={inc.incident_id}
          position={[inc.latitude, inc.longitude]}
          icon={icon}
        >
          <Popup>
            <div className="text-xs">
              <strong>{inc.type}</strong>
              <br />
              Severity: {inc.severity}
              <br />
              Road: {inc.road}
              <br />
              Area: {inc.area}
              <br />
              Lanes blocked: {inc.lanes_blocked}
              <br />
              Duration: {inc.duration_min} min
            </div>
          </Popup>
        </Marker>
      ))}
    </MapContainer>
  );
};

export default TrafficMap;
