"""Support helpers for the standalone ML-STAR phase 3 asset."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import xgboost as xgb
from imblearn.over_sampling import SMOTE
from sklearn.ensemble import RandomForestClassifier, StackingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import StratifiedKFold, train_test_split


BASELINE_ACCURACY = 0.725
DEMO_RANDOM_SEED = 42
DEMO_SAMPLE_COUNT = 10000
DEMO_FEATURE_COUNT = 73


class SmartEnergyAIPredictor:
    """Production inference wrapper for the standalone phase 3 asset."""

    def __init__(self, model: Any, selected_indices: Any):
        self.model = model
        self.selected_indices = selected_indices
        self.classes = ["BUY", "SELL", "HOLD", "DISCHARGE"]

    def predict(self, X: pd.DataFrame):
        X_selected = X.iloc[:, self.selected_indices]
        return self.model.predict(X_selected)

    def predict_proba(self, X: pd.DataFrame):
        X_selected = X.iloc[:, self.selected_indices]
        return self.model.predict_proba(X_selected)


def train_phase3_demo_model(logger: Any) -> dict:
    logger.info("=" * 80)
    logger.info("ML-STAR PHASE 3 - OPTIMIZED ENSEMBLE (STANDALONE)")
    logger.info("=" * 80)
    logger.info("\n[SETUP] Generating synthetic training data...")

    X_train, X_test, y_train, y_test = _generate_demo_training_data()
    logger.info(
        f"  ✓ Generated {DEMO_SAMPLE_COUNT} samples with {DEMO_FEATURE_COUNT} features"
    )

    logger.info("\n[PHASE 1] SMOTE Balancing")
    X_train_balanced, y_train_balanced = _apply_smote(X_train, y_train)
    logger.info(f"  ✓ SMOTE: {len(X_train)} → {len(X_train_balanced)} samples")

    logger.info("\n[PHASE 2] Stacking Ensemble Training")
    stacking_phase2 = _build_stacking_classifier(_phase2_base_models())
    logger.info("  Training stacking ensemble...")
    stacking_phase2.fit(X_train_balanced, y_train_balanced)
    phase2_accuracy, phase2_f1 = _evaluate_model(stacking_phase2, X_test, y_test)
    logger.info(f"  ✓ Phase 2: Accuracy {phase2_accuracy:.4f}, F1 {phase2_f1:.4f}")

    logger.info("\n[PHASE 3] Feature Selection + Optimization")
    selected_indices = _select_feature_indices(stacking_phase2)
    logger.info(f"  ✓ Selected {len(selected_indices)}/{DEMO_FEATURE_COUNT} features")

    stacking_phase3 = _build_stacking_classifier(_phase3_base_models())
    stacking_phase3.fit(X_train_balanced.iloc[:, selected_indices], y_train_balanced)
    phase3_accuracy, phase3_f1 = _evaluate_model(
        stacking_phase3,
        X_test,
        y_test,
        selected_indices=selected_indices,
    )
    logger.info(f"  ✓ Phase 3: Accuracy {phase3_accuracy:.4f}, F1 {phase3_f1:.4f}")
    logger.info(
        f"  ✓ Improvement: +{(phase3_accuracy - BASELINE_ACCURACY) * 100:.1f}% vs baseline 72.5%"
    )
    logger.info("\n✅ ML-STAR Phase 3 Complete")

    return build_model_summary(
        model=stacking_phase3,
        selected_indices=selected_indices,
        accuracy=phase3_accuracy,
        f1_score_value=phase3_f1,
        total_features=DEMO_FEATURE_COUNT,
    )


def build_model_summary(
    *,
    model: Any,
    selected_indices: Any,
    accuracy: float,
    f1_score_value: float,
    total_features: int,
) -> dict:
    return {
        "model": model,
        "selected_indices": selected_indices,
        "accuracy": float(accuracy),
        "f1_score": float(f1_score_value),
        "features_used": int(len(selected_indices)),
        "total_features": int(total_features),
        "improvement_percent": float((accuracy - BASELINE_ACCURACY) * 100),
    }


def build_metrics_payload(model_dict: dict) -> dict:
    return {
        "accuracy": model_dict["accuracy"],
        "f1_score": model_dict["f1_score"],
        "features_used": model_dict["features_used"],
        "total_features": model_dict["total_features"],
        "improvement_percent": model_dict["improvement_percent"],
        "baseline_accuracy": BASELINE_ACCURACY,
    }


def _generate_demo_training_data() -> tuple[pd.DataFrame, pd.DataFrame, np.ndarray, np.ndarray]:
    np.random.seed(DEMO_RANDOM_SEED)
    X = pd.DataFrame(
        np.random.randn(DEMO_SAMPLE_COUNT, DEMO_FEATURE_COUNT),
        columns=[f"feature_{index}" for index in range(DEMO_FEATURE_COUNT)],
    )
    y = np.random.choice(
        [0, 1, 2, 3],
        size=DEMO_SAMPLE_COUNT,
        p=[0.35, 0.30, 0.30, 0.05],
    )
    return train_test_split(X, y, test_size=0.2, stratify=y, random_state=DEMO_RANDOM_SEED)


def _apply_smote(X_train: pd.DataFrame, y_train: np.ndarray) -> tuple[pd.DataFrame, np.ndarray]:
    smote = SMOTE(sampling_strategy="auto", random_state=DEMO_RANDOM_SEED)
    return smote.fit_resample(X_train, y_train)


def _phase2_base_models() -> list[tuple[str, Any]]:
    return [
        (
            "xgb",
            xgb.XGBClassifier(
                n_estimators=300,
                max_depth=7,
                learning_rate=0.05,
                subsample=0.9,
                colsample_bytree=0.8,
                reg_alpha=0.1,
                reg_lambda=1.0,
                random_state=DEMO_RANDOM_SEED,
                n_jobs=-1,
                verbosity=0,
            ),
        ),
        (
            "rf",
            RandomForestClassifier(
                n_estimators=250,
                max_depth=16,
                random_state=DEMO_RANDOM_SEED,
                n_jobs=-1,
            ),
        ),
    ]


def _phase3_base_models() -> list[tuple[str, Any]]:
    return [
        (
            "xgb",
            xgb.XGBClassifier(
                n_estimators=350,
                max_depth=7,
                learning_rate=0.05,
                subsample=0.92,
                colsample_bytree=0.85,
                reg_alpha=0.05,
                reg_lambda=0.8,
                random_state=DEMO_RANDOM_SEED,
                n_jobs=-1,
                verbosity=0,
            ),
        ),
        (
            "rf",
            RandomForestClassifier(
                n_estimators=280,
                max_depth=17,
                random_state=DEMO_RANDOM_SEED,
                n_jobs=-1,
            ),
        ),
    ]


def _build_stacking_classifier(base_models: list[tuple[str, Any]]) -> StackingClassifier:
    return StackingClassifier(
        estimators=base_models,
        final_estimator=LogisticRegression(max_iter=1000, random_state=DEMO_RANDOM_SEED),
        cv=StratifiedKFold(n_splits=5, shuffle=True, random_state=DEMO_RANDOM_SEED),
    )


def _evaluate_model(
    model: Any,
    X_test: pd.DataFrame,
    y_test: np.ndarray,
    *,
    selected_indices: Any | None = None,
) -> tuple[float, float]:
    evaluation_frame = X_test.iloc[:, selected_indices] if selected_indices is not None else X_test
    predictions = model.predict(evaluation_frame)
    accuracy = accuracy_score(y_test, predictions)
    f1_value = f1_score(y_test, predictions, average="weighted", zero_division=0)
    return accuracy, f1_value


def _select_feature_indices(model: Any) -> np.ndarray:
    feature_importance = model.estimators_[0].feature_importances_
    threshold = np.percentile(feature_importance, 50)
    return np.where(feature_importance >= threshold)[0]