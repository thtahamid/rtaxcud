/**
 * FlowSync API Client
 * Connects to the FastAPI backend for simulation frames and optimizations.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface Location {
  location_id: string;
  name: string;
  road: string;
  area: string;
  direction: string;
  latitude: number;
  longitude: number;
  num_lanes: number;
  capacity_vph: number;
  free_flow_speed: number;
  volume_vph: number;
  demand_vph: number;
  avg_speed_kph: number;
  vc_ratio: number;
  occupancy_pct: number;
  level_of_service: string;
  congestion: string;
  color: string;
}

export interface Phase {
  phase_id: string;
  movement: string;
  green_s: number;
  yellow_s: number;
  all_red_s: number;
  min_green_s: number;
  max_green_s: number;
  adjusted?: boolean;
  delta?: number;
}

export interface Junction {
  junction_id: string;
  name: string;
  area: string;
  latitude: number;
  longitude: number;
  num_approaches: number;
  control_type: string;
  active_program: string;
  cycle_length_s: number;
  degree_of_saturation: number;
  avg_delay_s_per_veh: number;
  avg_queue_veh: number;
  throughput_vph: number;
  phase_failures: number;
  adaptive_active: boolean;
  phases: Phase[];
}

export interface Weather {
  temp_c: number;
  humidity_pct: number;
  wind_kph: number;
  visibility_km: number;
  precip_mm: number;
  condition: string;
}

export interface Incident {
  incident_id: string;
  type: string;
  severity: string;
  road: string;
  area: string;
  latitude: number;
  longitude: number;
  lanes_blocked: number;
  duration_min: number;
}

export interface Metrics {
  total_volume_vph: number;
  avg_speed_kph: number;
  avg_vc_ratio: number;
  critical_locations: number;
  heavy_locations: number;
  total_delay_s: number;
  total_queue_veh: number;
  phase_failures: number;
  active_incidents: number;
}

export interface Frame {
  timestamp: string;
  hour: number;
  day_of_week: string;
  locations: Location[];
  junctions: Junction[];
  weather: Weather;
  incidents: Incident[];
  metrics: Metrics;
}

export interface SignalAdjustment {
  junction_id: string;
  phase_id: string;
  green_delta_s: number;
  reason: string;
}

export interface ReroutingRecommendation {
  from_location: string;
  to_alternative: string;
  reason: string;
}

export interface Optimization {
  reasoning: string;
  signal_adjustments: SignalAdjustment[];
  rerouting_recommendations: ReroutingRecommendation[];
  predicted_improvement: {
    delay_reduction_pct: number;
    throughput_increase_pct: number;
  };
  source: string;
  model: string;
}

export interface Comparison {
  baseline_metrics: Metrics;
  optimized_metrics: Metrics;
  improvements: {
    delay_reduction_pct: number;
    throughput_increase_pct: number;
    critical_resolved: number;
    queue_reduction_pct: number;
    speed_increase_pct: number;
    vehicles_rerouted: number;
    time_saved_min: number;
    signal_adjustments: number;
  };
  reasoning: string;
  signal_adjustments: SignalAdjustment[];
  rerouting: ReroutingRecommendation[];
  baseline_junctions: Junction[];
  optimized_junctions: Junction[];
  locations: Location[];
  weather: Weather;
  incidents: Incident[];
  timestamp: string;
  source: string;
  model: string;
}

export async function fetchDates(): Promise<{ dates: string[]; count: number }> {
  const res = await fetch(`${API_BASE}/api/dates`);
  if (!res.ok) throw new Error("Failed to fetch dates");
  return res.json();
}

export async function fetchHours(date: string): Promise<{ date: string; hours: number[] }> {
  const res = await fetch(`${API_BASE}/api/hours?date=${date}`);
  if (!res.ok) throw new Error("Failed to fetch hours");
  return res.json();
}

export async function fetchFrame(date: string, hour: number): Promise<Frame> {
  const res = await fetch(`${API_BASE}/api/frame?date=${date}&hour=${hour}`);
  if (!res.ok) throw new Error("Failed to fetch frame");
  return res.json();
}

export async function fetchComparison(date: string, hour: number): Promise<Comparison> {
  const res = await fetch(`${API_BASE}/api/compare?date=${date}&hour=${hour}`);
  if (!res.ok) throw new Error("Failed to fetch comparison");
  return res.json();
}

export async function fetchHealth(): Promise<{ status: string; mistral: boolean }> {
  const res = await fetch(`${API_BASE}/api/health`);
  if (!res.ok) throw new Error("Failed to fetch health");
  return res.json();
}
