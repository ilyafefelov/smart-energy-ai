"""Dagster definitions for Energy ML system - Minimal Config.

This is the entry point for Dagster. Loads only available assets.
"""
from dagster import Definitions, define_asset_job

# Import ML-STAR Phase 3 assets only (these are standalone)
from energy_ml.assets.ml_star_phase3 import (
    ml_star_phase3_optimized_model,
    ml_star_production_predictor,
    ml_star_metrics
)

# Define ML-STAR optimization job
ml_star_optimization_pipeline = define_asset_job(
    name="ml_star_optimization_pipeline",
    selection=[
        ml_star_phase3_optimized_model,
        ml_star_production_predictor,
        ml_star_metrics,
    ],
    tags={"optimization": True, "ml_star": True, "phase": 3},
)

# Create definitions with just ML-STAR (no dependencies)
defs = Definitions(
    assets=[
        ml_star_phase3_optimized_model,
        ml_star_production_predictor,
        ml_star_metrics,
    ],
    jobs=[ml_star_optimization_pipeline],
)

