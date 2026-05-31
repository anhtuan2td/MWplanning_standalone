from pathlib import Path

from app.core.config import get_settings


class DemSampler:
    _dataset_cache: dict[Path, list] = {}

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
