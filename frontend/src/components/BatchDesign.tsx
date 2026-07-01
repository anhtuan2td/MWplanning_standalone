import { Download, Upload } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  downloadCentralRegionGis,
  fetchEquipmentProfiles,
  planBatch,
  type AcceptedFilters,
  type BatchPlanSite,
  type BatchPlanResult,
  type EquipmentProfile,
} from "../api";

type Props = { onClose: () => void };
type BatchProgress = { done: number; total: number; current?: string };
const defaultAcceptedFilters: AcceptedFilters = {
  reject_site_code_contains: "-",
  min_site_code_number: null,
  reject_overload: true,
  reject_overlink: true,
};

const HEADER_ALIASES: Record<string, string[]> = {
  site_name: ["site_name", "site", "name", "site_code", "plan", "quy_hoach", "quy hoạch", "quyhoach"],
  latitude: ["latitude", "lat", "vi_do", "vĩ độ", "vido"],
  longitude: ["longitude", "long", "lon", "lng", "kinh_do", "kinh độ", "kinhdo"],
};

const OPTIONAL_HEADER_ALIASES: Record<string, string[]> = {
  tower_height_m: [
    "tower_height_m",
    "tower_height",
    "height",
    "tower",
    "anten_height",
    "antenna_height",
    "new_site_height_m",
    "cao",
    "cot",
    "cao_do",
    "cao do",
    "do_cao",
    "do cao",
    "cao_anten",
    "cao anten",
  ],
  radius_km: [
    "radius_km",
    "radius",
    "max_radius_km",
    "max_radius",
    "scan_radius",
    "search_radius",
    "ban_kinh",
    "ban kinh",
    "bankinh",
  ],
  min_radius_km: [
    "min_radius_km",
    "min_radius",
    "min_distance_km",
    "min_distance",
    "ban_kinh_min",
    "ban kinh min",
    "bankinhmin",
  ],
  band: ["band", "freq", "frequency", "tan_so", "tan so"],
  rain_zone: ["rain_zone", "rainzone", "itu_rain_zone"],
  antenna_diameter_m: ["antenna_diameter_m", "antenna_diameter", "diameter", "duong_kinh_anten", "duong kinh anten"],
  equipment_profile: ["equipment_profile", "profile", "equipment", "thiet_bi", "thiet bi"],
};

const ALL_HEADER_ALIASES: Record<string, string[]> = { ...HEADER_ALIASES, ...OPTIONAL_HEADER_ALIASES };

function delimiterFor(line: string): "," | ";" {
  return line.split(";").length > line.split(",").length ? ";" : ",";
}

function normalizeHeader(value: string): string {
  return value
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/đ/g, "d")
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
}

function headerIndex(headers: string[], field: keyof typeof HEADER_ALIASES): number {
  const aliases = HEADER_ALIASES[field].map(normalizeHeader);
  return headers.findIndex((header) => aliases.includes(header));
}

function rowValue(row: Record<string, string>, field: string): string | undefined {
  for (const alias of ALL_HEADER_ALIASES[field] ?? [field]) {
    const value = row[normalizeHeader(alias)];
    if (value) return value;
  }
  return undefined;
}

function rowNumber(row: Record<string, string>, field: string, lineNumber: number): number | undefined {
  const value = rowValue(row, field);
  if (!value) return undefined;
  const numeric = Number(value.replace(",", "."));
  if (!Number.isFinite(numeric)) {
    throw new Error(`Gia tri ${field} khong hop le o dong ${lineNumber}`);
  }
  return numeric;
}

