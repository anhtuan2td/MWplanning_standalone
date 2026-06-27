import {
  Bot,
  Download,
  FileJson,
  MapPinned,
  Power,
  RadioTower,
  RefreshCw,
  Send,
  SlidersHorizontal,
  Upload
} from "lucide-react";
import { FormEvent, Suspense, lazy, useEffect, useMemo, useRef, useState } from "react";
import {
  downloadGis,
  fetchCalloffRules,
  fetchSystemStatus,
  importMwLinks,
  importSites,
  importEquipment,
  fetchEquipmentProfiles,
  planSingleLink,
  shutdownApp,
  type AcceptedFilters, type PlanRequest, type EquipmentProfile
} from "./api";
import type { CalloffRules, CandidateLink, PlanResult, SystemStatus } from "./types";
import { BatchDesign } from "./components/BatchDesign";

const CandidateMap = lazy(() => import("./components/CandidateMap").then((module) => ({ default: module.CandidateMap })));
const TerrainChart = lazy(() => import("./components/TerrainChart").then((module) => ({ default: module.TerrainChart })));

const initialForm: PlanRequest = {
  site_name: "NEW_SITE",
  latitude: 16.032,
  longitude: 108.221,
  tower_height_m: 30,
  radius_km: 30,
  min_radius_km: 0,
  band: "AUTO",
  accepted_filters: {
    reject_site_code_contains: "-",
    min_site_code_number: null,
    reject_overload: true,
    reject_overlink: true
  }
};

type ChatMessage = {
  id: string;
  role: "assistant" | "user" | "system";
  text: string;
};

function displayError(error: unknown, fallback: string) {
  if (error instanceof TypeError && error.message === "Failed to fetch") {
    return "Không kết nối được backend. Hãy mở MWPreplanning.exe và dùng http://127.0.0.1:8000.";
  }
  return error instanceof Error ? error.message : fallback;
}

function closeAppTab() {
  window.open("", "_self");
  window.close();
  window.setTimeout(() => {
    if (window.closed) return;
    document.title = "MW Pre-planning Lite closed";
    document.body.innerHTML = `
      <main style="font-family: Segoe UI, Arial, sans-serif; padding: 40px; color: #17202a;">
        <h1 style="font-size: 22px; margin: 0 0 12px;">MW Pre-planning Lite is closed</h1>
        <p style="margin: 0; font-size: 15px;">The local backend has been shut down. You can close this browser tab.</p>
      </main>
    `;
  }, 400);
}

