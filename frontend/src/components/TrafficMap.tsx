"use client";

import { useEffect, useRef } from "react";
import {
  MapContainer,
  TileLayer,
  CircleMarker,
  Popup,
  Polyline,
  Marker,
  Tooltip,
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
}

export default function TrafficMap({
  locations,
  junctions,
  incidents,
  optimized = false,
  optimizedJunctions,
}: TrafficMapProps) {
  // Center on Dubai
  const dubaiCenter: [number, number] = [25.2048, 55.2708];

  const displayJunctions = optimized && optimizedJunctions ? optimizedJunctions : junctions;

  return (
    <MapContainer
      center={dubaiCenter}
      zoom={11}
      style={{ height: "100%", width: "100%", borderRadius: "12px" }}
      scrollWheelZoom={true}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />

      {/* Traffic volume circles */}
      {locations.map((loc) => {
        const radius = Math.max(6, Math.min(20, loc.volume_vph / 200));
        const color = optimized
          ? loc.vc_ratio > 0.7
            ? "#f97316"
            : loc.vc_ratio > 0.5
            ? "#eab308"
            : "#10b981"
          : loc.color;

        return (
          <CircleMarker
            key={loc.location_id}
            center={[loc.latitude, loc.longitude]}
            radius={radius}
            fillColor={color}
            fillOpacity={0.7}
            color={color}
            weight={2}
          >
            <Popup>
              <div className="text-xs">
                <strong>{loc.name}</strong>
                <br />
                Road: {loc.road}
                <br />
                Volume: {loc.volume_vph} veh/h
                <br />
                Speed: {loc.avg_speed_kph} km/h
                <br />
                v/c: {loc.vc_ratio}
                <br />
                LOS: {loc.level_of_service}
                <br />
                Status: {loc.congestion}
              </div>
            </Popup>
            <Tooltip direction="top" offset={[0, -5]} opacity={0.9}>
              {loc.name} — {loc.volume_vph} vph
            </Tooltip>
          </CircleMarker>
        );
      })}

      {/* Junction markers */}
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
            radius={8}
            fillColor={color}
            fillOpacity={0.9}
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
}
