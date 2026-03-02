"""Unit tests for solver-backed MILP scheduler."""

from src.optimization.milp_scheduler import MilpBatteryScheduler, MilpSchedulerConfig


def test_milp_scheduler_produces_feasible_schedule_with_fallback_solver():
    scheduler = MilpBatteryScheduler(
        MilpSchedulerConfig(
            capacity_kwh=140.0,
            min_soc_fraction=0.2,
            max_soc_fraction=0.9,
            initial_soc_fraction=0.55,
            max_charge_kw=35.0,
            max_discharge_kw=35.0,
            throughput_limit_kwh=80.0,
            degradation_cost_per_kwh=0.02,
        )
    )

    prices = [30.0] * 8 + [75.0] * 8 + [40.0] * 8
    loads = [28.0] * 24
    solars = [4.0] * 24

    result = scheduler.optimize(prices, loads, solars)
    schedule = result["schedule"]

    assert len(schedule) == 24
    assert result["constraints"]["final_throughput_kwh"] <= result["constraints"]["throughput_limit_kwh"] + 1e-6

    soc_min = result["constraints"]["soc_min_kwh"]
    soc_max = result["constraints"]["soc_max_kwh"]

    for row in schedule:
        assert soc_min - 1e-6 <= row["soc_after_kwh"] <= soc_max + 1e-6
        assert row["grid_import_kwh"] >= -1e-9
        assert row["grid_export_kwh"] >= -1e-9


def test_milp_scheduler_objective_matches_row_totals():
    scheduler = MilpBatteryScheduler(
        MilpSchedulerConfig(
            capacity_kwh=120.0,
            min_soc_fraction=0.1,
            max_soc_fraction=0.95,
            initial_soc_fraction=0.65,
            max_charge_kw=30.0,
            max_discharge_kw=30.0,
            throughput_limit_kwh=70.0,
            degradation_cost_per_kwh=0.015,
            export_price_factor=0.85,
        )
    )

    prices = [25.0] * 6 + [60.0] * 10 + [38.0] * 8
    loads = [24.0] * 24
    solars = [0.0] * 24

    result = scheduler.optimize(prices, loads, solars)
    schedule = result["schedule"]
    objective = result["objective"]

    purchase = sum(row["purchase_cost_eur"] for row in schedule)
    revenue = sum(row["export_revenue_eur"] for row in schedule)
    degradation = sum(row["degradation_penalty_eur"] for row in schedule)
    net_cost = sum(row["net_cost_eur"] for row in schedule)

    assert abs(objective["purchase_cost_eur"] - purchase) < 1e-8
    assert abs(objective["export_revenue_eur"] - revenue) < 1e-8
    assert abs(objective["degradation_penalty_eur"] - degradation) < 1e-8
    assert abs(objective["net_cost_eur"] - net_cost) < 1e-8
