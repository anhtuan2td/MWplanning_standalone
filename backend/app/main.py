from threading import Thread

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.core.config import get_settings
from app.database.session import init_db
from app.terrain.dem_health import audit_dem_directory, write_health_report


settings = get_settings()

app = FastAPI(title=settings.app_name, version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    init_db()
    Thread(target=_audit_dem_health_on_startup, name="dem-health-startup-audit", daemon=True).start()


def _audit_dem_health_on_startup() -> None:
    try:
        results = audit_dem_directory()
        output_path = write_health_report(results)
        counts: dict[str, int] = {}
        for item in results:
            counts[item.status] = counts.get(item.status, 0) + 1
        summary = ", ".join(f"{status}={count}" for status, count in sorted(counts.items())) or "no DEM tiles"
        print(f"DEM health startup audit complete: {summary}; report={output_path}", flush=True)
    except Exception as exc:
        print(f"DEM health startup audit failed: {exc}", flush=True)


app.include_router(router)

if settings.frontend_static_dir.exists():
    app.mount("/", StaticFiles(directory=settings.frontend_static_dir, html=True), name="frontend")
