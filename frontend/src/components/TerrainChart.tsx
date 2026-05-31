import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis, CartesianGrid, ReferenceLine } from "recharts";
import type { CandidateLink } from "../types";

type Props = {
  link: CandidateLink | null;
};

export function TerrainChart({ link }: Props) {
  const profile = link?.link.terrain_profile;
  const nearSiteCode = link?.calloff?.new_site ?? "New site";
  const farSiteCode = link?.candidate.site_code ?? "Candidate";
  const farKm = profile ? Number((profile.distance_m[profile.distance_m.length - 1] / 1000).toFixed(2)) : undefined;
  const farTerrain = profile?.effective_terrain_elevation_m[profile.effective_terrain_elevation_m.length - 1];
  const farAntenna = profile?.los_elevation_m[profile.los_elevation_m.length - 1];
  const allValues = profile ? [...profile.effective_terrain_elevation_m, ...profile.los_elevation_m] : [];
  const minValue = allValues.length ? Math.min(...allValues) : 0;
  const maxValue = allValues.length ? Math.max(...allValues) : 0;
  const span = Math.max(maxValue - minValue, 20);
  const yDomain: [number, number] = [Math.floor(minValue - span * 0.55), Math.ceil(maxValue + span * 0.18)];
  const rows = profile
    ? profile.distance_m.map((distance, index) => ({
        km: Number((distance / 1000).toFixed(2)),
        terrain: profile.effective_terrain_elevation_m[index],
        los: profile.los_elevation_m[index],
        farAntenna: profile.los_elevation_m[profile.los_elevation_m.length - 1]
      }))
    : [];

  return (
    <div className="chartPane">
      <div className="chartHeader">
        <h2>Terrain Profile</h2>
        <span>{link ? `${link.candidate.site_code} - ${link.link.risk_flags.join(", ") || "No flags"}` : "No link selected"}</span>
      </div>
      {link && (
        <div className="profileEndpoints">
          <span>{nearSiteCode}</span>
          <span>{farSiteCode}</span>
        </div>
      )}
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={rows}>
          <CartesianGrid strokeDasharray="3 3" stroke="#d6dbe3" />
          <XAxis dataKey="km" type="number" domain={["dataMin", "dataMax"]} tick={{ fontSize: 12 }} unit=" km" />
          <YAxis tick={{ fontSize: 12 }} unit=" m" width={58} domain={yDomain} />
          <Tooltip />
          {farKm !== undefined && farTerrain !== undefined && farAntenna !== undefined && (
            <ReferenceLine
              segment={[
                { x: farKm, y: farTerrain },
                { x: farKm, y: farAntenna }
              ]}
              stroke="#9333ea"
              strokeWidth={3}
              label={{ value: farSiteCode, position: "insideTopRight", fill: "#581c87", fontSize: 12 }}
            />
          )}
          <Line type="monotone" dataKey="terrain" stroke="#7c2d12" strokeWidth={2} dot={false} />
          <Line type="monotone" dataKey="los" stroke="#0369a1" strokeWidth={2} dot={false} />
          <Line type="monotone" dataKey="farAntenna" stroke="#9333ea" strokeWidth={2} strokeDasharray="5 4" dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
