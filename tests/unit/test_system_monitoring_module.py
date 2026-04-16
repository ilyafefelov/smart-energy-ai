from src.data_pipeline.system_monitoring import (
    _calculate_system_efficiency,
    _get_inverter_status,
)


def test_calculate_system_efficiency_applies_temperature_and_soc_derating() -> None:
    nominal = _calculate_system_efficiency(50.0, 25.0)
    hot_extreme = _calculate_system_efficiency(95.0, 40.0)
    cold_extreme = _calculate_system_efficiency(10.0, 0.0)

    assert nominal == 0.92
    assert hot_extreme < nominal
    assert cold_extreme < nominal


def test_get_inverter_status_maps_power_flow_sign() -> None:
    assert _get_inverter_status(0.0, 50.0) == "IDLE"
    assert _get_inverter_status(10.0, 50.0) == "CHARGING"
    assert _get_inverter_status(-10.0, 50.0) == "DISCHARGING"