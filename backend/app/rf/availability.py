from math import exp, log, log10, pi, sin, radians

from app.core.config import get_planner_config
from app.services.equipment import equipment_profile as load_equipment_profile


def _antenna_gain_db(frequency_ghz: float, diameter_m: float, efficiency: float) -> float:
    wavelength_m = 0.299792458 / frequency_ghz
    return 10 * log10(efficiency * (pi * diameter_m / wavelength_m) ** 2)


def _p838_coefficients(frequency_ghz: float) -> tuple[float, float]:
    # Horizontal-polarisation interpolation points used by P.838.
    table = {6: (0.000705, 1.590), 11: (0.01772, 1.214), 15: (0.04481, 1.123), 18: (0.07078, 1.081), 24: (0.1571, 1.021)}
    nearest = min(table, key=lambda value: abs(value - frequency_ghz))
    return table[nearest]


def _rain_attenuation_001(distance_km: float, frequency_ghz: float, rain_rate: float) -> float:
    k, alpha = _p838_coefficients(frequency_ghz)
    gamma_r = k * rain_rate**alpha
    denominator = 1 + 0.477 * distance_km**0.633 * rain_rate**0.073 * frequency_ghz**0.123 - 10.579 * (1 - exp(-0.024 * distance_km))
    effective_distance = distance_km / max(1.0, denominator)
    return gamma_r * effective_distance


def _attenuation_at_percent(a001: float, percent: float, latitude: float = 16.0) -> float:
    beta = 0.0 if abs(latitude) >= 36 else -0.005 * (36 - abs(latitude))
    exponent = -(0.655 + 0.033 * log(max(percent, 0.0001)) - 0.045 * log(max(a001, 0.001)) - beta * (1 - percent) * sin(radians(abs(latitude))))
    return a001 * (percent / 0.01) ** exponent


def estimate_availability_details(
    distance_km: float,
    band: str,
    rain_zone: str | None,
    antenna_diameter_m: float = 0.6,
    latitude: float = 16.0,
    equipment_profile: str | None = None,
) -> dict[str, float | str]:
    config = get_planner_config().get("availability", {})
    zone = (rain_zone or config.get("default_rain_zone", "N")).strip().upper()
    rates = config.get("rain_rates_mm_h", {})
    if zone not in rates:
        zone = str(config.get("default_rain_zone", "N")).upper()
    rain_rate = float(rates.get(zone, 95))
    frequency_ghz = float(band.upper().replace("GHZ", ""))
    profile_name, profile = load_equipment_profile(equipment_profile)

    if profile and abs(float(profile["band_ghz"]) - frequency_ghz) < 0.6:
        efficiency = float(config.get("antenna_efficiency", 0.6))
        gain = _antenna_gain_db(frequency_ghz, antenna_diameter_m, efficiency)
        fspl = 92.45 + 20 * log10(max(distance_km, 0.001)) + 20 * log10(frequency_ghz)
        received = float(profile["tx_power_max_dbm"]) + 2 * gain - fspl - float(config.get("implementation_loss_db", 2))
        fade_margin = received - float(profile["rx_threshold_dbm"])
        a001 = _rain_attenuation_001(distance_km, frequency_ghz, rain_rate)
        if fade_margin <= 0:
            outage = 5.0
        elif fade_margin >= _attenuation_at_percent(a001, 0.0001, latitude):
            outage = 0.0001
        else:
            low, high = 0.0001, 5.0
            for _ in range(50):
                mid = (low + high) / 2
                if _attenuation_at_percent(a001, mid, latitude) > fade_margin:
                    low = mid
                else:
                    high = mid
            outage = high
        availability = 100 - outage
        return {"availability_percent": round(availability, 5), "rain_zone": zone, "fade_margin_db": round(fade_margin, 2), "equipment_profile": profile_name}

    severity = (rain_rate / 95.0) * (frequency_ghz / 18.0) ** 1.35 * max(distance_km, 0.0) ** 1.15
    availability = 100.0 - min(5.0, 0.0035 * severity)
    return {"availability_percent": round(availability, 5), "rain_zone": zone, "fade_margin_db": 0.0, "equipment_profile": "SCREENING_FALLBACK"}


def estimate_availability(distance_km: float, band: str, rain_zone: str | None) -> tuple[float, str]:
    details = estimate_availability_details(distance_km, band, rain_zone)
    return float(details["availability_percent"]), str(details["rain_zone"])


def availability_score(availability_percent: float, weight: float, target_percent: float = 99.99) -> float:
    outage = max(0.0, 100.0 - availability_percent)
    target_outage = max(0.0001, 100.0 - target_percent)
    return weight * exp(-max(0.0, outage - target_outage) / target_outage)
