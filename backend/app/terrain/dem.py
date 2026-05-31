from pathlib import Path

from app.core.config import get_settings


class DemSampler:
    _dataset_cache: dict[Path, list] = {}
    _worldcover_dataset_cache: dict[Path, list] = {}

    def __init__(self, dem_directory: Path | None = None) -> None:
        self.dem_directory = dem_directory or get_settings().dem_directory

    @classmethod
    def clear_cache(cls) -> None:
        for datasets in cls._dataset_cache.values():
            for dataset in datasets:
                try:
                    dataset.close()
                except Exception:
                    continue
        cls._dataset_cache.clear()
        for datasets in cls._worldcover_dataset_cache.values():
            for dataset in datasets:
                try:
                    dataset.close()
                except Exception:
                    continue
        cls._worldcover_dataset_cache.clear()

    def _load(self):
        cache_key = self.dem_directory.resolve()
        if cache_key in self._dataset_cache:
            return self._dataset_cache[cache_key]

        try:
            import rasterio
        except ImportError:
            self._dataset_cache[cache_key] = []
            return self._dataset_cache[cache_key]

        datasets = []
        for path in self.dem_directory.glob("*.tif*"):
            try:
                datasets.append(rasterio.open(path))
            except Exception:
                continue
        self._dataset_cache[cache_key] = datasets
        return datasets

    def _load_worldcover(self):
        worldcover_directory = get_settings().worldcover_directory
        cache_key = worldcover_directory.resolve()
        if cache_key in self._worldcover_dataset_cache:
            return self._worldcover_dataset_cache[cache_key]

        try:
            import rasterio
        except ImportError:
            self._worldcover_dataset_cache[cache_key] = []
            return self._worldcover_dataset_cache[cache_key]

        datasets = []
        if worldcover_directory.exists():
            for path in worldcover_directory.glob("*.tif*"):
                try:
                    datasets.append(rasterio.open(path))
                except Exception:
                    continue
        self._worldcover_dataset_cache[cache_key] = datasets
        return datasets

    def _sample_worldcover(self, latitude: float, longitude: float) -> int | None:
        for dataset in self._load_worldcover():
            try:
                bounds = dataset.bounds
                if bounds.left <= longitude <= bounds.right and bounds.bottom <= latitude <= bounds.top:
                    value = next(dataset.sample([(longitude, latitude)]))[0]
                    if value is None:
                        return None
                    return int(value)
            except Exception:
                continue
        return None

    def _cover_height_offset(self, cover_class: int | None) -> float:
        if cover_class is None:
            return 0.0
        return get_settings().worldcover_height_offsets.get(cover_class, 0.0)

    def sample_surface(self, latitude: float, longitude: float, fallback_m: float = 0.0) -> float:
        terrain_elevation = self.sample(latitude, longitude, fallback_m)
        if not get_settings().worldcover_apply_height_offsets:
            return terrain_elevation
        cover_class = self._sample_worldcover(latitude, longitude)
        return terrain_elevation + self._cover_height_offset(cover_class)

    def sample(self, latitude: float, longitude: float, fallback_m: float = 0.0) -> float:
        for dataset in self._load():
            try:
                bounds = dataset.bounds
                if bounds.left <= longitude <= bounds.right and bounds.bottom <= latitude <= bounds.top:
                    value = next(dataset.sample([(longitude, latitude)]))[0]
                    return float(value)
            except Exception:
                continue
        return fallback_m
