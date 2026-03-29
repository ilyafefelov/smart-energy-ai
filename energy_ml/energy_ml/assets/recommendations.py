"""Recommendation and monitoring assets for Energy ML system.

These assets generate real-time recommendations and monitor model performance.
"""
import importlib.util
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Any
from dagster import asset, Output
import logging
from pathlib import Path
import sys


def _load_support_module():
    try:
        from energy_ml.energy_ml.assets import recommendation_support as support_module

        return support_module
    except Exception:
        support_path = Path(__file__).with_name("recommendation_support.py")
        module_name = "energy_ml.energy_ml.assets.recommendation_support"
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
build_dashboard_response = _SUPPORT_MODULE.build_dashboard_response
build_definitions = _SUPPORT_MODULE.build_definitions
build_fallback_recommendation = _SUPPORT_MODULE.build_fallback_recommendation
build_fallback_schedule = _SUPPORT_MODULE.build_fallback_schedule
build_lineage_output = _SUPPORT_MODULE.build_lineage_output
build_monitoring_frame = _SUPPORT_MODULE.build_monitoring_frame
build_retraining_frame = _SUPPORT_MODULE.build_retraining_frame
predict_current_recommendation = _SUPPORT_MODULE.predict_current_recommendation
predict_schedule = _SUPPORT_MODULE.predict_schedule
utc_now = _SUPPORT_MODULE.utc_now

logger = logging.getLogger(__name__)


@asset(
    name="current_recommendation",
    description="Real-time recommendation for next hour (BUY/SELL/HOLD/DISCHARGE)",
    tags={"domain": "recommendations", "stage": "generation"}
)
def current_recommendation(
    xgboost_trained_model: Dict[str, Any],
    feature_matrix: pd.DataFrame
) -> Output[pd.DataFrame]:
    """Generate current hour recommendation based on latest features."""
    
    logger.info("🎯 Generating current recommendation...")
    
    if 'error' in xgboost_trained_model:
        logger.error(f"❌ Model not available: {xgboost_trained_model['error']}")
        fallback_frame, fallback_metadata = build_fallback_recommendation(
            'Model not available, defaulting to HOLD',
            'fallback',
        )
        return Output(
            fallback_frame,
            metadata=fallback_metadata,
        )
    
    try:
        model = xgboost_trained_model['model']
        recommendation_frame, recommendation_metadata, log_data = predict_current_recommendation(
            model,
            feature_matrix,
        )
        
        logger.info(f"✅ Recommendation generated:")
        logger.info(f"   Action: {log_data['action']}")
        logger.info(f"   Confidence: {log_data['confidence']:.2%}")
        logger.info(f"   Rationale: {log_data['rationale']}")
        
        return Output(
            recommendation_frame,
            metadata=recommendation_metadata,
        )
    
    except Exception as e:
        logger.error(f"❌ Recommendation generation failed: {e}")
        fallback_frame, fallback_metadata = build_fallback_recommendation(
            f'Error: {str(e)}',
            'error',
        )
        fallback_metadata['error'] = str(e)
        return Output(
            fallback_frame,
            metadata=fallback_metadata,
        )


@asset(
    name="schedule_24h",
    description="24-hour hourly action schedule and expected profit",
    tags={"domain": "recommendations", "stage": "scheduling"}
)
def schedule_24h(
    xgboost_trained_model: Dict[str, Any],
    feature_matrix: pd.DataFrame,
    weather_forecast: pd.DataFrame
) -> Output[pd.DataFrame]:
    """Generate 24-hour action schedule."""
    
    logger.info("📅 Generating 24-hour schedule...")
    
    if 'error' in xgboost_trained_model:
        logger.warning("⚠️ Using fallback schedule")
        schedule, fallback_metadata = build_fallback_schedule('fallback')
        return Output(schedule, metadata=fallback_metadata)
    
    try:
        model = xgboost_trained_model['model']
        schedule, schedule_metadata = predict_schedule(
            model,
            feature_matrix,
            weather_forecast,
            datetime.now().hour,
        )
        
        logger.info(f"✅ 24-hour schedule generated:")
        logger.info(f"   Total expected profit: {schedule_metadata['total_expected_profit']:.2f} ₴")
        logger.info(f"   Buy hours: {(schedule['recommended_action'] == 'BUY').sum()}")
        logger.info(f"   Sell hours: {(schedule['recommended_action'] == 'SELL').sum()}")
        logger.info(f"   Discharge hours: {(schedule['recommended_action'] == 'DISCHARGE').sum()}")
        
        return Output(
            schedule,
            metadata=schedule_metadata,
        )
    
    except Exception as e:
        logger.error(f"❌ Schedule generation failed: {e}")
        schedule, error_metadata = build_fallback_schedule('error')
        return Output(schedule, metadata=error_metadata)


