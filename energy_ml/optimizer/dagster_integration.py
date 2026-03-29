"""Dagster Integration for ML-STAR Optimized Models.

This module provides Dagster-compatible assets and ops for running
the ML-STAR optimization pipeline within the Smart Energy AI Dagster workflow.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import pickle
import json

import pandas as pd
import numpy as np
from dagster import op

logger = logging.getLogger(__name__)


@op
def initialize_ml_star_optimizer(config: Dict) -> Dict[str, Any]:
    """Initialize ML-STAR optimizer with configuration."""
    logger.info("Initializing ML-STAR optimizer")
    logger.info(f"  - N trials: {config.get('n_trials', 100)}")
    logger.info(f"  - CV splits: {config.get('n_splits', 5)}")
    logger.info(f"  - SMOTE enabled: {config.get('use_smote', True)}")
    logger.info(f"  - Strategies: {config.get('ensemble_strategies', ['voting', 'stacking'])}")
    
    return {
        'n_trials': config.get('n_trials', 100),
        'n_splits': config.get('n_splits', 5),
        'random_state': config.get('random_state', 42),
        'use_smote': config.get('use_smote', True),
        'output_dir': config.get('output_dir', 'optimization_results'),
        'ensemble_strategies': config.get('ensemble_strategies', ['voting', 'stacking']),
        'timestamp': datetime.now().isoformat()
    }


def op_load_training_data(dataset_path: str, feature_cols: list, target_col: str) -> pd.DataFrame:
    """Load training dataset."""
    logger.info(f"Loading training data from {dataset_path}")
    
    df = pd.read_csv(dataset_path)
    logger.info(f"Loaded {len(df)} samples with {len(df.columns)} columns")
    
    # Validate required columns
    required_cols = feature_cols + [target_col]
    missing = set(required_cols) - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {missing}")
    
    logger.info(f"Using {len(feature_cols)} features and target '{target_col}'")
    return df[required_cols]


def op_run_hyperparameter_search(config: Dict, data: pd.DataFrame) -> Dict[str, Any]:
    """Run Optuna hyperparameter search."""
    from energy_ml.optimizer.ml_star_optimizer import HyperparameterOptimizer, OptimizationConfig
    import xgboost as xgb
    
    logger.info("Starting hyperparameter optimization")
    
    # Assume last column is target
    X = data.iloc[:, :-1]
    y = data.iloc[:, -1]
    
    opt_config = OptimizationConfig(
        n_trials=config.get('n_trials', 100),
        n_splits=config.get('n_splits', 5),
        random_state=config.get('random_state', 42),
        verbose=True
    )
    
    optimizer = HyperparameterOptimizer(X, y, opt_config)
    best_params = optimizer.optimize(n_trials=config.get('n_trials', 100))
    
    # Add computed class weights
    from sklearn.utils.class_weight import compute_class_weight
    class_weights = compute_class_weight('balanced', classes=np.unique(y), y=y)
    best_params['scale_pos_weight'] = class_weights[1] if len(class_weights) > 1 else 1.0
    
    logger.info(f"Best CV score: {optimizer.best_score:.4f}")
    
    return {
        'best_params': best_params,
        'best_score': optimizer.best_score,
        'n_trials_completed': len(optimizer.trial_history),
        'trial_history': optimizer.trial_history
    }


def op_train_baseline_model(config: Dict, data: pd.DataFrame, search_results: Dict) -> Dict[str, Any]:
    """Train optimized baseline XGBoost model."""
    import xgboost as xgb
    from sklearn.model_selection import train_test_split, cross_val_score
    from sklearn.metrics import accuracy_score
    
    logger.info("Training baseline XGBoost model with optimized hyperparameters")
    
    # Prepare data
    X = data.iloc[:, :-1]
    y = data.iloc[:, -1]
    
    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=0.2,
        random_state=config.get('random_state', 42),
        stratify=y
    )
    
    # Train model
    model = xgb.XGBClassifier(**search_results['best_params'])
    model.fit(X_train, y_train)
    
    # Evaluate
    train_acc = accuracy_score(y_train, model.predict(X_train))
    test_acc = accuracy_score(y_test, model.predict(X_test))
    
    # Cross-validation
    cv_scores = cross_val_score(model, X_train, y_train, cv=config.get('n_splits', 5))
    
    logger.info(f"Baseline results:")
    logger.info(f"  - Train accuracy: {train_acc:.4f}")
    logger.info(f"  - Test accuracy: {test_acc:.4f}")
    logger.info(f"  - CV mean: {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")
    
    return {
        'model': model,
        'X_train': X_train,
        'X_test': X_test,
        'y_train': y_train,
        'y_test': y_test,
        'train_accuracy': float(train_acc),
        'test_accuracy': float(test_acc),
        'cv_scores': cv_scores.tolist(),
        'cv_mean': float(cv_scores.mean()),
        'cv_std': float(cv_scores.std())
    }


def op_build_ensemble_models(baseline_result: Dict, config: Dict) -> Dict[str, Any]:
    """Build voting and stacking ensembles."""
    from energy_ml.optimizer.ml_star_optimizer import EnsembleBuilder, OptimizationConfig
    import xgboost as xgb
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    from sklearn.metrics import accuracy_score
    
    logger.info("Building ensemble models")
    
    X_train = baseline_result['X_train']
    y_train = baseline_result['y_train']
    X_test = baseline_result['X_test']
    y_test = baseline_result['y_test']
    
    opt_config = OptimizationConfig(random_state=config.get('random_state', 42))
    
    # Create base models
    base_models = {
        'xgboost': baseline_result['model'],
        'random_forest': RandomForestClassifier(n_estimators=200, random_state=config.get('random_state', 42)),
        'gradient_boosting': GradientBoostingClassifier(n_estimators=200, random_state=config.get('random_state', 42))
    }
    
    # Train additional models
    for name, model in base_models.items():
        if name != 'xgboost':
            model.fit(X_train, y_train)
    
    ensemble_builder = EnsembleBuilder(base_models, opt_config)
    
    results = {}
    ensemble_strategies = config.get('ensemble_strategies', ['voting', 'stacking'])
    
    # Voting ensemble
    if 'voting' in ensemble_strategies:
        voting = ensemble_builder.build_voting_ensemble('soft')
        voting.fit(X_train, y_train)
        voting_acc = accuracy_score(y_test, voting.predict(X_test))
        results['voting'] = {
            'model': voting,
            'accuracy': voting_acc,
            'type': 'voting'
        }
        logger.info(f"Voting ensemble accuracy: {voting_acc:.4f}")
    
    # Stacking ensemble
    if 'stacking' in ensemble_strategies:
        stacking = ensemble_builder.build_stacking_ensemble()
        stacking.fit(X_train, y_train)
        stacking_acc = accuracy_score(y_test, stacking.predict(X_test))
        results['stacking'] = {
            'model': stacking,
            'accuracy': stacking_acc,
            'type': 'stacking'
        }
        logger.info(f"Stacking ensemble accuracy: {stacking_acc:.4f}")
    
    return results


def op_validate_safety(baseline_result: Dict) -> Dict[str, Any]:
    """Validate model safety (data leakage, overfitting, reproducibility)."""
    from energy_ml.optimizer.ml_star_optimizer import SafetyValidator, OptimizationConfig
    
    logger.info("Running safety validation")
    
    config = OptimizationConfig()
    validator = SafetyValidator(config)
    
    X_train = baseline_result['X_train']
    X_test = baseline_result['X_test']
    y_train = baseline_result['y_train']
    y_test = baseline_result['y_test']
    
    leakage_report = validator.check_data_leakage(X_train, X_test, y_train, y_test)
    overfitting_report = validator.check_overfitting(
        baseline_result['train_accuracy'],
        baseline_result['test_accuracy'],
        baseline_result['cv_scores']
    )
    reproducibility_report = validator.check_reproducibility(baseline_result['model'], 42)
    
    return {
        'data_leakage': leakage_report,
        'overfitting': overfitting_report,
        'reproducibility': reproducibility_report,
        'all_passed': (
            not leakage_report['leakage_detected'] and
            overfitting_report['overfitting_risk'] == 'LOW' and
            reproducibility_report['status'] == 'OK'
        )
    }


def op_conduct_ablation_study(baseline_result: Dict, ensemble_results: Dict) -> pd.DataFrame:
    """Conduct ablation study on ensemble components."""
    from energy_ml.optimizer.ml_star_optimizer import AblationStudy, OptimizationConfig
    
    logger.info("Conducting ablation study")
    
    config = OptimizationConfig()
    ablation = AblationStudy(baseline_result['X_test'], baseline_result['y_test'], config)
    ablation.set_baseline(baseline_result['model'])
    
    # Test each ensemble
    for name, ensemble_info in ensemble_results.items():
        if name in ['voting', 'stacking']:
            ablation.test_component(
                ensemble_info['model'],
                f"{name.capitalize()} Ensemble",
                inference_time_ms=20.0,
                memory_usage_mb=60.0
            )
    
    ranking = ablation.get_ranking()
    logger.info(f"\nAblation ranking:\n{ranking}")
    
    return ranking


def op_save_optimization_results(baseline_result: Dict, ensemble_results: Dict, 
                                 safety_results: Dict, ablation_ranking: pd.DataFrame,
                                 output_dir: str = "optimization_results") -> Dict[str, str]:
    """Save all optimization results to disk."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    results_summary = {
        'baseline_accuracy': baseline_result['test_accuracy'],
        'best_ensemble_accuracy': max([e['accuracy'] for e in ensemble_results.values()]),
        'best_ensemble': max(ensemble_results.items(), key=lambda x: x[1]['accuracy'])[0],
        'cv_mean': baseline_result['cv_mean'],
        'cv_std': baseline_result['cv_std']
    }
    
    # Save baseline model
    baseline_path = output_path / 'baseline_model.pkl'
    with open(baseline_path, 'wb') as f:
        pickle.dump(baseline_result['model'], f)
    
    # Save ensemble models
    for name, ensemble_info in ensemble_results.items():
        model_path = output_path / f'{name}_ensemble_model.pkl'
        with open(model_path, 'wb') as f:
            pickle.dump(ensemble_info['model'], f)
    
    # Save summary
    summary_path = output_path / 'optimization_summary.json'
    with open(summary_path, 'w') as f:
        json.dump(results_summary, f, indent=2)
    
    # Save ablation results
    ablation_path = output_path / 'ablation_study.csv'
    ablation_ranking.to_csv(ablation_path, index=False)
    
    # Save safety report
    safety_path = output_path / 'safety_report.json'
    with open(safety_path, 'w') as f:
        safe_results = {
            'data_leakage': safety_results['data_leakage'],
            'overfitting': safety_results['overfitting'],
            'reproducibility': safety_results['reproducibility'],
            'all_passed': safety_results['all_passed']
        }
        json.dump(safe_results, f, indent=2, default=str)
    
    logger.info(f"Results saved to {output_path}")
    
    return {
        'baseline_model_path': str(baseline_path),
        'ensemble_models_dir': str(output_path),
        'summary_path': str(summary_path),
        'ablation_path': str(ablation_path),
        'safety_report_path': str(safety_path)
    }


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    logger.info("Dagster integration module loaded successfully")
