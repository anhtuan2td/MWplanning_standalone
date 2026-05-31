import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.terrain.dem import DemSampler


def main() -> None:
    sampler = DemSampler()
    value = sampler.sample(16.032, 108.221, fallback_m=0)
    print({"sample_lat": 16.032, "sample_lon": 108.221, "elevation_m": value})


if __name__ == "__main__":
    main()
