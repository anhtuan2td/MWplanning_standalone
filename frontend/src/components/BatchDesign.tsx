import { Download, Upload } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  downloadCentralRegionGis,
  fetchEquipmentProfiles,
  planBatch,
  type AcceptedFilters,
  type BatchPlanResult,
  type EquipmentProfile,
  type PlanRequest,
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

function delimiterFor(line: string): "," | ";" {
  return line.split(";").length > line.split(",").length ? ";" : ",";
}

function headerIndex(headers: string[], field: keyof typeof HEADER_ALIASES): number {
  return headers.findIndex((header) => HEADER_ALIASES[field].includes(header));
}

function csvCell(value: string | number): string {
  const text = String(value);
  return /[",\r\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

function parseCsv(text: string): PlanRequest[] {
  const lines = text.replace(/^\uFEFF/, "").split(/\r?\n/).filter((line) => line.trim());
  if (lines.length < 2) throw new Error("CSV cần có header và ít nhất một trạm.");

  const delimiter = delimiterFor(lines[0]);
  const headers = lines[0].split(delimiter).map((value) => value.trim().toLowerCase());
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
    return {
      site_name: siteName,
      latitude,
      longitude,
      tower_height_m: Number(row.tower_height_m || 30),
      radius_km: Number(row.radius_km || 30),
      min_radius_km: row.min_radius_km ? Number(row.min_radius_km) : undefined,
      band: row.band || "AUTO",
      rain_zone: row.rain_zone || undefined,
      antenna_diameter_m: row.antenna_diameter_m ? Number(row.antenna_diameter_m) : undefined,
      equipment_profile: row.equipment_profile || undefined,
    } as PlanRequest;
  });
}

export function BatchDesign({ onClose }: Props) {
  const [sites, setSites] = useState<PlanRequest[]>([]);
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
    () => result?.results.flatMap((site) => site.candidates.map((candidate) => ({ input: site.site_name, ...candidate }))) ?? [],
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
    const url = URL.createObjectURL(new Blob([[header, ...lines].join("\n")], { type: "text/csv" }));
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
                <td>{row.risk_flags.join(", ") || "-"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </main>
  );
}
