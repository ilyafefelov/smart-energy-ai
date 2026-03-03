"""Tenant isolation checks for dashboard API endpoints."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request

import pytest


BASE_URL = os.getenv("DASHBOARD_BASE_URL", "http://127.0.0.1:3600")


def _build_url(path: str, tenant_id: str | None = None) -> str:
    url = f"{BASE_URL}{path}"
    if tenant_id:
        separator = "&" if "?" in path else "?"
        url = f"{url}{separator}{urllib.parse.urlencode({'tenantId': tenant_id})}"
    return url


def _fetch_json(path: str, tenant_id: str | None = None) -> dict:
    headers = {"Accept": "application/json"}
    if tenant_id:
        headers["X-Tenant-Id"] = tenant_id

    request = urllib.request.Request(_build_url(path, tenant_id), headers=headers)
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def _post_json(path: str, payload: dict, tenant_id: str | None = None) -> dict:
    body = json.dumps(payload).encode("utf-8")
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    if tenant_id:
        headers["X-Tenant-Id"] = tenant_id

    request = urllib.request.Request(_build_url(path, tenant_id), data=body, headers=headers, method="POST")
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def _discover_tenants() -> list[str]:
    payload = _fetch_json("/api/tenants")
    if payload.get("success"):
        tenant_ids = [
            str(item.get("id"))
            for item in payload.get("tenants") or []
            if item.get("id")
        ]
        if tenant_ids:
            return tenant_ids
    return ["client_001_kyiv_mall", "client_002_lviv_office"]


@pytest.fixture(scope="module")
def tenant_ids() -> list[str]:
    try:
        return _discover_tenants()[:2]
    except (urllib.error.URLError, TimeoutError) as exc:
        pytest.skip(f"Dashboard API unavailable at {BASE_URL}: {exc}")


def test_execute_history_no_cross_tenant_leak(tenant_ids: list[str]) -> None:
    if len(tenant_ids) < 2:
        pytest.skip("Need at least two tenants for isolation checks")

    tenant_a, tenant_b = tenant_ids[0], tenant_ids[1]

    execute_payload = {
        "command": "hold",
        "power_kw": 0,
        "reason": "tenant isolation test",
        "user_id": "pytest",
    }

    response_a = _post_json("/api/control/execute", execute_payload, tenant_id=tenant_a)
    response_b = _post_json("/api/control/execute", execute_payload, tenant_id=tenant_b)

    assert response_a.get("success") is True
    assert response_b.get("success") is True
    assert (response_a.get("tenant") or {}).get("id") == tenant_a
    assert (response_b.get("tenant") or {}).get("id") == tenant_b

    history_a = _fetch_json("/api/control/history?limit=20", tenant_id=tenant_a)
    history_b = _fetch_json("/api/control/history?limit=20", tenant_id=tenant_b)

    assert history_a.get("success") is True
    assert history_b.get("success") is True

    rows_a = history_a.get("history") or []
    rows_b = history_b.get("history") or []

    assert all((row.get("tenant_id") == tenant_a) for row in rows_a)
    assert all((row.get("tenant_id") == tenant_b) for row in rows_b)

    assert not any((row.get("tenant_id") == tenant_b) for row in rows_a)
    assert not any((row.get("tenant_id") == tenant_a) for row in rows_b)


def test_tenant_scoped_settings_files_independent(tenant_ids: list[str]) -> None:
    if len(tenant_ids) < 2:
        pytest.skip("Need at least two tenants for isolation checks")

    tenant_a, tenant_b = tenant_ids[0], tenant_ids[1]

    payload_a = {
        "tenantId": tenant_a,
        "general": {
            "siteName": "Tenant A Site",
            "timezone": "Europe/Kiev (GMT+2)",
            "currency": "UAH",
            "notificationsEnabled": True,
        },
        "battery": {
            "capacity": 101,
            "minSOC": 15,
            "maxChargeRate": 50,
            "maxDischargeRate": 50,
        },
        "notifications": {
            "highPrice": True,
            "highPriceThreshold": 13,
            "lowPrice": True,
            "lowPriceThreshold": 7,
            "modelComplete": True,
            "systemAlerts": True,
        },
        "model": {
            "learningRate": 0.0003,
            "batchSize": 64,
            "epochs": 20,
        },
    }

    payload_b = {
        "tenantId": tenant_b,
        "general": {
            "siteName": "Tenant B Site",
            "timezone": "Europe/Kiev (GMT+2)",
            "currency": "UAH",
            "notificationsEnabled": True,
        },
        "battery": {
            "capacity": 202,
            "minSOC": 15,
            "maxChargeRate": 50,
            "maxDischargeRate": 50,
        },
        "notifications": {
            "highPrice": True,
            "highPriceThreshold": 13,
            "lowPrice": True,
            "lowPriceThreshold": 7,
            "modelComplete": True,
            "systemAlerts": True,
        },
        "model": {
            "learningRate": 0.0003,
            "batchSize": 64,
            "epochs": 20,
        },
    }

    save_a = _post_json("/api/settings/save", payload_a, tenant_id=tenant_a)
    save_b = _post_json("/api/settings/save", payload_b, tenant_id=tenant_b)

    assert save_a.get("success") is True
    assert save_b.get("success") is True

    load_a = _fetch_json("/api/settings/load", tenant_id=tenant_a)
    load_b = _fetch_json("/api/settings/load", tenant_id=tenant_b)

    assert load_a.get("success") is True
    assert load_b.get("success") is True

    assert ((load_a.get("settings") or {}).get("general") or {}).get("siteName") == "Tenant A Site"
    assert ((load_b.get("settings") or {}).get("general") or {}).get("siteName") == "Tenant B Site"
    assert ((load_a.get("settings") or {}).get("battery") or {}).get("capacity") == 101
    assert ((load_b.get("settings") or {}).get("battery") or {}).get("capacity") == 202
