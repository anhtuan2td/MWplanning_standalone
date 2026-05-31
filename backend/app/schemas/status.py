from pydantic import BaseModel, Field


class SystemStatus(BaseModel):
    total_sites: int
    total_mw_links: int = 0
    site_status_counts: dict[str, int] = Field(default_factory=dict)
    dem_tiles: list[str] = Field(default_factory=list)
    dem_regions: list[str] = Field(default_factory=list)
    dem_unmapped_tiles: list[str] = Field(default_factory=list)
    worldcover_maps: list[str] = Field(default_factory=list)
    worldcover_regions: list[str] = Field(default_factory=list)
    worldcover_unmapped_maps: list[str] = Field(default_factory=list)
