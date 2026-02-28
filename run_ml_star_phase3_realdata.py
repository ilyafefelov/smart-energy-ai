#!/usr/bin/env python3
"""
ML-STAR Phase 3 on Real Energy Data
Loads actual training_data_prepared from your Dagster pipeline
"""

import sys
import os
import pickle
import numpy as np
import pandas as pd
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier, StackingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, recall_score, classification_report
import xgboost as xgb
from imblearn.over_sampling import SMOTE

print("=" * 80)
print("ML-STAR PHASE 3 - REAL ENERGY DATA OPTIMIZATION")
print("=" * 80)
print()

# Try to load real data from pipeline outputs
try:
    print("[SETUP] Loading real energy training data...")
    
    # Check for saved training data from previous pipeline runs
    data_paths = [
        "energy_ml/outputs/training_data_prepared.pkl",
        "energy_ml/assets_cache/training_data_prepared.pkl",
        "outputs/training_data_prepared.pkl"
    ]
    
    training_data = None
    for path in data_paths:
        if os.path.exists(path):
            with open(path, 'rb') as f:
                training_data = pickle.load(f)
            print(f"  ✓ Loaded training data from {path}")
            break
    
    if training_data is None:
        print("  ⚠ Real training data not found. Using synthetic data for testing.")
        print("  (Will work with real data when integrated into full pipeline)")
        
        # Generate synthetic test data matching your pipeline structure
        np.random.seed(42)
        n_samples = 10000
        n_features = 73
        
        X = pd.DataFrame(
            np.random.randn(n_samples, n_features),
            columns=[f"feature_{i}" for i in range(n_features)]
        )
        
        # Realistic 4-class distribution
        y = np.random.choice(
            [0, 1, 2, 3],
            size=n_samples,
            p=[0.35, 0.30, 0.30, 0.05]
        )
        
        from sklearn.model_selection import train_test_split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, stratify=y, random_state=42
        )
        
        training_data = {
            'X_train': X_train,
            'y_train': y_train,
            'X_test': X_test,
            'y_test': y_test
        }
        
        print(f"  ✓ Generated synthetic test data: {n_samples} samples, {n_features} features")
    
    X_train = training_data['X_train']
    y_train = training_data['y_train']
    X_test = training_data['X_test']
    y_test = training_data['y_test']
    
    print(f"  ✓ Data shape: {X_train.shape}")
    print(f"  ✓ Class distribution: {np.unique(y_train, return_counts=True)[1]}")
    print()
    
    # ======================================================================
    # PHASE 1: SMOTE BALANCING
    # ======================================================================
    
    print("[PHASE 1] SMOTE Balancing")
    print("-" * 80)
    
    smote = SMOTE(sampling_strategy='auto', random_state=42)
    X_train_balanced, y_train_balanced = smote.fit_resample(X_train, y_train)
    
    print(f"  ✓ SMOTE applied: {len(X_train)} → {len(X_train_balanced)} samples")
    print()
    
    # ======================================================================
    # PHASE 2: STACKING ENSEMBLE (OPTIMIZED)
    # ======================================================================
    
    print("[PHASE 2] Stacking Ensemble Training")
    print("-" * 80)
    
    print("  Creating base models...")
    base_models = [
        ('xgb', xgb.XGBClassifier(
            n_estimators=300,
            max_depth=7,
            learning_rate=0.05,
            subsample=0.9,
            colsample_bytree=0.8,
            reg_alpha=0.1,
            reg_lambda=1.0,
            random_state=42,
            n_jobs=-1,
            verbosity=0
        )),
        ('rf', RandomForestClassifier(
            n_estimators=250,
            max_depth=16,
            random_state=42,
            n_jobs=-1
        ))
    ]
    
    stacking_phase2 = StackingClassifier(
        estimators=base_models,
        final_estimator=LogisticRegression(max_iter=1000, random_state=42),
        cv=StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    )
    
    print("  Training stacking ensemble...")
    stacking_phase2.fit(X_train_balanced, y_train_balanced)
    
    y_pred_phase2 = stacking_phase2.predict(X_test)
    acc_phase2 = accuracy_score(y_test, y_pred_phase2)
    f1_phase2 = f1_score(y_test, y_pred_phase2, average='weighted', zero_division=0)
    
    print(f"  ✓ Phase 2 Results:")
    print(f"    - Accuracy: {acc_phase2:.4f} (+{(acc_phase2-0.725)*100:.1f}% vs baseline 72.5%)")
    print(f"    - F1-Score: {f1_phase2:.4f}")
    print()
    
    # ======================================================================
    # PHASE 3: FEATURE SELECTION + FINE-TUNING
    # ======================================================================
    
    print("[PHASE 3] Feature Selection + Optimization")
    print("-" * 80)
    
    print("  Computing feature importance...")
    feature_importance = stacking_phase2.estimators_[0].feature_importances_
    threshold = np.percentile(feature_importance, 50)
    selected_indices = np.where(feature_importance >= threshold)[0]
    
    print(f"  ✓ Selected {len(selected_indices)}/{X_train.shape[1]} features (top 50%)")
    
    X_train_selected = X_train_balanced.iloc[:, selected_indices]
    X_test_selected = X_test.iloc[:, selected_indices]
    
    print("  Training optimized ensemble on selected features...")
    
    base_models_phase3 = [
        ('xgb', xgb.XGBClassifier(
            n_estimators=350,
            max_depth=7,
            learning_rate=0.05,
            subsample=0.92,
            colsample_bytree=0.85,
            reg_alpha=0.05,
            reg_lambda=0.8,
            random_state=42,
            n_jobs=-1,
            verbosity=0
        )),
        ('rf', RandomForestClassifier(
            n_estimators=280,
            max_depth=17,
            random_state=42,
            n_jobs=-1
        ))
    ]
    
    stacking_phase3 = StackingClassifier(
        estimators=base_models_phase3,
        final_estimator=LogisticRegression(max_iter=1000, random_state=42),
        cv=StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    )
    
    stacking_phase3.fit(X_train_selected, y_train_balanced)
    
    y_pred_phase3 = stacking_phase3.predict(X_test_selected)
    acc_phase3 = accuracy_score(y_test, y_pred_phase3)
    f1_phase3 = f1_score(y_test, y_pred_phase3, average='weighted', zero_division=0)
    recall_phase3 = recall_score(y_test, y_pred_phase3, average='weighted', zero_division=0)
    
    print(f"  ✓ Phase 3 Results (FINAL):")
    print(f"    - Accuracy: {acc_phase3:.4f} (+{(acc_phase3-0.725)*100:.1f}% vs baseline 72.5%)")
    print(f"    - F1-Score: {f1_phase3:.4f}")
    print(f"    - Recall: {recall_phase3:.4f}")
    print()
    
    # ======================================================================
    # SUMMARY & METRICS
    # ======================================================================
    
    print("[RESULTS SUMMARY]")
    print("-" * 80)
    print(f"  Baseline (XGBoost):        72.5%")
    print(f"  Phase 2 (Stacking):        {acc_phase2:.1%}")
    print(f"  Phase 3 (Optimized):       {acc_phase3:.1%}  ← FINAL MODEL")
    print()
    print(f"  TOTAL IMPROVEMENT:         +{(acc_phase3-0.725)*100:.1f}%")
    print()
    
    # ======================================================================
    # SAVE PRODUCTION ARTIFACTS
    # ======================================================================
    
    print("[PERSISTENCE]")
    print("-" * 80)
    
    os.makedirs("models", exist_ok=True)
    
    class SmartEnergyAIPredictor:
        def __init__(self, model, selected_indices):
            self.model = model
            self.selected_indices = selected_indices
            self.classes = ['BUY', 'SELL', 'HOLD', 'DISCHARGE']
        
        def predict(self, X):
            X_selected = X.iloc[:, self.selected_indices]
            return self.model.predict(X_selected)
        
        def predict_proba(self, X):
            X_selected = X.iloc[:, self.selected_indices]
            return self.model.predict_proba(X_selected)
    
    predictor = SmartEnergyAIPredictor(stacking_phase3, selected_indices)
    
    # Save models
    pickle.dump(stacking_phase2, open("models/phase2_stacking_ensemble.pkl", "wb"))
    print("  ✓ Saved: models/phase2_stacking_ensemble.pkl")
    
    pickle.dump(stacking_phase3, open("models/phase3_optimized_ensemble.pkl", "wb"))
    print("  ✓ Saved: models/phase3_optimized_ensemble.pkl")
    
    pickle.dump(predictor, open("models/production_predictor.pkl", "wb"))
    print("  ✓ Saved: models/production_predictor.pkl")
    
    # Save metadata
    metadata = {
        'accuracy': float(acc_phase3),
        'f1_score': float(f1_phase3),
        'recall': float(recall_phase3),
        'improvement_percent': float((acc_phase3 - 0.725) * 100),
        'features_used': int(len(selected_indices)),
        'total_features': int(X_train.shape[1]),
        'baseline_accuracy': 0.725,
        'selected_indices': selected_indices.tolist()
    }
    
    import json
    with open("models/ml_star_phase3_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)
    
    print("  ✓ Saved: models/ml_star_phase3_metadata.json")
    print()
    
    # ======================================================================
    # DEPLOYMENT INSTRUCTIONS
    # ======================================================================
    
    print("[DEPLOYMENT READY]")
    print("=" * 80)
    print()
    print("To integrate into your Dagster pipeline:")
    print()
    print("1. Load predictor:")
    print("   predictor = pickle.load(open('models/production_predictor.pkl', 'rb'))")
    print()
    print("2. Make predictions:")
    print("   predictions = predictor.predict(X_new)")
    print("   probabilities = predictor.predict_proba(X_new)")
    print()
    print("3. Check metrics:")
    print(f"   Accuracy: {acc_phase3:.1%}")
    print(f"   F1-Score: {f1_phase3:.1%}")
    print(f"   Improvement: +{(acc_phase3-0.725)*100:.1f}% vs baseline")
    print()
    print("=" * 80)
    
except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

sys.exit(0)
