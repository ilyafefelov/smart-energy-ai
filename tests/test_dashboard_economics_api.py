"""Endpoint-level checks for history/metrics economics provenance consistency."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

import pytest


BASE_URL = os.getenv("DASHBOARD_BASE_URL", "http://127.0.0.1:3600")


def _fetch_json(path: str) -> dict:
    request = urllib.request.Request(f"{BASE_URL}{path}", headers={"Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


@pytest.fixture(scope="module")
def api_payloads() -> tuple[dict, dict]:
    try:
        history = _fetch_json("/api/history")
        metrics = _fetch_json("/api/metrics")
        return history, metrics
    except (urllib.error.URLError, TimeoutError) as exc:
        pytest.skip(f"Dashboard API unavailable at {BASE_URL}: {exc}")


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
