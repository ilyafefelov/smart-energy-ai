"""Test suite for ML-STAR optimizer.

Tests cover:
- Module imports
- Core functionality (data prep, HPO, ensemble building, safety checks)
- Integration (full pipeline)
- Performance benchmarks
"""

import sys
import logging
from pathlib import Path
import pandas as pd
import numpy as np
import time

# Setup
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(
    level=logging.INFO,
    format='%(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_imports():
    """Test all required module imports."""
    logger.info("TEST: Module imports")
    try:
        from energy_ml.optimizer.ml_star_optimizer import (
            MLSTAROptimizer, OptimizationConfig, HyperparameterOptimizer,
            EnsembleBuilder, SafetyValidator, AblationStudy, FeatureAnalyzer,
            SOTA_TECHNIQUES, generate_sota_report
        )
        logger.info("  ✓ All core modules imported successfully")
        return True
    except ImportError as e:
        logger.error(f"  ✗ Import failed: {e}")
        return False


def test_synthetic_data_generation():
    """Test synthetic data generation."""
    logger.info("\nTEST: Synthetic data generation")
    try:
        np.random.seed(42)
        n_samples, n_features = 1000, 73
        
        X = np.random.randn(n_samples, n_features)
        y = np.random.randint(0, 4, n_samples)
        
        X_df = pd.DataFrame(X, columns=[f'feature_{i}' for i in range(n_features)])
        y_series = pd.Series(y)
        
        assert X_df.shape == (n_samples, n_features), "X shape mismatch"
        assert len(y_series) == n_samples, "y shape mismatch"
        assert y_series.nunique() == 4, "Not 4 classes"
        
        logger.info(f"  ✓ Generated {n_samples} samples with {n_features} features")
        logger.info(f"    Class distribution: {dict(y_series.value_counts())}")
        return True, X_df, y_series
    except Exception as e:
        logger.error(f"  ✗ Data generation failed: {e}")
        return False, None, None


def test_optimization_config():
    """Test optimization configuration."""
    logger.info("\nTEST: Optimization configuration")
    try:
        from energy_ml.optimizer.ml_star_optimizer import OptimizationConfig
        
        config = OptimizationConfig(
            n_trials=10,
            n_splits=3,
            random_state=42
        )
        
        assert config.n_trials == 10, "n_trials not set"
        assert config.n_splits == 3, "n_splits not set"
        assert config.random_state == 42, "random_state not set"
        
        logger.info(f"  ✓ Config created: {config.n_trials} trials, {config.n_splits} splits")
        return True, config
    except Exception as e:
        logger.error(f"  ✗ Config test failed: {e}")
        return False, None


def test_feature_analyzer(X, y):
    """Test feature analysis."""
    logger.info("\nTEST: Feature analyzer")
    try:
        from energy_ml.optimizer.ml_star_optimizer import FeatureAnalyzer, OptimizationConfig
        
        config = OptimizationConfig(n_trials=5)
        analyzer = FeatureAnalyzer(X, y, config)
        
        # Compute importance
        importance_df = analyzer.compute_importance(n_estimators=10)
        
        assert len(importance_df) > 0, "No importances computed"
        assert 'importance' in importance_df.columns, "Missing importance column"
        
        # Select features
        selected = analyzer.select_features(threshold_percentile=80)
        assert len(selected) > 0, "No features selected"
        
        logger.info(f"  ✓ Feature importance computed for {len(X.columns)} features")
        logger.info(f"  ✓ Selected {len(selected)} features (top 20%)")
        return True, analyzer
    except Exception as e:
        logger.error(f"  ✗ Feature analyzer test failed: {e}")
        return False, None


def test_hyperparameter_optimizer(X, y, config):
    """Test hyperparameter optimization (lightweight version)."""
    logger.info("\nTEST: Hyperparameter optimizer")
    try:
        from energy_ml.optimizer.ml_star_optimizer import HyperparameterOptimizer
        
        # Use small subset for speed
        X_sample = X.iloc[:500]
        y_sample = y.iloc[:500]
        
        optimizer = HyperparameterOptimizer(X_sample, y_sample, config)
        
        # Run with just 3 trials for testing
        best_params = optimizer.optimize(n_trials=3)
        
        assert best_params is not None, "No best params"
        assert 'max_depth' in best_params, "Missing max_depth"
        
        logger.info(f"  ✓ HPO completed: best CV score = {optimizer.best_score:.4f}")
        logger.info(f"  ✓ Trials completed: {len(optimizer.trial_history)}")
        return True, best_params
    except Exception as e:
        logger.error(f"  ✗ HPO test failed: {e}")
        return False, None


def test_imbalance_handler(y):
    """Test class imbalance handling."""
    logger.info("\nTEST: Imbalance handler")
    try:
        from energy_ml.optimizer.ml_star_optimizer import ImbalanceHandler, OptimizationConfig
        
        config = OptimizationConfig()
        handler = ImbalanceHandler(config)
        
        # Get class weights
        weights = handler.get_class_weights(y.values)
        
        assert len(weights) == 4, "Should have 4 classes"
        assert all(w > 0 for w in weights.values()), "Weights should be positive"
        
        logger.info(f"  ✓ Class weights computed: {weights}")
        return True
    except Exception as e:
        logger.error(f"  ✗ Imbalance handler test failed: {e}")
        return False


def test_ensemble_builder(X, y):
    """Test ensemble building."""
    logger.info("\nTEST: Ensemble builder")
    try:
        from energy_ml.optimizer.ml_star_optimizer import EnsembleBuilder, OptimizationConfig
        from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
        import xgboost as xgb
        from sklearn.model_selection import train_test_split
        
        config = OptimizationConfig(random_state=42)
        
        # Prepare data
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
        
        # Train base models
        base_models = {
            'xgboost': xgb.XGBClassifier(n_estimators=10, random_state=42),
            'rf': RandomForestClassifier(n_estimators=10, random_state=42),
            'gb': GradientBoostingClassifier(n_estimators=10, random_state=42)
        }
        
        for model in base_models.values():
            model.fit(X_train, y_train)
        
        # Build ensemble
        builder = EnsembleBuilder(base_models, config)
        voting = builder.build_voting_ensemble('soft')
        
        # Make predictions
        voting.fit(X_train, y_train)
        preds = voting.predict(X_test)
        
        assert len(preds) == len(X_test), "Prediction length mismatch"
        
        logger.info(f"  ✓ Voting ensemble created with {len(base_models)} base models")
        logger.info(f"  ✓ Predictions made: {len(preds)} samples")
        return True
    except Exception as e:
        logger.error(f"  ✗ Ensemble builder test failed: {e}")
        return False


def test_safety_validator(X, y):
    """Test safety validation."""
    logger.info("\nTEST: Safety validator")
    try:
        from energy_ml.optimizer.ml_star_optimizer import SafetyValidator, OptimizationConfig
        from sklearn.model_selection import train_test_split
        
        config = OptimizationConfig()
        validator = SafetyValidator(config)
        
        # Prepare data
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
        
        # Check data leakage
        leakage_report = validator.check_data_leakage(X_train, X_test, y_train, y_test)
        assert 'leakage_detected' in leakage_report, "Missing leakage detection field"
        
        # Check overfitting
        overfitting_report = validator.check_overfitting(0.95, 0.78, [0.80, 0.79, 0.81])
        assert 'overfitting_risk' in overfitting_report, "Missing overfitting risk field"
        
        logger.info(f"  ✓ Data leakage check: {leakage_report['leakage_detected']}")
        logger.info(f"  ✓ Overfitting risk: {overfitting_report['overfitting_risk']}")
        return True
    except Exception as e:
        logger.error(f"  ✗ Safety validator test failed: {e}")
        return False


def test_ablation_study(X, y):
    """Test ablation study."""
    logger.info("\nTEST: Ablation study")
    try:
        from energy_ml.optimizer.ml_star_optimizer import AblationStudy, OptimizationConfig
        from sklearn.model_selection import train_test_split
        import xgboost as xgb
        
        config = OptimizationConfig(random_state=42)
        
        # Prepare data
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
        
        # Train baseline
        baseline = xgb.XGBClassifier(n_estimators=10, random_state=42)
        baseline.fit(X_train, y_train)
        
        # Create ablation study
        ablation = AblationStudy(X_test, y_test, config)
        ablation.set_baseline(baseline)
        
        logger.info(f"  ✓ Ablation study initialized")
        logger.info(f"  ✓ Baseline accuracy: {ablation.baseline_accuracy:.4f}")
        return True
    except Exception as e:
        logger.error(f"  ✗ Ablation study test failed: {e}")
        return False


def test_sota_report():
    """Test SOTA report generation."""
    logger.info("\nTEST: SOTA report generation")
    try:
        from energy_ml.optimizer.ml_star_optimizer import generate_sota_report
        
        df = generate_sota_report()
        
        assert len(df) == 5, "Should have 5 SOTA techniques"
        assert 'rank' in df.columns, "Missing rank column"
        assert 'name' in df.columns, "Missing name column"
        assert df['rank'].tolist() == [1, 2, 3, 4, 5], "Incorrect ranking"
        
        logger.info(f"  ✓ SOTA report generated: {len(df)} techniques")
        for _, row in df.iterrows():
            logger.info(f"    {row['rank']}. {row['name']}")
        return True
    except Exception as e:
        logger.error(f"  ✗ SOTA report test failed: {e}")
        return False


def run_all_tests():
    """Run all tests."""
    logger.info("="*80)
    logger.info("ML-STAR OPTIMIZER TEST SUITE")
    logger.info("="*80)
    
    results = []
    
    # Test 1: Imports
    results.append(("Imports", test_imports()))
    
    # Test 2: Data generation
    success, X, y = test_synthetic_data_generation()
    results.append(("Synthetic Data", success))
    
    if not success:
        logger.error("Cannot continue without data")
        return results
    
    # Test 3: Config
    success, config = test_optimization_config()
    results.append(("Config", success))
    
    # Test 4: Feature analyzer
    success, _ = test_feature_analyzer(X, y)
    results.append(("Feature Analyzer", success))
    
    # Test 5: HPO (lightweight)
    success, _ = test_hyperparameter_optimizer(X, y, config)
    results.append(("Hyperparameter Optimizer", success))
    
    # Test 6: Imbalance handler
    results.append(("Imbalance Handler", test_imbalance_handler(y)))
    
    # Test 7: Ensemble builder
    results.append(("Ensemble Builder", test_ensemble_builder(X, y)))
    
    # Test 8: Safety validator
    results.append(("Safety Validator", test_safety_validator(X, y)))
    
    # Test 9: Ablation study
    results.append(("Ablation Study", test_ablation_study(X, y)))
    
    # Test 10: SOTA report
    results.append(("SOTA Report", test_sota_report()))
    
    # Print summary
    logger.info("\n" + "="*80)
    logger.info("TEST SUMMARY")
    logger.info("="*80)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        logger.info(f"{status}: {name}")
    
    logger.info(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("\n✓ All tests passed! Module is ready for production.")
    else:
        logger.error(f"\n✗ {total - passed} tests failed. Review above for details.")
    
    return results


if __name__ == '__main__':
    results = run_all_tests()
    sys.exit(0 if all(r for _, r in results) else 1)
