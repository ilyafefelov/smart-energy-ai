#!/usr/bin/env python3
"""
train_model.py - tenant-aware model retraining script.
Spawned by dashboard/server/api/retraining/start.ts.

This script currently simulates training stages but now:
1. uses tenant-scoped artifact paths,
2. consumes retraining config overrides,
3. records which parameters were used for the run.
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional


def resolve_retraining_dir(tenant_id: str) -> Path:
    return Path(__file__).parent.parent / 'dashboard' / 'data' / 'tenants' / tenant_id / 'retraining'


def get_progress_file(tenant_id: str, job_id: str) -> Path:
    retraining_dir = resolve_retraining_dir(tenant_id)
    retraining_dir.mkdir(parents=True, exist_ok=True)
    return retraining_dir / f'{job_id}.json'


def get_metrics_file(tenant_id: str, job_id: str) -> Path:
    retraining_dir = resolve_retraining_dir(tenant_id)
    retraining_dir.mkdir(parents=True, exist_ok=True)
    return retraining_dir / f'{job_id}-metrics.json'


def update_progress(tenant_id: str, job_id: str, progress: int, message: str, status: str = 'running') -> None:
    progress_file = get_progress_file(tenant_id, job_id)
    payload = {
        'tenant_id': tenant_id,
        'jobId': job_id,
        'status': status,
        'progress': int(progress),
        'message': message,
        'timestamp': datetime.utcnow().isoformat(),
        'execution_mode': 'python',
    }
    progress_file.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    print(f'Progress {progress}% - {message}')


def merge_config_overrides(tenant_id: str, overrides: dict) -> dict:
    config_dir_env = Path((
        __import__('os').environ.get('ENERGY_ML_CONFIG_DIR')
        or (Path(__file__).parent.parent / 'energy_ml' / 'configs' / 'tenants' / tenant_id)
    ))
    config_dir_env.mkdir(parents=True, exist_ok=True)
    config_path = config_dir_env / 'user_config.json'

    existing = {}
    if config_path.exists():
        try:
            existing = json.loads(config_path.read_text(encoding='utf-8'))
        except Exception:
            existing = {}

    merged = {**existing, **overrides}
    config_path.write_text(json.dumps(merged, indent=2), encoding='utf-8')
    return merged


def load_training_data(tenant_id: str, job_id: str) -> int:
    update_progress(tenant_id, job_id, 5, 'Loading training data...')
    time.sleep(0.4)
    return 10000


def preprocess_data(tenant_id: str, job_id: str, samples: int) -> int:
    update_progress(tenant_id, job_id, 20, 'Preprocessing data...')
    time.sleep(0.4)
    return samples


def train_model(tenant_id: str, job_id: str, samples: int, epochs: int) -> None:
    _ = samples
    for epoch in range(1, epochs + 1):
        progress = 40 + int((epoch / max(epochs, 1)) * 40)
        update_progress(tenant_id, job_id, progress, f'Training epoch {epoch}/{epochs}...')
        time.sleep(0.2)


def optimize_parameters(tenant_id: str, job_id: str) -> None:
    update_progress(tenant_id, job_id, 85, 'Optimizing parameters...')
    time.sleep(0.4)


def save_model(tenant_id: str, job_id: str) -> Path:
    update_progress(tenant_id, job_id, 95, 'Saving model...')
    model_dir = Path(__file__).parent.parent / 'models' / 'tenants' / tenant_id
    model_dir.mkdir(parents=True, exist_ok=True)
    model_file = model_dir / f'model_{job_id}.json'
    model_file.write_text(json.dumps({
        'tenant_id': tenant_id,
        'jobId': job_id,
        'trainedAt': datetime.utcnow().isoformat(),
        'accuracy': 0.928,
        'loss': 0.045,
    }, indent=2), encoding='utf-8')
    return model_file


def save_metrics(tenant_id: str, job_id: str, epochs: int, used_config: dict) -> dict:
    metrics = {
        'tenant_id': tenant_id,
        'jobId': job_id,
        'completedAt': datetime.utcnow().isoformat(),
        'previousAccuracy': 85.2,
        'newAccuracy': 92.8,
        'improvementPercent': 8.9,
        'trainingTime': 45,
        'epochsCompleted': epochs,
        'finalLoss': 0.045,
        'convergenceRate': 0.95,
        'used_config': {
            'optimization_strategy': used_config.get('optimization_strategy'),
            'battery_capacity_kwh': used_config.get('battery_capacity_kwh'),
            'battery_c_rate_charge': used_config.get('battery_c_rate_charge'),
            'battery_c_rate_discharge': used_config.get('battery_c_rate_discharge'),
            'load_profile_type': used_config.get('load_profile_type'),
            'load_peak_kw': used_config.get('load_peak_kw'),
            'solar_capacity_kw': used_config.get('solar_capacity_kw'),
            'wind_capacity_kw': used_config.get('wind_capacity_kw'),
            'latitude': used_config.get('latitude'),
            'longitude': used_config.get('longitude'),
            'ml_forecast_horizon_hours': used_config.get('ml_forecast_horizon_hours'),
            'learningRate': used_config.get('learningRate'),
            'batchSize': used_config.get('batchSize'),
            'epochs': used_config.get('epochs'),
        },
    }
    metrics_file = get_metrics_file(tenant_id, job_id)
    metrics_file.write_text(json.dumps(metrics, indent=2), encoding='utf-8')
    return metrics


def parse_overrides(raw_config: Optional[str]) -> dict:
    if not raw_config:
        return {}
    try:
        return json.loads(raw_config)
    except Exception:
        return {}


def main() -> None:
    parser = argparse.ArgumentParser(description='Train energy optimization model')
    parser.add_argument('--job-id', required=True, help='Job ID')
    parser.add_argument('--tenant-id', required=True, help='Tenant ID')
    parser.add_argument('--config', help='JSON config overrides from dashboard')

    args = parser.parse_args()
    job_id = args.job_id
    tenant_id = args.tenant_id

    overrides = parse_overrides(args.config)
    epochs = int(overrides.get('epochs', 20))
    epochs = max(1, min(100, epochs))

    try:
        update_progress(tenant_id, job_id, 2, 'Starting model retraining...')

        merged_config = merge_config_overrides(tenant_id, overrides)

        samples = load_training_data(tenant_id, job_id)
        samples = preprocess_data(tenant_id, job_id, samples)
        train_model(tenant_id, job_id, samples, epochs)
        optimize_parameters(tenant_id, job_id)
        model_file = save_model(tenant_id, job_id)
        metrics = save_metrics(tenant_id, job_id, epochs, merged_config)

        update_progress(tenant_id, job_id, 100, 'Training completed successfully!', status='completed')

        print('TRAINING COMPLETE')
        print(f"Tenant: {tenant_id}")
        print(f"Model: {model_file}")
        print(f"Accuracy improvement: {metrics['improvementPercent']:.1f}%")
        sys.exit(0)
    except Exception as exc:
        update_progress(tenant_id, job_id, 0, f'Training failed: {exc}', status='failed')
        print(f'ERROR: {exc}')
        sys.exit(1)


if __name__ == '__main__':
    main()
