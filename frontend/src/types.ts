export type Site = {
  id: string;
  site_code: string;
  site_name: string;
  latitude: number;
  longitude: number;
  ground_elevation_m: number;
  tower_height_m: number;
  available_height_m: number;
  overload: number;
  diverse_routing: boolean;
  cells_4g: number | null;
  cells_5g: number | null;
  status: string;
  distance_km: number;
  bearing_deg: number;
};

export type TerrainProfile = {
  distance_m: number[];
  terrain_elevation_m: number[];
  effective_terrain_elevation_m: number[];
  los_elevation_m: number[];
};

export type LinkResult = {
  distance_km: number;
  band: string;
  los_pass: boolean;
  worst_clearance_m: number;
  worst_point_km: number;
  fresnel_clearance_percent: number;
  minimum_clearance_m: number;
  score: number;
  status: string;
  risk_flags: string[];
  terrain_profile: TerrainProfile;
  availability_percent: number;
  rain_zone: string;
  fade_margin_db: number;
  equipment_profile: string;
};

export type CalloffInfo = {
  line: string;
  frequency: string;
  new_site: string;
  new_site_frequency: string;
  new_site_band_side: string;
  new_site_antenna_diameter_m: number;
  new_site_height_m: number;
  new_site_azimuth_deg: number;
  new_site_tilt_deg: number;
  root_site: string;
  root_site_frequency: string;
  root_site_band_side: string;
  root_site_antenna_diameter_m: number;
  root_site_height_m: number;
  root_site_azimuth_deg: number;
  root_site_tilt_deg: number;
  distance_km: number;
};

export type CandidateLink = {
  candidate: Site;
  link: LinkResult;
  rank: number | null;
  calloff: CalloffInfo | null;
};

export type PlanResult = {
  best_candidate: CandidateLink | null;
  candidate_links: CandidateLink[];
  rejected_links: CandidateLink[];
  summary: {
    total_candidates: number;
    accepted: number;
    rejected: number;
    band: string;
    elapsed_seconds: number;
    avg_seconds_per_link: number;
  };
};

export type SystemStatus = {
  total_sites: number;
  total_mw_links: number;
  site_status_counts: Record<string, number>;
  dem_tiles: string[];
  dem_regions: string[];
  dem_unmapped_tiles: string[];
  worldcover_maps: string[];
  worldcover_regions: string[];
  worldcover_unmapped_maps: string[];
};

export type CalloffRules = {
  band_antenna_rules: Array<{
    distance: string;
    band: string;
    antenna_diameter_m: number;
  }>;
};