function id() {
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function formatCandidate(row: CandidateLink) {
  return `${row.candidate.site_code}: ${row.link.distance_km.toFixed(2)} km, ${row.link.band}, score ${row.link.score.toFixed(1)}, ${row.link.status}`;
}

function updateAcceptedFilters(form: PlanRequest, patch: Partial<AcceptedFilters>): PlanRequest {
  const current = form.accepted_filters ?? {
    reject_site_code_contains: null,
    min_site_code_number: null,
    reject_overload: false,
    reject_overlink: false
  };
  return { ...form, accepted_filters: { ...current, ...patch } };
}

function tileName(latFloor: number, lonFloor: number) {
  const ns = latFloor >= 0 ? "N" : "S";
  const ew = lonFloor >= 0 ? "E" : "W";
  return `${ns}${Math.abs(latFloor).toString().padStart(2, "0")}${ew}${Math.abs(lonFloor).toString().padStart(3, "0")}`;
}

function tilesForRadius(latitude: number, longitude: number, radiusKm: number) {
  const latDelta = radiusKm / 111.0;
  const lonScale = Math.max(Math.cos((latitude * Math.PI) / 180), 0.1);
  const lonDelta = radiusKm / (111.0 * lonScale);
  const minLat = Math.floor(latitude - latDelta);
  const maxLat = Math.floor(latitude + latDelta);
  const minLon = Math.floor(longitude - lonDelta);
  const maxLon = Math.floor(longitude + lonDelta);
  const tiles: string[] = [];
  for (let lat = minLat; lat <= maxLat; lat += 1) {
    for (let lon = minLon; lon <= maxLon; lon += 1) {
      tiles.push(tileName(lat, lon));
    }
  }
  return tiles;
}

function worldcoverTileName(latFloor: number, lonFloor: number) {
  const latOrigin = Math.floor(latFloor / 3) * 3;
  const lonOrigin = Math.floor(lonFloor / 3) * 3;
  return `${tileName(latOrigin, lonOrigin).replace(/([NS]\d{2})([EW]\d{3})/, "ESA_WorldCover_10m_2020_v100_$1$2_Map")}`;
}

function worldcoverTilesForRadius(latitude: number, longitude: number, radiusKm: number) {
  const latDelta = radiusKm / 111.0;
  const lonScale = Math.max(Math.cos((latitude * Math.PI) / 180), 0.1);
  const lonDelta = radiusKm / (111.0 * lonScale);
  const minLat = Math.floor(latitude - latDelta);
  const maxLat = Math.floor(latitude + latDelta);
  const minLon = Math.floor(longitude - lonDelta);
  const maxLon = Math.floor(longitude + lonDelta);
  const tiles = new Set<string>();
  for (let lat = minLat; lat <= maxLat; lat += 1) {
    for (let lon = minLon; lon <= maxLon; lon += 1) {
      tiles.add(worldcoverTileName(lat, lon));
    }
  }
  return [...tiles].sort();
}

function missingGis(status: SystemStatus | null, request: PlanRequest) {
  if (!status) return { dem: ["status unknown"], worldcover: ["status unknown"] };
  const demTiles = new Set(status.dem_tiles);
  const coverMaps = new Set(status.worldcover_maps);
  const dem = tilesForRadius(request.latitude, request.longitude, request.radius_km).filter((tile) => !demTiles.has(tile));
  const worldcover = worldcoverTilesForRadius(request.latitude, request.longitude, request.radius_km).filter((tile) => !coverMaps.has(tile));
  return { dem, worldcover };
}

function parseCoordinatePair(text: string): { lat: number; lon: number } | null {
  const normalized = text.replace(/,/g, " ");
  const coordPattern = /(?:^|[^A-Za-z0-9_.-])(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)(?=$|[^A-Za-z0-9_.-])/g;
  let match: RegExpExecArray | null = null;
  while ((match = coordPattern.exec(normalized)) !== null) {
    const lat = Number(match[1]);
    const lon = Number(match[2]);
    if (Math.abs(lat) <= 90 && Math.abs(lon) <= 180) {
      return { lat, lon };
    }
  }
  return null;
}

function parseSiteName(text: string): string | null {
  const explicitSite = text.match(/(?:site|t[eê]n|name)\s*[:=]?\s*([A-Za-z][A-Za-z0-9_-]{2,})/i);
  if (explicitSite) return explicitSite[1].toUpperCase();

  const planSite = text.match(/(?:plan|planning|quy\s*ho[aạ]ch)\s+(?:site\s+)?([A-Za-z][A-Za-z0-9_-]{2,})/i);
  return planSite ? planSite[1].toUpperCase() : null;
}

function stripVietnameseMarks(text: string): string {
  return text.normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/đ/g, "d").replace(/Đ/g, "D");
}

function parseChatPlan(text: string, current: PlanRequest): { nextForm: PlanRequest; changed: string[] } {
  const nextForm = { ...current };
  const changed: string[] = [];
  const keywordText = stripVietnameseMarks(text);

  const coords = parseCoordinatePair(text);
  if (coords) {
    nextForm.latitude = coords.lat;
    nextForm.longitude = coords.lon;
    changed.push(`tọa độ ${coords.lat}, ${coords.lon}`);
  }

  const minRadiusMatch = keywordText.match(/(?:min(?:imum)?\s+radius|min(?:imum)?\s+r|ban kinh\s+toi\s+thieu)\s*[:=]?\s*(\d+(?:\.\d+)?)\s*(?:km)?/i);
  if (minRadiusMatch) {
    nextForm.min_radius_km = Number(minRadiusMatch[1]);
    changed.push(`bán kính tối thiểu ${nextForm.min_radius_km} km`);
  }

  const radiusPattern = /(?:max(?:imum)?\s*)?(?:radius|ban kinh|r)\s*[:=]?\s*(\d+(?:\.\d+)?)\s*(?:km)?/gi;
  let radiusMatch: RegExpExecArray | null = null;
  let candidateRadiusMatch: RegExpExecArray | null = null;
  while ((candidateRadiusMatch = radiusPattern.exec(keywordText)) !== null) {
    const prefix = keywordText.slice(0, candidateRadiusMatch.index).toLowerCase();
    if (!/(?:min(?:imum)?\s*)$/.test(prefix)) {
      radiusMatch = candidateRadiusMatch;
    }
  }
  if (radiusMatch) {
    nextForm.radius_km = Number(radiusMatch[1]);
    changed.push(`bán kính ${nextForm.radius_km} km`);
  }

  const heightMatch = text.match(/(?:tower|height|cao|c[oộ]t)\s*[:=]?\s*(\d+(?:\.\d+)?)\s*(?:m)?/i);
  if (heightMatch) {
    nextForm.tower_height_m = Number(heightMatch[1]);
    changed.push(`cao anten ${nextForm.tower_height_m} m`);
  }

  const siteMatch = parseSiteName(text);
  if (siteMatch) {
    nextForm.site_name = siteMatch;
    changed.push(`site ${nextForm.site_name}`);
  }

  return { nextForm, changed };
}

