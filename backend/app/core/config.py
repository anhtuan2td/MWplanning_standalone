from __future__ import annotations

import sys
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def _resource_root() -> Path:
    return Path(sys._MEIPASS) if _is_frozen() else PROJECT_ROOT


def _runtime_root() -> Path:
    return Path(sys.executable).resolve().parent if _is_frozen() else PROJECT_ROOT


def _ensure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _default_data_directory() -> Path:
    return _ensure_directory(_runtime_root() / "data")


def _default_database_url() -> str:
    database_path = _default_data_directory() / "mwplanner.db"
    return f"sqlite:///{database_path.as_posix()}"


class Settings(BaseSettings):
    app_name: str = "MW Pre-planning Lite"
    # Prefer explicit env override. If running frozen, default to a local SQLite DB.
    database_url: str = Field(
        default_factory=lambda: os.environ.get(
            "MW_DATABASE_URL"
        )
        or (_default_database_url() if _is_frozen() else "postgresql+psycopg://mw:mw@postgres:5432/mwplanner")
    )
    planner_config_path: Path = _resource_root() / "config" / "planner_config.yaml"
    dem_directory: Path = _default_data_directory() / "dem"
    mw_links_directory: Path = _default_data_directory() / "mw_links"
    default_mw_links_file: Path = _resource_root() / "data" / "mw_links" / "existing_links.csv"
    frontend_static_dir: Path = _resource_root() / "frontend" / "dist"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"])

    model_config = SettingsConfigDict(
        env_file=_resource_root() / ".env",
        env_prefix="MW_",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


@lru_cache
def get_planner_config() -> dict[str, Any]:
    path = get_settings().planner_config_path
    if not path.exists():
        raise FileNotFoundError(f"Planner config not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def get_band_config(band: str) -> dict[str, Any]:
    config = get_planner_config()
    bands = config.get("bands", {})
    if band not in bands:
        raise ValueError(f"Unsupported band: {band}")
    return bands[band]
