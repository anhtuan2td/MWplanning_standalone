from app.services.equipment import FIELDS, list_equipment_profiles


def test_default_racom_catalog_is_available():
    profiles = list_equipment_profiles()
    profile = next(item for item in profiles if item["profile_id"] == "RACOM_RAy3_24_56_256QAM")
    assert profile["rx_threshold_dbm"] == -65
    assert profile["tx_power_max_dbm"] == 10
    assert tuple(profile) == FIELDS
