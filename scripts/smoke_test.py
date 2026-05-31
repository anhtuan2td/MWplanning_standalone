import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.rf.fresnel import fresnel_clearance
from app.rf.los import check_los
from app.schemas.planning import Endpoint
from app.terrain.profile import generate_profile


def main() -> None:
    a = Endpoint(latitude=16.032, longitude=108.221, ground_elevation_m=10, tower_height_m=30)
    b = Endpoint(latitude=16.0471, longitude=108.2068, ground_elevation_m=12, tower_height_m=40)
    profile = generate_profile(a, b, 100)
    los = check_los(profile)
    fresnel = fresnel_clearance(profile, "18GHz")
    print({"samples": len(profile.distance_m), "los": los, "fresnel": fresnel})


if __name__ == "__main__":
    main()