@asset(
    name="performance_monitoring",
    description="Monitor model performance and alert if drift detected",
    tags={"domain": "monitoring", "stage": "tracking"}
)
def performance_monitoring(
    model_evaluation: pd.DataFrame,
    baseline_model_metrics: pd.DataFrame
) -> Output[pd.DataFrame]:
    """Monitor model performance metrics and detect drift."""
    
    logger.info("📊 Monitoring performance...")
    
    try:
        monitoring_df, monitoring_metadata, monitoring_summary = build_monitoring_frame(model_evaluation)
        
        logger.info(f"✅ Performance monitoring:")
        logger.info(f"   Current accuracy: {monitoring_summary['current_accuracy']:.2%}")
        logger.info(f"   Status: {'PASS' if 'PASS' in monitoring_summary['status'] else 'FAIL'}")
        
        return Output(
            monitoring_df,
            metadata=monitoring_metadata,
        )
    
    except Exception as e:
        logger.error(f"❌ Performance monitoring failed: {e}")
        return Output(
            pd.DataFrame({
                'metric': ['status'],
                'value': [f'Error: {str(e)}']
            }),
            metadata={"status": "error"}
        )


@asset(
    name="retraining_triggers",
    description="Detect when model needs retraining",
    tags={"domain": "monitoring", "stage": "triggers"}
)
def retraining_triggers(
    model_readiness_check: pd.DataFrame,
    performance_monitoring: pd.DataFrame
) -> Output[pd.DataFrame]:
    """Determine if retraining is needed."""
    
    logger.info("🔄 Checking retraining triggers...")
    
    triggers_df, trigger_metadata, needs_retraining = build_retraining_frame(performance_monitoring)
    
    logger.info(f"✅ Retraining check complete:")
    logger.info(f"   Needs retraining: {'YES' if needs_retraining else 'NO'}")
    logger.info(f"   Triggered: {triggers_df[triggers_df['triggered'] == 'YES'].shape[0]} trigger(s)")
    
    return Output(
        triggers_df,
        metadata=trigger_metadata,
    )


@asset(
    name="recommendation_metadata",
    description="Metadata about latest recommendation (lineage, source, timestamp)",
    tags={"domain": "recommendations", "stage": "metadata"}
)
def recommendation_metadata(
    current_recommendation: pd.DataFrame,
    feature_matrix: pd.DataFrame,
    xgboost_trained_model: Dict[str, Any]
) -> Output[pd.DataFrame]:
    """Generate metadata about recommendation source (lineage)."""
    
    logger.info("📝 Generating recommendation metadata...")
    
    try:
        lineage_frame, lineage_metadata, lineage_summary = build_lineage_output(current_recommendation)
        
        logger.info(f"✅ Metadata generated:")
        logger.info(f"   Timestamp: {lineage_summary['timestamp']}")
        logger.info(f"   Data sources: {lineage_summary['data_sources']}")
        logger.info(f"   Features: {lineage_summary['features']}")
        
        return Output(
            lineage_frame,
            metadata=lineage_metadata,
        )
    
    except Exception as e:
        logger.error(f"❌ Metadata generation failed: {e}")
        return Output(
            pd.DataFrame({
                'error': [str(e)]
            }),
            metadata={"status": "error"}
        )


@asset(
    name="dashboard_recommendation_api_response",
    description="Formatted API response ready for dashboard integration",
    tags={"domain": "api", "stage": "integration"}
)
def dashboard_recommendation_api_response(
    current_recommendation: pd.DataFrame,
    schedule_24h: pd.DataFrame,
    recommendation_metadata: pd.DataFrame,
    retraining_triggers: pd.DataFrame
) -> Output[Dict[str, Any]]:
    """Format recommendation as API response for dashboard."""
    
    logger.info("📡 Formatting API response...")
    
    try:
        api_response, response_metadata = build_dashboard_response(
            current_recommendation,
            schedule_24h,
            retraining_triggers,
        )
        
        logger.info(f"✅ API response formatted:")
        logger.info(f"   Action: {api_response['recommendation']['action']}")
        logger.info(f"   Confidence: {api_response['recommendation']['confidence_percent']}%")
        logger.info(f"   Expected 24h profit: {api_response['schedule_24h']['total_expected_profit']:.2f} ₴")
        
        return Output(
            api_response,
            metadata=response_metadata,
        )
    
    except Exception as e:
        logger.error(f"❌ API response formatting failed: {e}")
        return Output(
            {
                'status': 'error',
                'error': str(e),
            },
            metadata={"status": "error"}
        )


# Create Definitions object for Dagster
defs = build_definitions(
    [
        current_recommendation,
        schedule_24h,
        performance_monitoring,
        retraining_triggers,
        recommendation_metadata,
        dashboard_recommendation_api_response,
    ]
)
