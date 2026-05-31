import { Upload, RadioTower, Download, RotateCw, Power } from "lucide-react";
import { Suspense, lazy, useEffect, useMemo, useRef, useState } from "react";
import { downloadGis, fetchCalloffRules, fetchSystemStatus, importMwLinks, importSites, planSingleLink, shutdownApp, type PlanRequest } from "./api";
import type { CalloffRules, CandidateLink, PlanResult, SystemStatus } from "./types";

const CandidateMap = lazy(() => import("./components/CandidateMap").then((module) => ({ default: module.CandidateMap })));
const TerrainChart = lazy(() => import("./components/TerrainChart").then((module) => ({ default: module.TerrainChart })));

const initialForm: PlanRequest = {
  site_name: "NEW_SITE",
  latitude: 16.032,
  longitude: 108.221,
  tower_height_m: 30,
  radius_km: 30,
  band: "AUTO"
};

function displayError(error: unknown, fallback: string) {
  if (error instanceof TypeError && error.message === "Failed to fetch") {
    return "Cannot connect to backend. Open MWPreplanning.exe and use http://127.0.0.1:8000.";
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

export default function App() {
  const [form, setForm] = useState<PlanRequest>(initialForm);
  const [result, setResult] = useState<PlanResult | null>(null);
  const [selected, setSelected] = useState<CandidateLink | null>(null);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [planning, setPlanning] = useState(false);
  const [showExports, setShowExports] = useState(false);
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [calloffRules, setCalloffRules] = useState<CalloffRules | null>(null);
  const planningAbortRef = useRef<AbortController | null>(null);

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

  async function refreshSystemStatus() {
    try {
      setSystemStatus(await fetchSystemStatus());
    } catch {
      setSystemStatus(null);
    }
  }

  useEffect(() => {
    refreshSystemStatus();
    fetchCalloffRules().then(setCalloffRules).catch(() => setCalloffRules(null));
  }, []);

  async function refreshWorkspace() {
    planningAbortRef.current?.abort();
    setResult(null);
    setSelected(null);
    setShowExports(false);
    setMessage("");
    setPlanning(false);
    setBusy(true);
    try {
      await refreshSystemStatus();
      setCalloffRules(await fetchCalloffRules());
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Refresh failed");
    } finally {
      setBusy(false);
    }
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

  async function runPlan() {
    planningAbortRef.current?.abort();
    const controller = new AbortController();
    planningAbortRef.current = controller;
    setBusy(true);
    setPlanning(true);
    setMessage("");
    try {
      const data = await planSingleLink(form, controller.signal);
      setResult(data);
      setSelected(data.best_candidate ?? data.rejected_links[0] ?? null);
      if (data.summary.total_candidates === 0) {
        setMessage("No candidate sites found. Import site CSV or increase radius.");
      }
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") {
        setMessage("Scan cancelled");
      } else {
        setMessage(error instanceof Error ? error.message : "Planning failed");
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
      setMessage(`CSV imported: ${data.inserted} inserted, ${data.updated} updated, ${data.skipped} skipped`);
      refreshSystemStatus();
    } catch (error) {
      setMessage(displayError(error, "Import failed"));
    } finally {
      setBusy(false);
    }
  }

  async function onMwLinksUpload(file: File | undefined) {
    if (!file) return;
    setBusy(true);
    try {
      const data = await importMwLinks(file);
      setMessage(`MW links imported: ${data.imported}`);
      refreshSystemStatus();
    } catch (error) {
      setMessage(displayError(error, "MW link import failed"));
    } finally {
      setBusy(false);
    }
  }

  async function onDownloadGis() {
    setBusy(true);
    setMessage("Downloading GIS tiles...");
    try {
      const data = await downloadGis({
        latitude: form.latitude,
        longitude: form.longitude,
        radius_km: form.radius_km
      });
      setMessage(
        `GIS download complete. DEM: ${data.dem.downloaded_tiles.length} downloaded, ${data.dem.existing_tiles.length} existing, ${data.dem.failed_tiles.length} failed; WorldCover: ${data.worldcover.downloaded_tiles.length} downloaded, ${data.worldcover.existing_tiles.length} existing, ${data.worldcover.failed_tiles.length} failed`
      );
      refreshSystemStatus();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "GIS download failed");
    } finally {
      setBusy(false);
    }
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
    const header = ["rank", "site_code", "distance_km", "los", "fresnel_percent", "score", "status", "risk_flags"];
    const lines = rows.map((row) =>
      [
        row.rank ?? "",
        row.candidate.site_code,
        row.link.distance_km,
        row.link.los_pass ? "PASS" : "FAIL",
        row.link.fresnel_clearance_percent,
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

  return (
    <main className="shell">
      <aside className="sidebar">
        <div className="brand">
          <RadioTower size={24} />
          <div>
            <h1>MW Pre-planning Lite</h1>
            <span>Offline candidate screening</span>
          </div>
        </div>

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
        <label>
          Band
          <input value="AUTO" disabled />
        </label>

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

        <button onClick={onDownloadGis} disabled={busy}>
          <Download size={18} />
          Download GIS
        </button>

        <button onClick={refreshWorkspace} disabled={busy}>
          <RotateCw size={18} />
          Refresh
        </button>

        <button className="danger" onClick={exitApp} disabled={busy}>
          <Power size={18} />
          Exit app
        </button>

        <button className="primary" onClick={runPlan} disabled={busy}>
          <RadioTower size={18} />
          {busy ? "Running" : "Run planning"}
        </button>
        {planning && (
          <button className="danger" onClick={cancelPlan}>
            Stop scan
          </button>
        )}

        <label className="upload">
          <Upload size={18} />
          Import site CSV
          <input type="file" accept=".csv" onChange={(e) => onCsvUpload(e.target.files?.[0])} />
        </label>
        <label className="upload">
          <Upload size={18} />
          Import MW links
          <input type="file" accept=".csv" onChange={(e) => onMwLinksUpload(e.target.files?.[0])} />
        </label>

        <button onClick={exportCalloffXlsx} disabled={!canExportCalloff}>
          <Download size={18} />
          Export calloff XLS
        </button>
        <label className="toggleRow">
          <input type="checkbox" checked={showExports} onChange={(e) => setShowExports(e.target.checked)} />
          Show raw exports
        </label>
        {showExports && (
          <>
            <button onClick={exportJson} disabled={!result}>
              <Download size={18} />
              Export JSON
            </button>
            <button onClick={exportCsv} disabled={!result}>
              <Download size={18} />
              Export CSV
            </button>
          </>
        )}

        {message && <p className="message">{message}</p>}
      </aside>

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