function isPlanIntent(text: string) {
  return /(plan|planning|quy ho[aạ]ch|ch[aạ]y|scan|t[iì]m|candidate|link)/i.test(text);
}

function isGisIntent(text: string) {
  return /(download|t[aả]i).*(gis|dem|worldcover)|gis|dem/i.test(text);
}

function isStatusIntent(text: string) {
  return /(status|tr[aạ]ng th[aá]i|refresh|reload|c[aậ]p nh[aậ]t)/i.test(text);
}

function isHelpIntent(text: string) {
  return /(help|h[uư][oớ]ng d[aẫ]n|l[eệ]nh|command|\?)/i.test(text);
}

export default function App() {
  const [batchMode, setBatchModeState] = useState(() => window.location.hash === "#batch" || localStorage.getItem("mw_batch_mode") === "1");
  const [form, setForm] = useState<PlanRequest>(initialForm);
  const [result, setResult] = useState<PlanResult | null>(null);
  const [selected, setSelected] = useState<CandidateLink | null>(null);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [planning, setPlanning] = useState(false);
  const [showDetails, setShowDetails] = useState(false);
  const [showExports, setShowExports] = useState(false);
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [calloffRules, setCalloffRules] = useState<CalloffRules | null>(null);
  const [equipmentProfiles, setEquipmentProfiles] = useState<EquipmentProfile[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([
    {
      id: id(),
      role: "assistant",
      text: "Nhập yêu cầu quy hoạch bằng tiếng Việt. Ví dụ: quy hoạch site DN001 tại 16.032, 108.221 bán kính 30km cao 30m."
    }
  ]);
  const chatEndRef = useRef<HTMLDivElement | null>(null);
  const planningAbortRef = useRef<AbortController | null>(null);

  function setBatchMode(value: boolean) {
    setBatchModeState(value);
    localStorage.setItem("mw_batch_mode", value ? "1" : "0");
    if (value) {
      window.history.replaceState(null, "", "#batch");
    } else if (window.location.hash === "#batch") {
      window.history.replaceState(null, "", window.location.pathname + window.location.search);
    }
  }

  const rows = useMemo(() => {
    if (!result) return [];
    return [...result.candidate_links, ...result.rejected_links];
  }, [result]);
  const bestLink = result?.best_candidate
    ? `${result.best_candidate.candidate.site_code}-${form.site_name || "NEW_SITE"}`
    : "-";
  const statusText = systemStatus
    ? Object.entries(systemStatus.site_status_counts).map(([key, value]) => `${key}: ${value}`).join(", ")
    : "-";
  const demRegionText = systemStatus?.dem_regions.length ? systemStatus.dem_regions.join(", ") : "-";
  const worldCoverRegionText = systemStatus?.worldcover_regions.length ? systemStatus.worldcover_regions.join(", ") : "-";
  const canExportCalloff = Boolean(selected?.calloff && selected.link.status !== "REJECTED");

  function pushMessage(role: ChatMessage["role"], text: string) {
    setChatMessages((items) => [...items, { id: id(), role, text }]);
  }

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [chatMessages, busy]);

  async function refreshSystemStatus() {
    try {
      const data = await fetchSystemStatus();
      setSystemStatus(data);
      return data;
    } catch {
      setSystemStatus(null);
      return null;
    }
  }

  useEffect(() => {
    refreshSystemStatus();
    fetchCalloffRules().then(setCalloffRules).catch(() => setCalloffRules(null));
    fetchEquipmentProfiles().then(setEquipmentProfiles).catch(() => setEquipmentProfiles([]));
  }, []);

  async function refreshWorkspace(announce = true) {
    planningAbortRef.current?.abort();
    setResult(null);
    setSelected(null);
    setShowExports(false);
    setMessage("");
    setPlanning(false);
    setBusy(true);
    try {
      const [status, rules] = await Promise.all([refreshSystemStatus(), fetchCalloffRules()]);
      setCalloffRules(rules);
      if (announce) {
        pushMessage("assistant", `Đã refresh workspace. Sites: ${status?.total_sites ?? 0}, MW links: ${status?.total_mw_links ?? 0}.`);
      }
    } catch (error) {
      const text = error instanceof Error ? error.message : "Refresh failed";
      setMessage(text);
      pushMessage("assistant", text);
    } finally {
      setBusy(false);
    }
  }

  async function onEquipmentUpload(file?: File) {
    if (!file) return;
    try { const imported = await importEquipment(file); setEquipmentProfiles(await fetchEquipmentProfiles()); setMessage(`Equipment: imported ${imported.imported}, total ${imported.total}.`); }
    catch (error) { setMessage(displayError(error, "Equipment import failed")); }
  }

  async function exitApp() {
    const confirmed = window.confirm("Shutdown MW Pre-planning Lite?");
    if (!confirmed) return;
    planningAbortRef.current?.abort();
    setBusy(true);
    setMessage("Shutting down app...");
    try {
      await shutdownApp();
      closeAppTab();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Shutdown failed");
      setBusy(false);
    }
  }

  async function runPlan(nextForm = form, announce = true) {
    planningAbortRef.current?.abort();
    const controller = new AbortController();
    planningAbortRef.current = controller;
    setForm(nextForm);
    setBusy(true);
    setPlanning(true);
    setMessage("");
    if (announce) {
      pushMessage("system", `Đang kiểm tra GIS cho ${nextForm.site_name} trong bán kính ${nextForm.radius_km} km...`);
    }
    try {
      const gisReady = await ensureGisReady(nextForm);
      if (!gisReady) return;
      pushMessage("system", `GIS đã sẵn sàng. Đang quét candidate cho ${nextForm.site_name}...`);
      const data = await planSingleLink(nextForm, controller.signal);
      setResult(data);
      setSelected(data.best_candidate ?? data.rejected_links[0] ?? null);
      if (data.summary.total_candidates === 0) {
        setMessage("No candidate sites found. Import site CSV or increase radius.");
        pushMessage("assistant", "Không tìm thấy candidate. Hãy import site CSV hoặc tăng bán kính tìm kiếm.");
      } else {
        const best = data.best_candidate ? formatCandidate(data.best_candidate) : "không có link đạt yêu cầu";
        pushMessage(
          "assistant",
          `Hoàn tất: ${data.summary.total_candidates} candidate, ${data.summary.accepted} accepted, ${data.summary.rejected} rejected. Best: ${best}.`
        );
      }
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") {
        setMessage("Scan cancelled");
        pushMessage("assistant", "Đã dừng scan.");
      } else {
        const text = displayError(error, "Planning failed");
        setMessage(text);
        pushMessage("assistant", text);
      }
    } finally {
      if (planningAbortRef.current === controller) {
        planningAbortRef.current = null;
      }
      setBusy(false);
      setPlanning(false);
    }
  }

  function cancelPlan() {
    planningAbortRef.current?.abort();
  }

  async function onCsvUpload(file: File | undefined) {
    if (!file) return;
    setBusy(true);
    try {
      const data = await importSites(file);
      const text = `CSV imported: ${data.inserted} inserted, ${data.updated} updated, ${data.skipped} skipped`;
      setMessage(text);
      pushMessage("assistant", text);
      refreshSystemStatus();
    } catch (error) {
      const text = displayError(error, "Import failed");
      setMessage(text);
      pushMessage("assistant", text);
    } finally {
      setBusy(false);
    }
  }

  async function onMwLinksUpload(file: File | undefined) {
    if (!file) return;
    setBusy(true);
    try {
      const data = await importMwLinks(file);
      const text = `MW links imported: ${data.imported}`;
      setMessage(text);
      pushMessage("assistant", text);
      refreshSystemStatus();
    } catch (error) {
      const text = displayError(error, "MW link import failed");
      setMessage(text);
      pushMessage("assistant", text);
    } finally {
      setBusy(false);
    }
  }

  async function onDownloadGis() {
    setBusy(true);
    setMessage("Downloading GIS tiles...");
    pushMessage("system", `Đang tải GIS quanh ${form.latitude}, ${form.longitude} bán kính ${form.radius_km} km...`);
    try {
      const data = await downloadGis({
        latitude: form.latitude,
        longitude: form.longitude,
        radius_km: form.radius_km
      });
      const text =
        `GIS xong. DEM: ${data.dem.downloaded_tiles.length} tải mới, ${data.dem.existing_tiles.length} có sẵn, ${data.dem.failed_tiles.length} lỗi; ` +
        `WorldCover: ${data.worldcover.downloaded_tiles.length} tải mới, ${data.worldcover.existing_tiles.length} có sẵn, ${data.worldcover.failed_tiles.length} lỗi.`;
      setMessage(text);
      pushMessage("assistant", text);
      refreshSystemStatus();
    } catch (error) {
      const text = error instanceof Error ? error.message : "GIS download failed";
      setMessage(text);
      pushMessage("assistant", text);
    } finally {
      setBusy(false);
    }
  }

  async function ensureGisReady(nextForm: PlanRequest) {
    const status = await refreshSystemStatus();
    const missing = missingGis(status, nextForm);
    if (missing.dem.length === 0 && missing.worldcover.length === 0) {
      pushMessage("system", "GIS đã đủ cho khu vực hiện tại.");
      return true;
    }

    pushMessage(
      "system",
      `Thiếu GIS cho khu vực này. DEM thiếu ${missing.dem.length} tile, WorldCover thiếu ${missing.worldcover.length} tile. Đang tải tự động...`
    );
    const data = await downloadGis({
      latitude: nextForm.latitude,
      longitude: nextForm.longitude,
      radius_km: nextForm.radius_km
    });
    const failed = data.dem.failed_tiles.length + data.worldcover.failed_tiles.length;
    const text =
      `GIS auto-check xong. DEM: ${data.dem.downloaded_tiles.length} tải mới, ${data.dem.existing_tiles.length} có sẵn, ${data.dem.failed_tiles.length} lỗi; ` +
      `WorldCover: ${data.worldcover.downloaded_tiles.length} tải mới, ${data.worldcover.existing_tiles.length} có sẵn, ${data.worldcover.failed_tiles.length} lỗi.`;
    setMessage(text);
    pushMessage(failed ? "assistant" : "system", text);
    await refreshSystemStatus();
    if (failed > 0) {
      pushMessage("assistant", "Một số tile GIS tải lỗi nên chưa chạy planning. Kiểm tra mạng hoặc nguồn GIS rồi chạy lại.");
      return false;
    }
    return true;
  }

  function exportJson() {
    if (!result) return;
    const blob = new Blob([JSON.stringify(result, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${form.site_name}_mw_plan.json`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  function exportCsv() {
    if (!result) return;
    const header = ["rank", "site_code", "distance_km", "los", "fresnel_percent", "availability_percent", "rain_zone", "score", "status", "risk_flags"];
    const lines = rows.map((row) =>
      [
        row.rank ?? "",
        row.candidate.site_code,
        row.link.distance_km,
        row.link.los_pass ? "PASS" : "FAIL",
        row.link.fresnel_clearance_percent,
        row.link.availability_percent,
        row.link.rain_zone,
        row.link.score,
        row.link.status,
        row.link.risk_flags.join("|")
      ].join(",")
    );
    const blob = new Blob([[header.join(","), ...lines].join("\n")], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${form.site_name}_mw_plan.csv`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  function exportCalloffXlsx() {
    if (!selected?.calloff || selected.link.status === "REJECTED") return;
    const headers = [
      "Line",
      "Frequency",
      "Distance",
      "Device",
      "A end",
      "Band (A)",
      "Antena diameter (A)",
      "Elevation (A)",
      "Azimuth (A)",
      "Tilt (A)",
      "B end",
      "Band (B)",
      "Antena diameter (B)",
      "",
      "Elevation (B)",
      "Azimuth (B)",
      "Tilt (B)"
    ];
    const row = [
      selected.calloff.line,
      selected.calloff.frequency,
      selected.calloff.distance_km,
      "",
      selected.calloff.new_site,
      selected.calloff.new_site_band_side,
      selected.calloff.new_site_antenna_diameter_m,
      selected.calloff.new_site_height_m,
      selected.calloff.new_site_azimuth_deg,
      selected.calloff.new_site_tilt_deg,
      selected.calloff.root_site,
      selected.calloff.root_site_band_side,
      selected.calloff.root_site_antenna_diameter_m,
      "",
      selected.calloff.root_site_height_m,
      selected.calloff.root_site_azimuth_deg,
      selected.calloff.root_site_tilt_deg
    ];
    const escapeXml = (value: string | number) =>
      String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
    const xmlRows = [headers, row].map((items) =>
      `<Row>${items.map((item) => `<Cell><Data ss:Type="${typeof item === "number" ? "Number" : "String"}">${escapeXml(item)}</Data></Cell>`).join("")}</Row>`
    ).join("");
    const content = `<?xml version="1.0" encoding="UTF-8"?><?mso-application progid="Excel.Sheet"?><Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet" xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:x="urn:schemas-microsoft-com:office:excel" xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet"><Worksheet ss:Name="calloff"><Table>${xmlRows}</Table></Worksheet></Workbook>`;
    const blob = new Blob([content], { type: "application/vnd.ms-excel;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${selected.calloff.new_site}_${selected.calloff.root_site}_calloff.xls`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  async function handleChatSubmit(event: FormEvent) {
    event.preventDefault();
    const text = chatInput.trim();
    if (!text || busy) return;
    setChatInput("");
    pushMessage("user", text);

    const { nextForm, changed } = parseChatPlan(text, form);
    if (changed.length) {
      setForm(nextForm);
      pushMessage("assistant", `Đã nhận: ${changed.join(", ")}.`);
    }

    if (isHelpIntent(text)) {
      pushMessage("assistant", "Có thể nhập: quy hoạch site DN001 tại 16.032, 108.221 bán kính 30km cao 30m; tải GIS; refresh; hoặc hỏi best link sau khi chạy.");
      return;
    }

    if (isStatusIntent(text)) {
      await refreshWorkspace(true);
      return;
    }

    if (isGisIntent(text) && !isPlanIntent(text)) {
      await onDownloadGis();
      return;
    }

    if (isPlanIntent(text) || changed.length > 0) {
      await runPlan(nextForm, true);
      return;
    }

    if (/(best|t[oố]t nh[aấ]t|k[eế]t qu[aả])/i.test(text) && result) {
      pushMessage("assistant", result.best_candidate ? `Best hiện tại: ${formatCandidate(result.best_candidate)}.` : "Chưa có best candidate đạt yêu cầu.");
      return;
    }

    pushMessage("assistant", "Tôi chưa hiểu lệnh này. Gõ help để xem mẫu câu.");
  }

  if (batchMode) return <BatchDesign onClose={() => setBatchMode(false)} />;

  return (
    <main className="chatShell">
      <section className="chatPanel">
        <div className="brand">
          <RadioTower size={24} />
          <div>
            <h1>MW Pre-planning Lite</h1>
            <span>Chat-driven candidate screening</span>
          </div>
        </div>

        <div className="chatMessages">
          {chatMessages.map((item) => (
            <div key={item.id} className={`chatBubble ${item.role}`}>
              <span className="bubbleIcon">{item.role === "user" ? "You" : item.role === "system" ? "Run" : <Bot size={15} />}</span>
              <p>{item.text}</p>
            </div>
          ))}
          {busy && (
            <div className="chatBubble system">
              <span className="bubbleIcon">Run</span>
              <p>{planning ? "Planner đang xử lý..." : "Đang xử lý..."}</p>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        <form className="chatComposer" onSubmit={handleChatSubmit}>
          <input
            value={chatInput}
            onChange={(e) => setChatInput(e.target.value)}
            placeholder="Nhập yêu cầu quy hoạch, ví dụ: plan site DN001 tại 16.032, 108.221 radius 30 cao 30"
          />
          <button className="primary iconButton" disabled={busy || !chatInput.trim()} title="Send">
            <Send size={18} />
          </button>
        </form>

        <div className="quickActions">
          <button type="button" onClick={() => setBatchMode(true)}>Design theo lô</button>
          <button onClick={() => runPlan(form)} disabled={busy}>
            <RadioTower size={18} />
            Run
          </button>
          {planning && (
            <button className="danger" onClick={cancelPlan}>
              Stop
            </button>
          )}
          <button onClick={onDownloadGis} disabled={busy}>
            <MapPinned size={18} />
            GIS
          </button>
          <button onClick={() => refreshWorkspace(true)} disabled={busy}>
            <RefreshCw size={18} />
            Refresh
          </button>
          <button onClick={() => setShowDetails((value) => !value)}>
            <SlidersHorizontal size={18} />
            Params
          </button>
          <button className="danger" onClick={exitApp} disabled={busy}>
            <Power size={18} />
            Exit
          </button>
        </div>

        {showDetails && (
          <div className="paramPanel">
            <label>
              Site name
              <input value={form.site_name} onChange={(e) => setForm({ ...form, site_name: e.target.value })} />
            </label>
            <div className="grid2">
              <label>
                Latitude
                <input type="number" value={form.latitude} onChange={(e) => setForm({ ...form, latitude: Number(e.target.value) })} />
              </label>
              <label>
                Longitude
                <input type="number" value={form.longitude} onChange={(e) => setForm({ ...form, longitude: Number(e.target.value) })} />
              </label>
            </div>
            <label>
              Equipment profile
              <select value={form.equipment_profile ?? "RACOM_RAy3_24_56_256QAM"} onChange={(e) => setForm({ ...form, equipment_profile: e.target.value })}>
                {equipmentProfiles.map((profile) => <option key={profile.profile_id} value={profile.profile_id}>{profile.vendor} {profile.model} · {profile.band_ghz}GHz/{profile.channel_bw_mhz}MHz · {profile.modulation}</option>)}
              </select>
            </label>
            <div className="grid2">
              <label>
                Tower m
                <input type="number" value={form.tower_height_m} onChange={(e) => setForm({ ...form, tower_height_m: Number(e.target.value) })} />
              </label>
              <label>
                Radius km
                <input type="number" value={form.radius_km} onChange={(e) => setForm({ ...form, radius_km: Number(e.target.value) })} />
              </label>
            </div>
            <div className="grid2">
              <label>
                Min radius km
                <input type="number" value={form.min_radius_km ?? 0} onChange={(e) => setForm({ ...form, min_radius_km: Number(e.target.value) })} />
              </label>
              <div />
            </div>
            <div className="filterPanel">
              <span>Accepted filters</span>
              <label className="checkRow">
                <input
                  type="checkbox"
                  checked={form.accepted_filters?.reject_site_code_contains === "-"}
                  onChange={(e) => setForm(updateAcceptedFilters(form, { reject_site_code_contains: e.target.checked ? "-" : null }))}
                />
                Loại site code có dấu -
              </label>
              <label className="checkRow">
                <input
                  type="checkbox"
                  checked={Boolean(form.accepted_filters?.reject_overload)}
                  onChange={(e) => setForm(updateAcceptedFilters(form, { reject_overload: e.target.checked }))}
                />
                Loại overload
              </label>
              <label className="checkRow">
                <input
                  type="checkbox"
                  checked={Boolean(form.accepted_filters?.reject_overlink)}
                  onChange={(e) => setForm(updateAcceptedFilters(form, { reject_overlink: e.target.checked }))}
                />
                Loại overlink
              </label>
              <label className="checkRow thresholdRow">
                <input
                  type="checkbox"
                  checked={form.accepted_filters?.min_site_code_number != null}
                  onChange={(e) => setForm(updateAcceptedFilters(form, { min_site_code_number: e.target.checked ? 0 : null }))}
                />
                Site code number &gt;
                <input
                  type="number"
                  disabled={form.accepted_filters?.min_site_code_number == null}
                  value={form.accepted_filters?.min_site_code_number ?? ""}
                  onChange={(e) => setForm(updateAcceptedFilters(form, { min_site_code_number: e.target.value === "" ? null : Number(e.target.value) }))}
                />
              </label>
            </div>
          </div>
        )}

        <div className="fileActions">
          <label className="upload">
            <Upload size={18} />
            Site CSV
            <input type="file" accept=".csv" onChange={(e) => onCsvUpload(e.target.files?.[0])} />
          </label>
          <label className="upload">
            <Upload size={18} />
            Equipment CSV
            <input type="file" accept=".csv" onChange={(e) => onEquipmentUpload(e.target.files?.[0])} />
          </label>
          <label className="upload">
            <Upload size={18} />
            MW links
            <input type="file" accept=".csv" onChange={(e) => onMwLinksUpload(e.target.files?.[0])} />
          </label>
          <button onClick={exportCalloffXlsx} disabled={!canExportCalloff}>
            <Download size={18} />
            Calloff
          </button>
          <button onClick={() => setShowExports((value) => !value)}>
            <FileJson size={18} />
            Raw
          </button>
          {showExports && (
            <>
              <button onClick={exportJson} disabled={!result}>JSON</button>
              <button onClick={exportCsv} disabled={!result}>CSV</button>
            </>
          )}
        </div>

        {calloffRules && (
          <div className="rulePanel">
            <strong>Band / antenna rule</strong>
            {calloffRules.band_antenna_rules.map((rule) => (
              <div key={`${rule.distance}-${rule.band}`}>
                <span>{rule.distance}</span>
                <b>{rule.band}</b>
                <em>{rule.antenna_diameter_m.toFixed(1)} m</em>
              </div>
            ))}
          </div>
        )}

        {message && <p className="message">{message}</p>}
      </section>

      <section className="workspace">
        <div className="summary">
          <div><strong>{result?.summary.total_candidates ?? 0}</strong><span>Total</span></div>
          <div><strong>{result?.summary.accepted ?? 0}</strong><span>Accepted</span></div>
          <div><strong>{result?.summary.rejected ?? 0}</strong><span>Rejected</span></div>
          <div><strong>{bestLink}</strong><span>Best link</span></div>
          <div><strong>{systemStatus?.total_sites ?? 0}</strong><span>Imported sites</span></div>
          <div><strong>{systemStatus?.total_mw_links ?? 0}</strong><span>MW links</span></div>
          <div><strong>{systemStatus?.dem_tiles.length ?? 0}</strong><span>DEM tiles</span></div>
          <div><strong>{systemStatus?.worldcover_maps.length ?? 0}</strong><span>Cover maps</span></div>
          <div><strong>{result?.summary.avg_seconds_per_link?.toFixed(3) ?? "-"}</strong><span>Avg sec/link</span></div>
          <div><strong>{result?.summary.elapsed_seconds?.toFixed(2) ?? "-"}</strong><span>Total sec</span></div>
        </div>
        <div className="statusStrip">
          <span>Input: {form.site_name} | {form.latitude}, {form.longitude} | {form.radius_km} km | {form.tower_height_m} m</span>
          <span>Site status: {statusText}</span>
          <span>DEM regions: {demRegionText}</span>
          <span>Cover regions: {worldCoverRegionText}</span>
        </div>

        <Suspense fallback={<div className="mapPane loadingPane">Loading map...</div>}>
          <CandidateMap origin={form} selected={selected} candidates={rows} />
        </Suspense>

        <div className="lower">
          <div className="tablePane">
            <table>
              <thead>
                <tr>
                  <th>Rank</th>
                  <th>Candidate</th>
                  <th>Distance</th>
                  <th>Site status</th>
                  <th>LOS</th>
                  <th>Fresnel</th>
                  <th>Band</th>
                  <th>Availability</th>
                  <th>Score</th>
                  <th>Status</th>
                  <th>Notes</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.candidate.id} className={selected?.candidate.id === row.candidate.id ? "active" : ""} onClick={() => setSelected(row)}>
                    <td>{row.rank ?? "-"}</td>
                    <td>{row.candidate.site_code}</td>
                    <td>{row.link.distance_km.toFixed(2)} km</td>
                    <td>{row.candidate.status}</td>
                    <td>{row.link.los_pass ? "PASS" : "FAIL"}</td>
                    <td>{row.link.fresnel_clearance_percent.toFixed(1)}%</td>
                    <td>{row.link.band}</td>
                    <td>{row.link.availability_percent.toFixed(5)}% ({row.link.rain_zone})</td>
                    <td>{row.link.score.toFixed(1)}</td>
                    <td><span className={`pill ${row.link.status.toLowerCase()}`}>{row.link.status}</span></td>
                    <td>{row.link.risk_flags.join(", ") || "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Suspense fallback={<div className="chartPane loadingPane">Loading chart...</div>}>
            <TerrainChart link={selected} />
          </Suspense>
        </div>
      </section>
    </main>
  );
}
