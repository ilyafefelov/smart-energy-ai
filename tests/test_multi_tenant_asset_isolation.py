"""Tests for tenant-level asset isolation and namespace determinism."""

from __future__ import annotations

from typing import Any, Dict, List

from src.assets.multi_tenant.asset_factory import (
    _build_tenant_descriptor,
    _normalize_tenant_id,
    _sanitize_shared_input,
    create_client_specific_asset,
    generate_client_assets,
)


def _sample_config(client_id: str) -> Dict[str, Any]:
    return {
        "id": client_id,
        "name": "Sample Client",
        "type": "commercial",
        "energy_system": {
            "battery_capacity_kwh": 100.0,
            "solar_capacity_kw": 40.0,
            "peak_load_kw": 70.0,
            "base_load_kw": 20.0,
            "load_profile": "commercial",
        },
        "economic_params": {
            "electricity_tariff": 0.12,
            "feed_in_tariff": 0.08,
        },
    }


def test_normalize_tenant_id_is_deterministic() -> None:
    assert _normalize_tenant_id("Client-001 Kyiv Mall") == "client_001_kyiv_mall"
    assert _normalize_tenant_id("client_001_kyiv_mall") == "client_001_kyiv_mall"


def test_tenant_descriptor_contains_isolated_namespaces() -> None:
    descriptor = _build_tenant_descriptor(_sample_config("Client-001 Kyiv Mall"))

    assert descriptor["normalized_id"] == "client_001_kyiv_mall"
    assert descriptor["tenant_namespace"] == "tenant/client_001_kyiv_mall"
    assert descriptor["storage_namespace"] == "tenants/client_001_kyiv_mall"
    assert descriptor["asset_name"] == "client_data_client_001_kyiv_mall"


def test_sanitize_shared_input_removes_tenant_columns() -> None:
    class StubFrame:
        def __init__(self, columns: List[str]) -> None:
            self.columns = columns

        def drop(self, values: List[str]):
            return StubFrame([column for column in self.columns if column not in values])

    source = StubFrame(
        [
            "timestamp",
            "client_id",
            "tenant_namespace",
            "value",
        ]
    )

    sanitized = _sanitize_shared_input(source)

    assert "client_id" not in sanitized.columns
    assert "tenant_namespace" not in sanitized.columns
    assert "value" in sanitized.columns


def test_client_asset_uses_tenant_key_prefix_and_metadata() -> None:
    asset_def = create_client_specific_asset(_sample_config("Client-001 Kyiv Mall"))

    key = next(iter(asset_def.keys))
    assert key.path[0] == "tenant"
    assert key.path[1] == "client_001_kyiv_mall"
    assert key.path[2] == "client_data_client_001_kyiv_mall"

    metadata = asset_def.metadata_by_key[key]
    assert metadata["tenant_namespace"] == "tenant/client_001_kyiv_mall"
    assert metadata["storage_namespace"] == "tenants/client_001_kyiv_mall"


def test_generate_client_assets_skips_duplicate_normalized_tenants(monkeypatch) -> None:
    configs: List[Dict[str, Any]] = [
        _sample_config("Client-001 Kyiv Mall"),
        _sample_config("client_001_kyiv_mall"),
        _sample_config("Client-002 Lviv Office"),
    ]

    monkeypatch.setattr(
        "src.assets.multi_tenant.asset_factory.load_customer_configurations",
        lambda: configs,
    )

    assets = generate_client_assets()

    # Two unique normalized IDs should produce two isolated assets.
    assert len(assets) == 2