function csvCell(value: string | number): string {
  const text = String(value);
  return /[",\r\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

function parseCsv(text: string): BatchPlanSite[] {
  const lines = text.replace(/^\uFEFF/, "").split(/\r?\n/).filter((line) => line.trim());
  if (lines.length < 2) throw new Error("CSV cần có header và ít nhất một trạm.");

  const delimiter = delimiterFor(lines[0]);
  const headers = lines[0].split(delimiter).map(normalizeHeader);
  const siteIndex = headerIndex(headers, "site_name");
  const latIndex = headerIndex(headers, "latitude");
  const lonIndex = headerIndex(headers, "longitude");
  if (siteIndex < 0 || latIndex < 0 || lonIndex < 0) {
    throw new Error("CSV cần có cột tên trạm (site_name/Plan/Quy hoạch), lat và long.");
  }

  return lines.slice(1).map((line, index) => {
    const values = line.split(delimiter).map((value) => value.trim());
    const row = Object.fromEntries(headers.map((header, i) => [header, values[i] ?? ""]));
    const siteName = values[siteIndex] || "";
    const latitude = Number(values[latIndex]);
    const longitude = Number(values[lonIndex]);
    if (!siteName || !Number.isFinite(latitude) || !Number.isFinite(longitude)) {
      throw new Error(`Dữ liệu không hợp lệ ở dòng ${index + 2}`);
    }
    const lineNumber = index + 2;
    const site: BatchPlanSite = {
      site_name: siteName,
      latitude,
      longitude,
    };
    const towerHeight = rowNumber(row, "tower_height_m", lineNumber);
    const radius = rowNumber(row, "radius_km", lineNumber);
    const minRadius = rowNumber(row, "min_radius_km", lineNumber);
    const antennaDiameter = rowNumber(row, "antenna_diameter_m", lineNumber);
    if (towerHeight !== undefined) site.tower_height_m = towerHeight;
    if (radius !== undefined) site.radius_km = radius;
    if (minRadius !== undefined) site.min_radius_km = minRadius;
    if (antennaDiameter !== undefined) site.antenna_diameter_m = antennaDiameter;
    site.band = rowValue(row, "band") || "AUTO";
    site.rain_zone = rowValue(row, "rain_zone");
    site.equipment_profile = rowValue(row, "equipment_profile");
    return site;
  });
}

export function BatchDesign({ onClose }: Props) {
  const [sites, setSites] = useState<BatchPlanSite[]>([]);
  const [result, setResult] = useState<BatchPlanResult | null>(null);
  const [topN, setTopN] = useState(3);
  const [busy, setBusy] = useState(false);
  const [gisBusy, setGisBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [progress, setProgress] = useState<BatchProgress>({ done: 0, total: 0 });
  const [profiles, setProfiles] = useState<EquipmentProfile[]>([]);
  const [profileId, setProfileId] = useState("RACOM_RAy3_24_56_256QAM");
  const [minRadiusKm, setMinRadiusKm] = useState(0);
  const [acceptedFilters, setAcceptedFilters] = useState<AcceptedFilters>(defaultAcceptedFilters);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    fetchEquipmentProfiles().then(setProfiles).catch(() => setProfiles([]));
  }, []);

  const rows = useMemo(
    () =>
      result?.results.flatMap((site) =>
        site.candidates.map((candidate) => ({
          input: site.site_name,
          gis_status: site.gis_status ?? "",
          dem_tiles: site.dem_tiles ?? [],
          missing_dem_tiles: site.missing_dem_tiles ?? [],
          missing_worldcover_tiles: site.missing_worldcover_tiles ?? [],
          bad_dem_tiles: site.bad_dem_tiles ?? [],
          suspect_dem_tiles: site.suspect_dem_tiles ?? [],
          unknown_dem_tiles: site.unknown_dem_tiles ?? [],
          ...candidate,
        }))
      ) ?? [],
    [result]
  );
  const errorRows = useMemo(() => result?.results.filter((site) => site.error) ?? [], [result]);
  const progressPercent = progress.total ? Math.round((progress.done / progress.total) * 100) : 0;

  async function upload(file?: File) {
    if (!file) return;
    try {
      const parsed = parseCsv(await file.text());
      setSites(parsed);
      setResult(null);
      setProgress({ done: 0, total: parsed.length });
      setMessage(`Đã nạp ${parsed.length} trạm từ ${file.name}.`);
    } catch (error) {
      setSites([]);
      setResult(null);
      setProgress({ done: 0, total: 0 });
      setMessage(error instanceof Error ? error.message : "Không đọc được CSV");
    }
  }

  async function run() {
    const controller = new AbortController();
    const completedResults: BatchPlanResult["results"] = [];
    abortRef.current = controller;
    setBusy(true);
    setResult({ results: [] });
    setProgress({ done: 0, total: sites.length, current: sites[0]?.site_name });
    setMessage(`Đang chạy 0/${sites.length} trạm...`);

    try {
      for (let index = 0; index < sites.length; index += 1) {
        if (controller.signal.aborted) break;
        const site = sites[index];
        setProgress({ done: index, total: sites.length, current: site.site_name });
        setMessage(`Đang chạy ${index + 1}/${sites.length}: ${site.site_name}`);

        const payloadSite = {
          ...site,
          min_radius_km: site.min_radius_km ?? minRadiusKm,
          equipment_profile: site.equipment_profile || profileId,
          accepted_filters: acceptedFilters,
        };
        const batchResult = await planBatch([payloadSite], topN, controller.signal);
        completedResults.push(...batchResult.results);
        setResult({ results: [...completedResults] });
        setProgress({ done: index + 1, total: sites.length, current: site.site_name });
      }

      const totalRows = completedResults.reduce((sum, site) => sum + site.candidates.length, 0);
      const failedSites = completedResults.filter((site) => site.error).length;
      if (controller.signal.aborted) {
        setMessage(`Đã dừng ở ${completedResults.length}/${sites.length} trạm, có ${totalRows} dòng kết quả.`);
      } else {
        setMessage(`Đã chạy ${completedResults.length} trạm, trả ${totalRows} dòng kết quả${failedSites ? `, ${failedSites} trạm có ghi chú/lỗi` : ""}.`);
      }
    } catch (error) {
      if (!controller.signal.aborted) setMessage(error instanceof Error ? error.message : "Batch planning thất bại");
    } finally {
      setBusy(false);
      abortRef.current = null;
    }
  }

  async function downloadRegionGis() {
    setGisBusy(true);
    setMessage("Đang kiểm tra/tải GIS vùng Quảng Trị - Lâm Đồng...");
    try {
      const result = await downloadCentralRegionGis();
      const failed = result.dem.failed_tiles.length + result.worldcover.failed_tiles.length;
      setMessage(
        `GIS vùng: DEM ${result.dem.existing_tiles.length} có sẵn, ${result.dem.downloaded_tiles.length} tải mới; WorldCover ${result.worldcover.existing_tiles.length} có sẵn, ${result.worldcover.downloaded_tiles.length} tải mới${failed ? `; lỗi ${failed} tile` : ""}.`
      );
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Tải GIS vùng thất bại");
    } finally {
      setGisBusy(false);
    }
  }

  function exportCsv() {
    const header = [
      "input_site",
      "rank",
      "candidate",
      "distance_km",
      "band",
      "availability_percent",
      "rain_zone",
      "fade_margin_db",
      "equipment_profile",
      "score",
      "status",
      "gis_status",
      "dem_tiles",
      "missing_dem_tiles",
      "missing_worldcover_tiles",
      "bad_dem_tiles",
      "suspect_dem_tiles",
      "unknown_dem_tiles",
      "error",
      "calloff_line",
      "frequency",
      "new_site_frequency",
      "new_site_band_side",
      "new_site_antenna_diameter_m",
      "new_site_height_m",
      "new_site_azimuth_deg",
      "new_site_tilt_deg",
      "root_site_frequency",
      "root_site_band_side",
      "root_site_antenna_diameter_m",
      "root_site_height_m",
      "root_site_azimuth_deg",
      "root_site_tilt_deg",
      "risk_flags",
    ].join(",");
    const lines = rows.map((r) =>
      [
        r.input,
        r.rank,
        r.site_code,
        r.distance_km,
        r.band,
        r.availability_percent,
        r.rain_zone,
        r.fade_margin_db,
        r.equipment_profile,
        r.score,
        r.status,
        r.gis_status,
        r.dem_tiles.join("|"),
        r.missing_dem_tiles.join("|"),
        r.missing_worldcover_tiles.join("|"),
        r.bad_dem_tiles.join("|"),
        r.suspect_dem_tiles.join("|"),
        r.unknown_dem_tiles.join("|"),
        "",
        r.calloff?.line ?? "",
        r.calloff?.frequency ?? "",
        r.calloff?.new_site_frequency ?? "",
        r.calloff?.new_site_band_side ?? "",
        r.calloff?.new_site_antenna_diameter_m ?? "",
        r.calloff?.new_site_height_m ?? "",
        r.calloff?.new_site_azimuth_deg ?? "",
        r.calloff?.new_site_tilt_deg ?? "",
        r.calloff?.root_site_frequency ?? "",
        r.calloff?.root_site_band_side ?? "",
        r.calloff?.root_site_antenna_diameter_m ?? "",
        r.calloff?.root_site_height_m ?? "",
        r.calloff?.root_site_azimuth_deg ?? "",
        r.calloff?.root_site_tilt_deg ?? "",
        r.risk_flags.join("|"),
      ].map(csvCell).join(",")
    );
    const errorLines =
      result?.results
        .filter((site) => !site.candidates.length && site.error)
        .map((site) =>
          [
            site.site_name,
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            site.gis_status ?? "",
            (site.dem_tiles ?? []).join("|"),
            (site.missing_dem_tiles ?? []).join("|"),
            (site.missing_worldcover_tiles ?? []).join("|"),
            (site.bad_dem_tiles ?? []).join("|"),
            (site.suspect_dem_tiles ?? []).join("|"),
            (site.unknown_dem_tiles ?? []).join("|"),
            site.error ?? "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
          ].map(csvCell).join(",")
        ) ?? [];
    const url = URL.createObjectURL(new Blob([[header, ...lines, ...errorLines].join("\n")], { type: "text/csv" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = "batch_candidates.csv";
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <main className="batchShell">
      <header className="batchHeader">
        <div>
          <h1>Design theo lô</h1>
          <p>Import CSV, tính và xuất top candidate cho toàn bộ trạm.</p>
        </div>
        <button type="button" onClick={onClose}>Design đơn trạm</button>
      </header>

      <section className="batchControls">
        <label className="upload">
          <Upload size={18} /> Import input CSV
          <input type="file" accept=".csv" onChange={(event) => upload(event.target.files?.[0])} />
        </label>
        <label>
          Equipment
          <select value={profileId} onChange={(event) => setProfileId(event.target.value)}>
            {profiles.map((profile) => (
              <option key={profile.profile_id} value={profile.profile_id}>
                {profile.vendor} {profile.model} · {profile.channel_bw_mhz}MHz {profile.modulation}
              </option>
            ))}
          </select>
        </label>
        <label>
          Top candidate
          <input type="number" min={1} max={20} value={topN} onChange={(event) => setTopN(Number(event.target.value))} />
        </label>
        <label>
          Min radius km
          <input type="number" min={0} value={minRadiusKm} onChange={(event) => setMinRadiusKm(Number(event.target.value))} />
        </label>
        <div className="filterInline">
          <label className="checkRow">
            <input
              type="checkbox"
              checked={acceptedFilters.reject_site_code_contains === "-"}
              onChange={(event) => setAcceptedFilters({ ...acceptedFilters, reject_site_code_contains: event.target.checked ? "-" : null })}
            />
            Không dấu -
          </label>
          <label className="checkRow">
            <input
              type="checkbox"
              checked={acceptedFilters.reject_overload}
              onChange={(event) => setAcceptedFilters({ ...acceptedFilters, reject_overload: event.target.checked })}
            />
            Không overload
          </label>
          <label className="checkRow">
            <input
              type="checkbox"
              checked={acceptedFilters.reject_overlink}
              onChange={(event) => setAcceptedFilters({ ...acceptedFilters, reject_overlink: event.target.checked })}
            />
            Không overlink
          </label>
          <label className="checkRow thresholdRow">
            <input
              type="checkbox"
              checked={acceptedFilters.min_site_code_number != null}
              onChange={(event) => setAcceptedFilters({ ...acceptedFilters, min_site_code_number: event.target.checked ? 0 : null })}
            />
            Mã &gt;
            <input
              type="number"
              disabled={acceptedFilters.min_site_code_number == null}
              value={acceptedFilters.min_site_code_number ?? ""}
              onChange={(event) => setAcceptedFilters({ ...acceptedFilters, min_site_code_number: event.target.value === "" ? null : Number(event.target.value) })}
            />
          </label>
        </div>
        <button type="button" disabled={gisBusy || busy} onClick={downloadRegionGis}>
          {gisBusy ? "Đang tải GIS..." : "Tải GIS vùng QT-LĐ"}
        </button>
        <button type="button" className="primary" disabled={!sites.length || busy} onClick={run}>
          {busy ? `Đang chạy ${progress.done}/${progress.total}` : `Chạy ${sites.length} trạm`}
        </button>
        {busy && (
          <button type="button" className="danger" onClick={() => abortRef.current?.abort()}>
            Dừng
          </button>
        )}
        <button type="button" disabled={!rows.length} onClick={exportCsv}>
          <Download size={18} />
          Xuất CSV
        </button>
      </section>

      <p className="batchHint">
        Đã nạp: {sites.length} trạm. Cột bắt buộc: site_name/Plan/Quy hoạch, lat, long. Tùy chọn: tower_height_m, radius_km, min_radius_km, band, rain_zone, antenna_diameter_m, equipment_profile.
      </p>
      {progress.total > 0 && (
        <section className="batchProgress">
          <div>
            Tiến độ: {progress.done}/{progress.total} ({progressPercent}%)
            {busy && progress.current ? ` · Đang xử lý: ${progress.current}` : ""}
          </div>
          <progress value={progress.done} max={progress.total} />
        </section>
      )}
      {message && <p className="message">{message}</p>}

      {errorRows.length > 0 && (
        <section className="batchErrors">
          <h2>Lỗi batch</h2>
          {errorRows.map((site) => (
            <p key={site.site_name}>
              <strong>{site.site_name}</strong>: {site.error}
              {site.gis_status ? ` | ${site.gis_status}` : ""}
              {site.bad_dem_tiles?.length ? ` | BAD DEM: ${site.bad_dem_tiles.join(", ")}` : ""}
              {site.suspect_dem_tiles?.length ? ` | SUSPECT DEM: ${site.suspect_dem_tiles.join(", ")}` : ""}
              {site.unknown_dem_tiles?.length ? ` | UNKNOWN DEM: ${site.unknown_dem_tiles.join(", ")}` : ""}
            </p>
          ))}
        </section>
      )}

      <section className="batchTable">
        <table>
          <thead>
            <tr>
              <th>Trạm đầu vào</th>
              <th>Rank</th>
              <th>Candidate</th>
              <th>Khoảng cách</th>
              <th>Band</th>
              <th>Availability</th>
              <th>Vùng mưa</th>
              <th>Fade margin</th>
              <th>Thiết bị</th>
              <th>Score</th>
              <th>Status</th>
              <th>GIS</th>
              <th>DEM warning</th>
              <th>Ghi chú</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={`${row.input}-${row.rank}`}>
                <td>{row.input}</td>
                <td>{row.rank}</td>
                <td>{row.site_code}</td>
                <td>{row.distance_km.toFixed(2)} km</td>
                <td>{row.band}</td>
                <td>{row.availability_percent.toFixed(5)}%</td>
                <td>{row.rain_zone}</td>
                <td>{row.fade_margin_db.toFixed(1)} dB</td>
                <td>{row.equipment_profile}</td>
                <td>{row.score.toFixed(1)}</td>
                <td>{row.status}</td>
                <td>{row.gis_status || "-"}</td>
                <td>
                  {[
                    row.bad_dem_tiles.length ? `BAD ${row.bad_dem_tiles.join("|")}` : "",
                    row.suspect_dem_tiles.length ? `SUSPECT ${row.suspect_dem_tiles.join("|")}` : "",
                    row.unknown_dem_tiles.length ? `UNKNOWN ${row.unknown_dem_tiles.join("|")}` : "",
                    row.missing_dem_tiles.length ? `MISSING ${row.missing_dem_tiles.join("|")}` : "",
                  ].filter(Boolean).join(", ") || "-"}
                </td>
                <td>{row.risk_flags.join(", ") || "-"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </main>
  );
}
