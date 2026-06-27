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
    rain_zone: str | None = None
    antenna_diameter_m: float = Field(default=0.6, gt=0)
    equipment_profile: str | None = None


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
    availability_percent: float = 100
    rain_zone: str = "N"
    fade_margin_db: float = 0
    equipment_profile: str = "SCREENING_FALLBACK"


class AcceptedFilters(BaseModel):
    reject_site_code_contains: str | None = None
    min_site_code_number: int | None = None
    reject_overload: bool = False
    reject_overlink: bool = False


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
    min_radius_km: float | None = None
    band: str = "AUTO"
    rain_zone: str | None = None
    antenna_diameter_m: float | None = Field(default=None, gt=0)
    equipment_profile: str | None = None
    accepted_filters: AcceptedFilters | None = None


class BatchPlanRequest(BaseModel):
    sites: list[SingleLinkPlanRequest] = Field(min_length=1, max_length=500)
    top_n: int = Field(default=3, ge=1, le=20)


class BatchCandidate(BaseModel):
    rank: int
    site_code: str
    distance_km: float
    band: str
    score: float
    status: str
    availability_percent: float
    rain_zone: str
    fade_margin_db: float
    equipment_profile: str
    risk_flags: list[str]
    calloff: CalloffInfo | None = None


class BatchSiteResult(BaseModel):
    site_name: str
    candidates: list[BatchCandidate]
    error: str | None = None
    gis_status: str | None = None
    missing_dem_tiles: list[str] = Field(default_factory=list)
    missing_worldcover_tiles: list[str] = Field(default_factory=list)


class BatchPlanResult(BaseModel):
    results: list[BatchSiteResult]


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
