"""Support helpers for the ML-STAR optimized pipeline asset."""

from __future__ import annotations

from typing import Any, Dict, Sequence

import numpy as np


def evaluate_classifier_metrics(
    context: Any,
    model: Any,
    X_test: Any,
    y_test: Any,
    *,
    phase: int,
    model_type: str,
    selected_indices: Sequence[int] | None = None,
) -> Dict[str, Any]:
    from sklearn.metrics import accuracy_score, f1_score, recall_score

    evaluation_frame = X_test.iloc[:, selected_indices] if selected_indices is not None else X_test
    y_pred = model.predict(evaluation_frame)

    metrics = {
        "phase": phase,
        "model_type": model_type,
        "accuracy": accuracy_score(y_test, y_pred),
        "f1_score": f1_score(y_test, y_pred, average="weighted"),
        "recall": recall_score(y_test, y_pred, average="weighted"),
    }
    if selected_indices is not None:
        metrics["selected_features"] = len(selected_indices)

    context.log.info(
        f"Phase {phase} Results: Accuracy={metrics['accuracy']:.4f}, F1={metrics['f1_score']:.4f}"
    )
    if phase == 3:
        context.log.info(
            f"Total improvement: +{(metrics['accuracy'] - 0.725) * 100:.1f}% vs baseline (72.5%)"
        )

    return metrics


class SmartEnergyAIPredictor:
    """Production inference wrapper for optimized energy model."""

    def __init__(self, model: Any, selected_indices: Sequence[int], feature_scaler: Any = None):
        self.model = model
        self.selected_indices = selected_indices
        self.scaler = feature_scaler
        self.classes = ["BUY", "SELL", "HOLD", "DISCHARGE"]

    def predict(self, X: Any):
        X_selected = X.iloc[:, self.selected_indices]
        return self.model.predict(X_selected)

    def predict_proba(self, X: Any):
        X_selected = X.iloc[:, self.selected_indices]
        return self.model.predict_proba(X_selected)

    def predict_batch(self, X: Any, batch_size: int = 1000):
        predictions = []
        for index in range(0, len(X), batch_size):
            batch = X.iloc[index : index + batch_size]
            predictions.extend(self.predict(batch))
        return np.array(predictions)

    def predict_with_confidence(self, X: Any):
        probabilities = self.predict_proba(X)
        predictions = self.predict(X)
        confidence = probabilities.max(axis=1)
        return {
            "predictions": predictions,
            "confidence": confidence,
            "probabilities": probabilities,
            "class_labels": [self.classes[prediction] for prediction in predictions],
        }


DEPLOYMENT_INSTRUCTIONS = """
DEPLOYMENT STEPS:

1. Copy this file to: energy_ml/assets/ml_star_optimized_pipeline.py

2. Update energy_ml/jobs/__init__.py to include:
   from energy_ml.assets.ml_star_optimized_pipeline import energy_ml_star_pipeline

3. Replace old pipeline with:
   @job
   def energy_optimization_pipeline():
       energy_ml_star_pipeline()

4. Run:
   dagster job execute -f energy_ml/jobs/__init__.py -j energy_optimization_pipeline

5. Expected Results:
   - Phase 1: 76%+ accuracy
   - Phase 2: 79-80%+ accuracy
   - Phase 3: 82-85%+ accuracy

6. Production Deployment:
   predictor = SmartEnergyAIPredictor(phase3_model, selected_indices)
   predictions = predictor.predict_batch(X_new)

7. Rollback if needed:
   - Keep old model in backup
   - Use A/B testing (50% old, 50% new)
   - Monitor for 1 week before full cutover
"""