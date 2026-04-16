from datetime import datetime

from src.data_pipeline import client_load_solar_simulation as simulation_module


def test_calculate_solar_generation_reflects_irradiance_and_cloud_cover() -> None:
    config = {"solar_capacity_kw": 100.0}

    assert simulation_module._calculate_solar_generation(config, 0.0, 0.0) == 0.0

    clearer_output = simulation_module._calculate_solar_generation(config, 800.0, 10.0)
    cloudier_output = simulation_module._calculate_solar_generation(config, 800.0, 90.0)

    assert clearer_output > 0.0
    assert cloudier_output < clearer_output


def test_calculate_load_consumption_uses_profile_shape_without_random_noise(monkeypatch) -> None:
    monkeypatch.setattr(simulation_module.np.random, "normal", lambda *args, **kwargs: 0.0)
    config = {
        "base_load_kw": 30.0,
        "peak_load_kw": 120.0,
        "load_profile": "office",
    }

    business_hour = simulation_module._calculate_load_consumption(config, datetime(2026, 3, 3, 10, 0, 0))
    overnight = simulation_module._calculate_load_consumption(config, datetime(2026, 3, 3, 2, 0, 0))
    weekend = simulation_module._calculate_load_consumption(config, datetime(2026, 3, 7, 10, 0, 0))

    assert business_hour > overnight
    assert business_hour > weekend
    assert overnight >= 15.0


def test_calculate_load_consumption_respects_minimum_floor(monkeypatch) -> None:
    monkeypatch.setattr(simulation_module.np.random, "normal", lambda *args, **kwargs: -10.0)
    config = {
        "base_load_kw": 40.0,
        "peak_load_kw": 80.0,
        "load_profile": "residential",
    }

    load_actual = simulation_module._calculate_load_consumption(config, datetime(2026, 3, 3, 3, 0, 0))

    assert load_actual == 20.0