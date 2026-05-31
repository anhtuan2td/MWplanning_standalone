import type { CalloffRules, PlanResult, SystemStatus } from "./types";

const API_BASE = import.meta.env.VITE_API_BASE ?? window.location.origin;
export const MAP_TILE_URL = import.meta.env.VITE_MAP_TILE_URL ?? "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png";

export type PlanRequest = {
  site_name: string;
  latitude: number;
  longitude: number;
  tower_height_m: number;
  radius_km: number;
  band: string;
};

export type DemDownloadResult = {
  requested_tiles: string[];
  downloaded_tiles: string[];
  existing_tiles: string[];
  failed_tiles: string[];
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

export async function downloadDem(payload: { latitude: number; longitude: number; radius_km: number }): Promise<DemDownloadResult> {
  const response = await fetch(`${API_BASE}/dem/download`, {
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
