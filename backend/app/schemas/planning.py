from pydantic import BaseModel, Field

from app.schemas.site import SiteSearchResult


class Endpoint(BaseModel):
    latitude: float
    longitude: float
    ground_elevation_m: float = 0
    tower_height_m: float = 30


class TerrainProfileRequest(BaseModel):
    a: Endpoint
    b: Endpoint
    step_m: float | None = None


class TerrainProfile(BaseModel):
    distance_m: list[float]
    terrain_elevation_m: list[float]
    effective_terrain_elevation_m: list[float]
    los_elevation_m: list[float] | None = None


class TerrainGridRequest(BaseModel):
    north: float
    south: float
    east: float
    west: float
    rows: int = 12
    cols: int = 12


class TerrainGridPoint(BaseModel):
    latitude: float
    longitude: float
    elevation_m: float


class TerrainGridResult(BaseModel):
    points: list[TerrainGridPoint]


class LinkCheckRequest(BaseModel):
    a: Endpoint
    b: Endpoint
    band: str = "18GHz"
    step_m: float | None = None


class LinkCheckResult(BaseModel):
    distance_km: float
    band: str
    los_pass: bool
    worst_clearance_m: float
    worst_point_km: float
    fresnel_clearance_percent: float
    minimum_clearance_m: float
    score: float
    status: str
    risk_flags: list[str] = Field(default_factory=list)
    terrain_profile: TerrainProfile


class CalloffInfo(BaseModel):
    line: str
    frequency: str
    new_site: str
    new_site_frequency: str
    new_site_band_side: str
    new_site_antenna_diameter_m: float
    new_site_height_m: float
    new_site_azimuth_deg: float
    new_site_tilt_deg: float
    root_site: str
    root_site_frequency: str
    root_site_band_side: str
    root_site_antenna_diameter_m: float
    root_site_height_m: float
    root_site_azimuth_deg: float
    root_site_tilt_deg: float
    distance_km: float


class SingleLinkPlanRequest(BaseModel):
    site_name: str = "NEW_SITE"
    latitude: float
    longitude: float
    tower_height_m: float = 30
    radius_km: float | None = None
    band: str = "AUTO"


class CandidateLink(BaseModel):
    candidate: SiteSearchResult
    link: LinkCheckResult
    rank: int | None = None
    calloff: CalloffInfo | None = None


class PlanSummary(BaseModel):
    total_candidates: int
    accepted: int
    rejected: int
    band: str | None = None
    elapsed_seconds: float = 0
    avg_seconds_per_link: float = 0


class SingleLinkPlanResult(BaseModel):
    best_candidate: CandidateLink | None
    candidate_links: list[CandidateLink]
    rejected_links: list[CandidateLink]
    summary: PlanSummary


class DemDownloadRequest(BaseModel):
    latitude: float
    longitude: float
    radius_km: float = 30


class DemDownloadResult(BaseModel):
    requested_tiles: list[str]
    downloaded_tiles: list[str]
    existing_tiles: list[str]
    failed_tiles: list[str] = Field(default_factory=list)


class WorldCoverDownloadRequest(BaseModel):
    latitude: float
    longitude: float
    radius_km: float = 30


class WorldCoverDownloadResult(BaseModel):
    requested_tiles: list[str]
    downloaded_tiles: list[str]
    existing_tiles: list[str]
    failed_tiles: list[str] = Field(default_factory=list)


class GisDownloadResult(BaseModel):
    dem: DemDownloadResult
    worldcover: WorldCoverDownloadResult


GisDownloadRequest = DemDownloadRequest
