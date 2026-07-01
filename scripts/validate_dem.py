import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.terrain.dem_health import audit_dem_directory, latest_health_report_path, write_health_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit DEM tiles and write a tile-level health report.")
    parser.add_argument("--tiles", nargs="*", help="Optional DEM tile names to audit, for example N16E108 N15E107.")
    parser.add_argument("--grid-size", type=int, default=5, help="Sample grid size per tile. Default: 5 for 25 samples.")
    parser.add_argument("--output", type=Path, default=latest_health_report_path(), help="CSV report path.")
    args = parser.parse_args()

    results = audit_dem_directory(tiles=args.tiles, grid_size=args.grid_size)
    output = write_health_report(results, args.output)
    counts: dict[str, int] = {}
    for item in results:
        counts[item.status] = counts.get(item.status, 0) + 1
    print({"output": str(output), "tiles": len(results), "status_counts": counts})
    for item in results:
        if item.status != "OK":
            print({"tile": item.tile, "status": item.status, "reason": item.reason})


if __name__ == "__main__":
    main()
