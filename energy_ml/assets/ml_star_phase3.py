"""
ML-STAR Phase 3 - Optimized Ensemble (Standalone)
Does NOT depend on any other assets
"""

import importlib.util
import logging
import sys
from pathlib import Path

from dagster import asset


def _load_support_module():
    try:
        from energy_ml.assets import ml_star_phase3_support as support_module

        return support_module
    except Exception:
        support_path = Path(__file__).with_name("ml_star_phase3_support.py")
        module_name = "energy_ml.assets.ml_star_phase3_support"
        existing_module = sys.modules.get(module_name)
        if existing_module is not None:
            return existing_module

        spec = importlib.util.spec_from_file_location(module_name, support_path)
        module = importlib.util.module_from_spec(spec)
        assert spec is not None and spec.loader is not None
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module


_SUPPORT_MODULE = _load_support_module()
SmartEnergyAIPredictor = _SUPPORT_MODULE.SmartEnergyAIPredictor
build_metrics_payload = _SUPPORT_MODULE.build_metrics_payload
train_phase3_demo_model = _SUPPORT_MODULE.train_phase3_demo_model

logger = logging.getLogger(__name__)


@asset
def ml_star_phase3_optimized_model() -> dict:
    """
    ML-STAR Phase 3: Feature-selected stacking ensemble
    STANDALONE: Generates synthetic data for demo/testing
    On production: Feed real training_data_prepared here
    
    Expected: 82-85%+ accuracy (vs baseline 72.5%)
    """
    
    return train_phase3_demo_model(logger)


@asset
def ml_star_production_predictor(ml_star_phase3_optimized_model: dict):
    """Production inference wrapper"""
    return SmartEnergyAIPredictor(
        ml_star_phase3_optimized_model['model'],
        ml_star_phase3_optimized_model['selected_indices']
    )


@asset
def ml_star_metrics(ml_star_phase3_optimized_model: dict) -> dict:
    """Export metrics for dashboard"""
    return build_metrics_payload(ml_star_phase3_optimized_model)

