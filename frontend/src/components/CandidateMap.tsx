import L from "leaflet";
import { useEffect } from "react";
import { MapContainer, Marker, Polyline, Popup, TileLayer } from "react-leaflet";
import { useMap } from "react-leaflet";
import { MAP_TILE_URL } from "../api";
import type { CandidateLink } from "../types";
import type { PlanRequest } from "../api";

const SELECTED_LINK_MAX_ZOOM = 17;

function siteIcon(label: string, variant: "origin" | "candidate") {
  return L.divIcon({
    className: `siteLabel ${variant === "origin" ? "originLabel" : "candidateLabel"}`,
    html: `<span>${label}</span>`,
    iconSize: [96, 28],
    iconAnchor: [48, 14]
  });
}

type Props = {
  origin: PlanRequest;
  candidates: CandidateLink[];
  selected: CandidateLink | null;
};

function MapAutoView({ origin, candidates, selected }: Props) {
  const map = useMap();

  useEffect(() => {
    if (selected) {
      requestAnimationFrame(() => {
        map.invalidateSize();
        const originPoint = L.latLng(origin.latitude, origin.longitude);
        const candidatePoint = L.latLng(selected.candidate.latitude, selected.candidate.longitude);
        const bounds = L.latLngBounds([originPoint, candidatePoint]);
        const size = map.getSize();
        const originPixel = map.project(originPoint, 0);
        const candidatePixel = map.project(candidatePoint, 0);
        const baseWidthPx = Math.abs(candidatePixel.x - originPixel.x);
        const baseHeightPx = Math.abs(candidatePixel.y - originPixel.y);
        const widthScale = baseWidthPx > 0 ? (size.x * 0.5) / baseWidthPx : Number.POSITIVE_INFINITY;
        const heightScale = baseHeightPx > 0 ? (size.y * 0.8) / baseHeightPx : Number.POSITIVE_INFINITY;
        const scale = Math.min(widthScale, heightScale);
        const zoom = Number.isFinite(scale) && scale > 0
          ? Math.min(SELECTED_LINK_MAX_ZOOM, Math.max(4, Math.log2(scale)))
          : SELECTED_LINK_MAX_ZOOM;
        map.flyTo(bounds.getCenter(), zoom, { animate: true, duration: 0.45 });
      });
      return;
    }

    const points: [number, number][] = [
      [origin.latitude, origin.longitude],
      ...candidates.map((item) => [item.candidate.latitude, item.candidate.longitude] as [number, number])
    ];

    if (points.length === 1) {
      map.setView(points[0], 11);
      return;
    }

    map.fitBounds(L.latLngBounds(points), {
      padding: [42, 42],
      maxZoom: 13
    });
  }, [origin.latitude, origin.longitude, candidates, selected, map]);

  return null;
}

function routeColor(status: string) {
  if (status === "REJECTED") return "#c2410c";
  if (status === "DANGER") return "#ea580c";
  if (status === "OVERLINK") return "#7c3aed";
  return "#047857";
}

export function CandidateMap({ origin, candidates, selected }: Props) {
  const center: [number, number] = [origin.latitude, origin.longitude];

  return (
    <div className="mapPane">
      <MapContainer center={center} zoom={11} scrollWheelZoom className="map">
        <TileLayer
          attribution="&copy; OpenStreetMap contributors"
          url={MAP_TILE_URL}
        />
        <MapAutoView origin={origin} candidates={candidates} selected={selected} />
        <Marker position={center} icon={siteIcon(origin.site_name || "NEW_SITE", "origin")}>
          <Popup>{origin.site_name}</Popup>
        </Marker>
        {candidates.map((item) => {
          const position: [number, number] = [item.candidate.latitude, item.candidate.longitude];
          return (
            <Marker key={item.candidate.id} position={position} icon={siteIcon(item.candidate.site_code, "candidate")}>
              <Popup>{item.candidate.site_code}</Popup>
            </Marker>
          );
        })}
        {selected && (
          <>
            <Polyline
              positions={[
                center,
                [selected.candidate.latitude, selected.candidate.longitude]
              ]}
              pathOptions={{ color: "#111827", weight: 14, opacity: 0.55 }}
            />
            <Polyline
              positions={[
                center,
                [selected.candidate.latitude, selected.candidate.longitude]
              ]}
              pathOptions={{ color: "#ffffff", weight: 10, opacity: 1 }}
            />
            <Polyline
              positions={[
                center,
                [selected.candidate.latitude, selected.candidate.longitude]
              ]}
              pathOptions={{ color: routeColor(selected.link.status), weight: 7, opacity: 1 }}
            />
          </>
        )}
      </MapContainer>
    </div>
  );
}
