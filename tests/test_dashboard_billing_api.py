"""Tenant-scoped billing draft integration checks."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

import pytest


BASE_URL = os.getenv("DASHBOARD_BASE_URL", "http://127.0.0.1:3600")


def _request_json(
    path: str,
    *,
    method: str = "GET",
    tenant_id: str | None = None,
    body: dict | None = None,
) -> dict:
    headers = {"Accept": "application/json"}
    if tenant_id:
        headers["X-Tenant-Id"] = tenant_id

    request_data = None
    if body is not None:
        request_data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"

    url = f"{BASE_URL}{path}"
    if tenant_id:
        separator = "&" if "?" in path else "?"
        url = f"{url}{separator}{urllib.parse.urlencode({'tenantId': tenant_id})}"

    request = urllib.request.Request(url, data=request_data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=12) as response:
        return json.loads(response.read().decode("utf-8"))


def _discover_tenants() -> list[str]:
    tenants_response = _request_json("/api/tenants")
    if tenants_response.get("success"):
        tenant_ids = [
            str(item.get("id"))
            for item in tenants_response.get("tenants") or []
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


def test_billing_draft_supports_multi_tenant_usage_capture(tenant_ids: list[str]) -> None:
    # Ensure each tenant emits at least one billable usage event via control execution.
    for index, tenant_id in enumerate(tenant_ids):
        command_payload = {
            "command": "charge" if index % 2 == 0 else "hold",
            "power_kw": 2,
            "duration_minutes": 15,
            "reason": f"billing_test_{tenant_id}",
            "user_id": "pytest-billing",
        }
        execute_response = _request_json(
            "/api/control/execute",
            method="POST",
            tenant_id=tenant_id,
            body=command_payload,
        )
        assert execute_response.get("success") is True

    from_ts = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
    to_ts = datetime.now(timezone.utc).isoformat()

    invoices_by_tenant: dict[str, dict] = {}

    for tenant_id in tenant_ids:
        draft_response = _request_json(
            f"/api/billing/draft?from={urllib.parse.quote(from_ts)}&to={urllib.parse.quote(to_ts)}&includeEvents=true",
            tenant_id=tenant_id,
        )
        assert draft_response.get("success") is True
        assert (draft_response.get("tenant") or {}).get("id") == tenant_id

        invoice = draft_response.get("draft_invoice") or {}
        assert invoice.get("tenant_id") == tenant_id
        assert (invoice.get("summary") or {}).get("event_count", 0) >= 1
        assert "entitlements" in (invoice.get("plan") or {})

        events = invoice.get("events") or []
        assert events, "Expected usage events in draft invoice payload"
        assert all(event.get("tenant_id") == tenant_id for event in events)

        invoices_by_tenant[tenant_id] = invoice

    # Cross-tenant isolation check: each tenant has its own invoice payload and events.
    assert len(invoices_by_tenant) == len(tenant_ids)
    first_tenant, second_tenant = tenant_ids[0], tenant_ids[1]
    assert invoices_by_tenant[first_tenant]["tenant_id"] != invoices_by_tenant[second_tenant]["tenant_id"]
