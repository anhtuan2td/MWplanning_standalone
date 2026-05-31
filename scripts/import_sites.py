import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.database.session import SessionLocal, init_db
from app.services.sites import import_sites_csv


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_path", type=Path)
    args = parser.parse_args()

    init_db()
    with SessionLocal() as db:
        result = import_sites_csv(db, args.csv_path.read_bytes())
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
