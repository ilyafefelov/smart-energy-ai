"""Unit tests for baseline DP optimizer."""

from src.optimization.baseline_dp import BaselineDPOptimizer, BaselineOptimizationConfig


def test_optimizer_respects_soc_and_throughput_constraints():
    config = BaselineOptimizationConfig(
        capacity_kwh=120.0,
        min_soc_fraction=0.2,
        max_soc_fraction=0.9,
        initial_soc_fraction=0.5,
        max_charge_kw=40.0,
        max_discharge_kw=40.0,
        throughput_limit_kwh=70.0,
        degradation_cost_per_kwh=0.02,
    )
    optimizer = BaselineDPOptimizer(config)

    prices = [35.0] * 8 + [80.0] * 8 + [45.0] * 8
    loads = [30.0] * 24
    solars = [5.0] * 24

    result = optimizer.optimize(prices, loads, solars)
    schedule = result["schedule"]

    assert len(schedule) == 24
    assert result["constraints"]["final_throughput_kwh"] <= config.throughput_limit_kwh + 1e-6

    soc_min = config.capacity_kwh * config.min_soc_fraction
    soc_max = config.capacity_kwh * config.max_soc_fraction

    for row in schedule:
        assert soc_min - 1e-6 <= row["soc_after_kwh"] <= soc_max + 1e-6
        assert abs(row["action_kw"]) <= max(config.max_charge_kw, config.max_discharge_kw) + 1e-6


def test_optimizer_objective_breakdown_matches_schedule_rows():
    config = BaselineOptimizationConfig(
        capacity_kwh=100.0,
        min_soc_fraction=0.1,
        max_soc_fraction=0.95,
        initial_soc_fraction=0.6,
        max_charge_kw=30.0,
        max_discharge_kw=30.0,
        throughput_limit_kwh=60.0,
        degradation_cost_per_kwh=0.015,
        export_price_factor=0.85,
    )
    optimizer = BaselineDPOptimizer(config)

    prices = [28.0] * 6 + [65.0] * 10 + [35.0] * 8
    loads = [22.0] * 24
    solars = [0.0] * 10 + [18.0] * 8 + [0.0] * 6

    result = optimizer.optimize(prices, loads, solars)
    schedule = result["schedule"]
    objective = result["objective"]

    purchase = sum(row["purchase_cost_eur"] for row in schedule)
    revenue = sum(row["export_revenue_eur"] for row in schedule)
    degradation = sum(row["degradation_penalty_eur"] for row in schedule)
    net_cost = sum(row["net_cost_eur"] for row in schedule)

    assert abs(objective["purchase_cost_eur"] - purchase) < 1e-9
    assert abs(objective["export_revenue_eur"] - revenue) < 1e-9
    assert abs(objective["degradation_penalty_eur"] - degradation) < 1e-9
    assert abs(objective["net_cost_eur"] - net_cost) < 1e-9
