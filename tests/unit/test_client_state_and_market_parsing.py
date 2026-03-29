"""Regression tests for client-state provenance, config normalization, and OREE table parsing."""

from datetime import date, datetime, timedelta
import json

from bs4 import BeautifulSoup
import polars as pl

from src.assets.core import client_state as client_state_module
from src.assets.core.client_state import (
    CONFIG_STATE_SOURCE,
    SIMULATOR_STATE_SOURCE,
    _generate_client_state,
    _load_operational_battery_state,
    _normalize_client_config,
)
from src.assets.core.market import (
    _extract_oree_price_rows,
    _extract_prices_from_data_view_content,
    _parse_decimal,
    _parse_hour_value,
)


def test_normalize_client_config_supports_nested_energy_system():
    raw = {
        "id": "client_nested",
        "type": "commercial",
        "location": {"lat": 50.45, "lon": 30.52},
        "energy_system": {
            "battery_type": "LFP_280Ah",
            "battery_capacity_kwh": 300.0,
            "solar_capacity_kw": 140.0,
            "peak_load_kw": 240.0,
            "base_load_kw": 60.0,
            "load_profile": "commercial",
        },
    }

    normalized = _normalize_client_config(raw)

    assert normalized is not None
    assert normalized["id"] == "client_nested"
    assert normalized["battery_capacity_kwh"] == 300.0
    assert normalized["solar_capacity_kw"] == 140.0
    assert normalized["peak_load_kw"] == 240.0
    assert normalized["base_load_kw"] == 60.0
    assert normalized["load_profile"] == "commercial"


def test_generate_client_state_handles_normalized_nested_config():
    raw = {
        "id": "client_nested",
        "type": "office",
        "energy_system": {
            "battery_type": "NMC_LG_Chem",
            "battery_capacity_kwh": 180.0,
            "solar_capacity_kw": 90.0,
            "peak_load_kw": 120.0,
            "base_load_kw": 30.0,
            "load_profile": "office",
        },
    }
    config = _normalize_client_config(raw)

    now = datetime(2026, 3, 3, 0, 0, 0)
    weather = pl.DataFrame(
        {
            "timestamp": [now, now + timedelta(hours=1)],
            "solar_radiation": [250.0, 500.0],
            "cloudcover": [40.0, 35.0],
            "temperature": [12.0, 13.0],
        }
    )
    market = pl.DataFrame(
        {
            "timestamp": [now, now + timedelta(hours=1)],
            "price_eur_mwh": [45.0, 80.0],
        }
    )

    rows = _generate_client_state(config, weather, market)

    assert len(rows) == 2
    assert all(row["client_id"] == "client_nested" for row in rows)
    assert all(0 <= row["battery_soc"] <= 100 for row in rows)


def test_load_operational_battery_state_prefers_simulator_backed_file(tmp_path, monkeypatch):
    tenant_dir = tmp_path / "dashboard" / "data" / "tenants" / "client_nested"
    tenant_dir.mkdir(parents=True)
    (tenant_dir / "battery_state.json").write_text(
        json.dumps(
            {
                "soc": 81.5,
                "voltage": 412.4,
                "current": 3.2,
                "temperature": 26.1,
                "cycles": 1111,
                "health": 97.4,
                "lastUpdate": "2026-03-07T10:15:00Z",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(client_state_module, "REPO_ROOT", tmp_path)

    state = _load_operational_battery_state({"tenant_id": "client_nested"})

    assert state["source"] == SIMULATOR_STATE_SOURCE
    assert state["state_source"] == "simulator_backed_telemetry"
    assert state["state_source_detail"] == "dashboard/data/tenants/client_nested/battery_state.json"
    assert state["telemetry_classification"] == "simulated_operational_telemetry"


def test_generate_client_state_marks_config_fallback_when_simulator_state_missing(tmp_path, monkeypatch):
    raw = {
        "id": "client_nested",
        "type": "office",
        "energy_system": {
            "battery_type": "NMC_LG_Chem",
            "battery_capacity_kwh": 180.0,
            "solar_capacity_kw": 90.0,
            "peak_load_kw": 120.0,
            "base_load_kw": 30.0,
            "load_profile": "office",
        },
    }
    config = _normalize_client_config(raw)
    now = datetime(2026, 3, 3, 0, 0, 0)
    weather = pl.DataFrame(
        {
            "timestamp": [now],
            "solar_radiation": [0.0],
            "cloudcover": [0.0],
            "temperature": [12.0],
        }
    )
    market = pl.DataFrame(
        {
            "timestamp": [now],
            "price_eur_mwh": [55.0],
        }
    )

    monkeypatch.setattr(client_state_module, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(client_state_module, "_simulate_battery_behavior", lambda *args, **kwargs: ("IDLE", 0.0))

    rows = _generate_client_state(config, weather, market)

    assert rows[0]["source"] == CONFIG_STATE_SOURCE
    assert rows[0]["state_source"] == "config_fallback"
    assert rows[0]["state_source_detail"] == "synthetic_config_defaults"
    assert rows[0]["telemetry_classification"] == "fabricated_training_scaffolding"


def test_extract_oree_price_rows_parses_table_without_price_table_class():
    table_rows = "\n".join(
        f"<tr><td>{hour:02d}:00</td><td>{1800 + hour},5</td><td>{1000 + hour}</td></tr>"
        for hour in range(24)
    )
    html = f"""
    <html><body>
      <table>
        <tr><th>Hour</th><th>Price UAH/MWh</th><th>Volume</th></tr>
        {table_rows}
      </table>
    </body></html>
    """

    parsed = _extract_oree_price_rows(BeautifulSoup(html, "html.parser"), date(2026, 3, 3))

    assert len(parsed) == 24
    assert parsed[0]["timestamp"].hour == 0
    assert parsed[-1]["timestamp"].hour == 23
    assert parsed[0]["source"] == "OREE"
    assert abs(parsed[0]["price_uah_mwh"] / 40.0 - parsed[0]["price_eur_mwh"]) < 1e-9


def test_numeric_and_hour_parsers_handle_localized_values():
    assert _parse_hour_value("00:00-01:00") == 0
    assert _parse_hour_value("23") == 23
    assert _parse_decimal("1 234,56 UAH") == 1234.56
    assert _parse_decimal("98.75") == 98.75


def test_extract_prices_from_data_view_content_parses_target_day():
        content_html = """
        <table>
            <tr><th>Date</th><th>1</th><th>2</th><th>3</th><th>4</th></tr>
            <tr><td>02.03.2026</td><td>5000.00</td><td>5200.00</td><td>5400.00</td><td>5600.00</td></tr>
            <tr><td>03.03.2026</td><td>6000.00</td><td>6200.00</td><td>6400.00</td><td>6600.00</td></tr>
        </table>
        """

        rows = _extract_prices_from_data_view_content(content_html, date(2026, 3, 3))

        assert len(rows) == 4
        assert rows[0]["timestamp"].hour == 0
        assert rows[-1]["timestamp"].hour == 3
        assert rows[0]["source"] == "OREE_DATA_VIEW"
        assert rows[0]["price_uah_mwh"] == 6000.0
        assert abs(rows[0]["price_eur_mwh"] - 150.0) < 1e-9
