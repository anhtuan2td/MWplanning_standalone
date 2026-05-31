from pydantic import BaseModel, Field


class SiteOut(BaseModel):
    id: str
    site_code: str
    site_name: str
    latitude: float
    longitude: float
    ground_elevation_m: float
    tower_height_m: float
    available_height_m: float
    overload: int = 0
    diverse_routing: bool = False
    status: str

    model_config = {"from_attributes": True}


class SiteSearchResult(SiteOut):
    distance_km: float
    bearing_deg: float


class ImportResult(BaseModel):
    inserted: int
    updated: int
    skipped: int
    errors: list[str] = Field(default_factory=list)
