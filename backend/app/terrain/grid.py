from app.schemas.planning import TerrainGridPoint, TerrainGridRequest, TerrainGridResult
from app.terrain.dem import DemSampler


def generate_grid(request: TerrainGridRequest) -> TerrainGridResult:
    rows = min(max(request.rows, 2), 24)
    cols = min(max(request.cols, 2), 24)
    sampler = DemSampler()
    points: list[TerrainGridPoint] = []
    for row in range(rows):
        lat = request.south + (request.north - request.south) * row / (rows - 1)
        for col in range(cols):
            lon = request.west + (request.east - request.west) * col / (cols - 1)
            points.append(
                TerrainGridPoint(
                    latitude=round(lat, 6),
                    longitude=round(lon, 6),
                    elevation_m=round(sampler.sample(lat, lon, fallback_m=0), 1),
                )
            )
    return TerrainGridResult(points=points)
