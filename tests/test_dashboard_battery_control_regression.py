"""Regression checks for battery control simulation, strategy context, and decision trace metadata."""

from __future__ import annotations

import json
import os
import re
import time
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


def _fetch_json(path: str, tenant_id: str | None = None, timeout: int = 20) -> dict:
    headers = {"Accept": "application/json"}
    if tenant_id:
        headers["X-Tenant-Id"] = tenant_id

    request = urllib.request.Request(_build_url(path, tenant_id), headers=headers)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _post_json(path: str, payload: dict, tenant_id: str | None = None, timeout: int = 20) -> dict:
    body = json.dumps(payload).encode("utf-8")
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    if tenant_id:
        headers["X-Tenant-Id"] = tenant_id

    request = urllib.request.Request(_build_url(path, tenant_id), data=body, headers=headers, method="POST")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _discover_tenant() -> str:
    payload = _fetch_json("/api/tenants")
    if payload.get("success"):
        for tenant in payload.get("tenants") or []:
            tenant_id = str(tenant.get("id") or "").strip()
            if tenant_id:
                return tenant_id
    return "client_001_kyiv_mall"


@pytest.fixture(scope="module")
def tenant_id() -> str:
    try:
        return _discover_tenant()
    except (urllib.error.URLError, TimeoutError) as exc:
        pytest.skip(f"Dashboard API unavailable at {BASE_URL}: {exc}")


@pytest.mark.integration
def test_battery_soc_progression_for_charge_and_discharge(tenant_id: str) -> None:
    sync_response = _post_json(
        "/api/battery/simulate",
        {
            "action": "setSoc",
            "socPercent": 50,
        },
        tenant_id=tenant_id,
    )
    assert sync_response.get("success") is True

    before_payload = _fetch_json("/api/battery/simulate", tenant_id=tenant_id)
    assert before_payload.get("success") is True
    before_soc = float((before_payload.get("battery") or {}).get("socPercentage") or 0)

    charge_response = _post_json(
        "/api/control/execute",
        {
            "command": "charge",
            "power_kw": 3.0,
            "reason": "pytest regression charge",
            "user_id": "pytest",
        },
        tenant_id=tenant_id,
    )
    assert charge_response.get("success") is True

    time.sleep(1.1)
    after_charge_payload = _fetch_json("/api/battery/simulate", tenant_id=tenant_id)
    assert after_charge_payload.get("success") is True
    after_charge_soc = float((after_charge_payload.get("battery") or {}).get("socPercentage") or 0)

    assert after_charge_soc > before_soc, (
        f"Expected SoC increase after charge command: before={before_soc}, after={after_charge_soc}"
    )

    discharge_response = _post_json(
        "/api/control/execute",
        {
            "command": "discharge",
            "power_kw": -3.0,
            "reason": "pytest regression discharge",
            "user_id": "pytest",
        },
        tenant_id=tenant_id,
    )
    assert discharge_response.get("success") is True

    time.sleep(1.1)
    after_discharge_payload = _fetch_json("/api/battery/simulate", tenant_id=tenant_id)
    assert after_discharge_payload.get("success") is True
    after_discharge_soc = float((after_discharge_payload.get("battery") or {}).get("socPercentage") or 0)

    assert after_discharge_soc < after_charge_soc, (
        "Expected SoC decrease after discharge command: "
        f"after_charge={after_charge_soc}, after_discharge={after_discharge_soc}"
    )


@pytest.mark.integration
def test_strategy_context_is_exposed_in_battery_and_recommendation_endpoints(tenant_id: str) -> None:
    battery_payload = _fetch_json("/api/battery/simulate", tenant_id=tenant_id)
    assert battery_payload.get("success") is True

    battery = battery_payload.get("battery") or {}
    assert battery.get("optimization_strategy") is not None
    assert battery.get("load_profile_type") is not None

    weights = battery.get("strategy_weights") or {}
    assert isinstance(weights, dict)
    assert float(weights.get("cost") or 0) >= 0
    assert float(weights.get("batteryHealth") or 0) >= 0
    assert float(weights.get("renewableUse") or 0) >= 0
    assert float(weights.get("reliability") or 0) >= 0

    recommendation_payload = _fetch_json("/api/dagster/recommendation", tenant_id=tenant_id)
    if "success" in recommendation_payload:
        assert recommendation_payload.get("success") is True
    assert recommendation_payload.get("recommendation") is not None

    strategy_context = recommendation_payload.get("strategy_context") or {}
    assert strategy_context.get("optimization_strategy") is not None
    assert strategy_context.get("load_profile_type") is not None

    recommendation = recommendation_payload.get("recommendation") or {}
    assert recommendation.get("action") is not None
    assert recommendation.get("action_kw") is not None
    assert "strategy_adjusted" in recommendation


@pytest.mark.integration
def test_control_history_exposes_decision_trace_fields(tenant_id: str) -> None:
    execute_response = _post_json(
        "/api/control/execute",
        {
            "command": "auto",
            "power_kw": 2.5,
            "reason": "pytest decision trace auto",
            "user_id": "pytest",
        },
        tenant_id=tenant_id,
    )
    assert execute_response.get("success") is True

    hold_response = _post_json(
        "/api/control/execute",
        {
            "command": "hold",
            "power_kw": 0,
            "reason": "pytest decision trace hold",
            "user_id": "pytest",
        },
        tenant_id=tenant_id,
    )
    assert hold_response.get("success") is True

    history_payload = _fetch_json("/api/control/history?limit=20&since_hours=24", tenant_id=tenant_id)
    assert history_payload.get("success") is True

    entries = history_payload.get("history") or []
    assert entries, "Expected non-empty decision trace history"

    # Validate the newest rows include trace metadata required by the timeline UI.
    first = entries[0]
    assert first.get("requested_command") is not None
    assert first.get("resolved_command") is not None
    assert first.get("decision_source") is not None
    assert first.get("optimization_strategy") is not None
    assert first.get("load_profile_type") is not None
    assert "strategy_weights" in first


@pytest.mark.integration
def test_dagster_schedule_contract_uses_clock_hour_and_freshness_sla(tenant_id: str) -> None:
    payload = _fetch_json("/api/dagster/recommendation", tenant_id=tenant_id)
    assert payload.get("status") == "success"

    source_metadata = payload.get("source_metadata") or {}
    assert int(source_metadata.get("dagster_snapshot_max_age_minutes") or 0) == 15

    schedule = ((payload.get("schedule_24h") or {}).get("schedule") or [])
    assert isinstance(schedule, list)
    assert len(schedule) > 0

    for row in schedule[:24]:
        hour = int(row.get("hour") or 0)
        assert 0 <= hour <= 23

        time_label = str(row.get("time") or "")
        assert re.match(r"^\d{2}:00$", time_label), f"Expected clock-hour format HH:00, got '{time_label}'"

        action = str(row.get("recommended_action") or "")
        assert action in {"BUY", "SELL", "HOLD"}
