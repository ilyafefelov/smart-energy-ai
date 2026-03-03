"""Endpoint-level checks for history/metrics economics provenance consistency."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request

import pytest


BASE_URL = os.getenv("DASHBOARD_BASE_URL", "http://127.0.0.1:3600")


def _fetch_json(path: str, tenant_id: str | None = None) -> dict:
    headers = {"Accept": "application/json"}
    if tenant_id:
      headers["X-Tenant-Id"] = tenant_id

    url = f"{BASE_URL}{path}"
    if tenant_id:
      separator = "&" if "?" in path else "?"
      url = f"{url}{separator}{urllib.parse.urlencode({'tenantId': tenant_id})}"

    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def _discover_tenants() -> list[str]:
    tenants_response = _fetch_json("/api/tenants")
    if tenants_response.get("success"):
        tenant_ids = [
            str(tenant.get("id"))
            for tenant in tenants_response.get("tenants") or []
            if tenant.get("id")
        ]
        if tenant_ids:
            return tenant_ids
    return ["client_001_kyiv_mall", "client_002_lviv_office"]


@pytest.fixture(scope="module")
def api_payloads() -> tuple[dict, dict]:
    try:
        history = _fetch_json("/api/history")
        metrics = _fetch_json("/api/metrics")
        return history, metrics
    except (urllib.error.URLError, TimeoutError) as exc:
        pytest.skip(f"Dashboard API unavailable at {BASE_URL}: {exc}")


@pytest.fixture(scope="module")
def tenant_ids() -> list[str]:
    try:
        return _discover_tenants()
    except (urllib.error.URLError, TimeoutError) as exc:
        pytest.skip(f"Dashboard API unavailable at {BASE_URL}: {exc}")


@pytest.fixture(scope="module")
def tenant_payloads(tenant_ids: list[str]) -> dict[str, tuple[dict, dict]]:
    scoped_payloads: dict[str, tuple[dict, dict]] = {}
    for tenant_id in tenant_ids[:2]:
        history = _fetch_json("/api/history", tenant_id=tenant_id)
        metrics = _fetch_json("/api/metrics", tenant_id=tenant_id)
        scoped_payloads[tenant_id] = (history, metrics)
    return scoped_payloads


def test_history_metrics_source_alignment(api_payloads: tuple[dict, dict]) -> None:
    history, metrics = api_payloads

    assert history.get("success") is True
    assert metrics.get("success") is True

    history_source = (history.get("source") or {}).get("economics_source")
    metrics_source = (metrics.get("source") or {}).get("economics_source")
    assert history_source is not None
    assert metrics_source == history_source


def test_history_value_sanity_when_canonical(api_payloads: tuple[dict, dict]) -> None:
    history, _ = api_payloads
    economics_source = (history.get("source") or {}).get("economics_source")
    if economics_source != "optimization_history_db":
        pytest.skip(f"Canonical source not active (economics_source={economics_source})")

    rows = history.get("data") or []
    assert rows, "Expected non-empty history rows when canonical source is active"

    first = rows[0]
    baseline = float(first.get("cost_baseline") or 0)
    optimized = float(first.get("cost_optimized") or 0)
    savings = float(first.get("savings") or 0)

    assert baseline >= 0
    assert optimized >= 0
    assert abs((baseline - optimized) - savings) < 0.2


def test_tenant_scoped_endpoints_echo_tenant_metadata(tenant_payloads: dict[str, tuple[dict, dict]]) -> None:
    for tenant_id, (history, metrics) in tenant_payloads.items():
        assert history.get("success") is True
        assert metrics.get("success") is True

        assert (history.get("tenant") or {}).get("id") == tenant_id
        assert (metrics.get("tenant") or {}).get("id") == tenant_id

        assert (history.get("tenant") or {}).get("validated") is True
        assert (metrics.get("tenant") or {}).get("validated") is True

        assert (history.get("source") or {}).get("tenant_filter_applied") is True
        assert (metrics.get("source") or {}).get("tenant_filter_applied") is True


def test_invalid_tenant_rejected_with_stable_envelope() -> None:
    response = _fetch_json("/api/metrics/dashboard", tenant_id="invalid_test_tenant")

    assert response.get("success") is False
    assert (response.get("error") or {}).get("code") == "INVALID_TENANT"
    assert (response.get("tenant") or {}).get("validated") is False
