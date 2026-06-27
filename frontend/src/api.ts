import type { CalloffInfo, CalloffRules, PlanResult, SystemStatus } from "./types";

function resolveApiBase() {
  const configured = import.meta.env.VITE_API_BASE;
  if (configured) return configured;
  if (window.location.protocol === "file:") return "http://127.0.0.1:8000";
  if (window.location.port === "5173") return "http://127.0.0.1:8000";
  return window.location.origin;
}

const API_BASE = resolveApiBase();
export const MAP_TILE_URL = import.meta.env.VITE_MAP_TILE_URL ?? "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png";

export type PlanRequest = {
  site_name: string;
  latitude: number;
  longitude: number;
  tower_height_m: number;
  radius_km: number;
  min_radius_km?: number;
  band: string;
  rain_zone?: string;
  antenna_diameter_m?: number;
  equipment_profile?: string;
  accepted_filters?: AcceptedFilters;
};

export type AcceptedFilters = {
  reject_site_code_contains?: string | null;
  min_site_code_number?: number | null;
  reject_overload: boolean;
  reject_overlink: boolean;
};

export type DemDownloadResult = {
  requested_tiles: string[];
  downloaded_tiles: string[];
  existing_tiles: string[];
  failed_tiles: string[];
};

export type WorldCoverDownloadResult = {
  requested_tiles: string[];
  downloaded_tiles: string[];
  existing_tiles: string[];
  failed_tiles: string[];
};

export type GisDownloadResult = {
  dem: DemDownloadResult;
  worldcover: WorldCoverDownloadResult;
};

export async function importSites(file: File) {
  const body = new FormData();
  body.append("file", file);
  const response = await fetch(`${API_BASE}/sites/import`, { method: "POST", body });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

export async function importMwLinks(file: File): Promise<{ imported: number }> {
  const body = new FormData();
  body.append("file", file);
  const response = await fetch(`${API_BASE}/mw-links/import`, { method: "POST", body });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

export async function fetchSystemStatus(): Promise<SystemStatus> {
  const response = await fetch(`${API_BASE}/system/status`);
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

export async function fetchCalloffRules(): Promise<CalloffRules> {
  const response = await fetch(`${API_BASE}/calloff/rules`);
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

export async function shutdownApp(): Promise<void> {
  const response = await fetch(`${API_BASE}/system/shutdown`, { method: "POST" });
  if (!response.ok) throw new Error(await response.text());
}

export async function downloadGis(payload: { latitude: number; longitude: number; radius_km: number }): Promise<GisDownloadResult> {
  const response = await fetch(`${API_BASE}/gis/download`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

export type TerrainGridResult = {
  points: Array<{ latitude: number; longitude: number; elevation_m: number }>;
};

export async function fetchTerrainGrid(payload: {
  north: number;
  south: number;
  east: number;
  west: number;
  rows?: number;
  cols?: number;
}): Promise<TerrainGridResult> {
  const response = await fetch(`${API_BASE}/terrain/grid`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

export async function planSingleLink(payload: PlanRequest, signal?: AbortSignal): Promise<PlanResult> {
  const response = await fetch(`${API_BASE}/plan/single-link`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    signal
  });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

export type EquipmentProfile = { profile_id: string; vendor: string; model: string; band_ghz: number; channel_bw_mhz: number; modulation: string; capacity_mbps: number; rx_threshold_dbm: number; tx_power_min_dbm: number; tx_power_max_dbm: number };
export async function fetchEquipmentProfiles(): Promise<EquipmentProfile[]> { const response = await fetch(`${API_BASE}/equipment/profiles`); if (!response.ok) throw new Error(await response.text()); return response.json(); }
export async function importEquipment(file: File): Promise<{ imported: number; total: number; added: number }> { const body = new FormData(); body.append("file", file); const response = await fetch(`${API_BASE}/equipment/import`, { method: "POST", body }); if (!response.ok) throw new Error(await response.text()); return response.json(); }

export type BatchCandidate = {
  rank: number; site_code: string; distance_km: number; band: string; score: number;
  status: string; availability_percent: number; rain_zone: string; fade_margin_db: number; equipment_profile: string; risk_flags: string[];
  calloff?: CalloffInfo | null;
};
export type BatchPlanResult = { results: Array<{ site_name: string; candidates: BatchCandidate[]; error?: string | null; gis_status?: string | null; missing_dem_tiles?: string[]; missing_worldcover_tiles?: string[] }> };

export async function planBatch(sites: PlanRequest[], topN: number, signal?: AbortSignal): Promise<BatchPlanResult> {
  const response = await fetch(`${API_BASE}/plan/batch`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sites, top_n: topN }),
    signal
  });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

export async function downloadCentralRegionGis(): Promise<GisDownloadResult> {
  const response = await fetch(`${API_BASE}/gis/download/central-region`, { method: "POST" });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}
