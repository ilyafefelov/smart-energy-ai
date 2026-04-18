"""Model training asset with MLflow model logging.

This asset demonstrates the modern MLflow "LoggedModel" approach where:
1. Models are logged with mlflow.sklearn.log_model()
2. Model metadata is captured with model_id
3. Benchmark metrics can be linked to specific model versions

Reference: https://mlflow.org/docs/latest/model-registry.html
"""

from datetime import datetime, timezone
from pathlib import Path

from dagster import asset, AssetIn
import mlflow
import pandas as pd
import polars as pl

from src.data_pipeline.benchmark_helpers import FORECAST_VALUE_SCORECARD_SCHEMA


def _ensure_src_in_path():
    """Ensure src/ is in sys.path for subprocess execution."""
    import sys
    from pathlib import Path as PathLib

    try:
        import physics.economics
        return
    except ImportError:
        pass

    src_dir = Path(__file__).resolve().parents[1]
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))


@asset(
    group_name="benchmarks",
    description="Train and log ML model with MLflow LoggedModel API",
    ins={
        "market_data": AssetIn("market_data_asset"),
        "forecast_scorecard": AssetIn("forecast_value_benchmark_asset"),
    },
)
def trained_model_asset(
    market_data: pl.DataFrame,
    forecast_scorecard: pl.DataFrame,
) -> pl.DataFrame:
    """
    Train a simple ML model and log it using MLflow's LoggedModel API.
    
    This demonstrates the modern MLflow approach where:
    - mlflow.sklearn.log_model() returns model_info with model_id
    - mlflow.get_logged_model(model_id) retrieves metadata
    - Metrics can be linked to specific model versions

    Returns DataFrame with logged model metadata.
    """
    _ensure_src_in_path()
    
    mlflow.set_tracking_uri("http://localhost:5000")
    mlflow.set_experiment(experiment_id="0")  # Match existing experiment

    # Convert market_data to pandas for sklearn
    pdf = market_data.to_pandas()
    
    # Simple feature engineering
    if "price_eur_mwh" in pdf.columns and len(pdf) > 24:
        pdf = pdf.sort_values("timestamp")
        pdf["price_lag1"] = pdf["price_eur_mwh"].shift(1)
        pdf["price_lag2"] = pdf["price_eur_mwh"].shift(2)
        pdf["price_ma3"] = pdf["price_eur_mwh"].rolling(3).mean()
        pdf = pdf.dropna()
        
        if len(pdf) > 50:
            # Prepare features and target
            feature_cols = ["price_lag1", "price_lag2", "price_ma3"]
            target_col = "price_eur_mwh"
            
            X = pdf[feature_cols]
            y = pdf[target_col]
            
            # Train/test split
            split_idx = int(len(X) * 0.8)
            X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
            y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
            
            # Import sklearn components
            from sklearn.ensemble import GradientBoostingRegressor
            from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
            
            # Train model
            model = GradientBoostingRegressor(
                n_estimators=50,
                max_depth=3,
                learning_rate=0.1,
                random_state=42,
            )
            model.fit(X_train, y_train)
            
            # Evaluate
            predictions = model.predict(X_test)
            rmse = mean_squared_error(y_test, predictions) ** 0.5
            mae = mean_absolute_error(y_test, predictions)
            r2 = r2_score(y_test, predictions)
            
            # ============================================================
            # MODERN MLFLOW LOGGING - LoggedModel API
            # ============================================================
            
            with mlflow.start_run(run_name="sklearn_price_model_v1") as training_run:
                # Log the model with mlflow.sklearn.log_model()
                # This returns a ModelInfo object with model_id
                model_info = mlflow.sklearn.log_model(
                    sk_model=model,
                    name="price_forecast_gbr",
                    params={
                        "n_estimators": 50,
                        "max_depth": 3,
                        "learning_rate": 0.1,
                    },
                    input_example=X_train.head(5),
                    registered_model_name="smart_energy_price_forecast" if False else None,  # Don't register yet
                )
                
                # Get the LoggedModel entity using the model_id
                logged_model = mlflow.get_logged_model(model_info.model_id)
                
                print(f"Model logged with ID: {logged_model.model_id}")
                print(f"Model params: {logged_model.params}")
                
                # Log metrics linked to the specific model version
                mlflow.log_metrics(
                    metrics={
                        "train_rmse": rmse,
                        "train_mae": mae,
                        "train_r2": r2,
                        "train_samples": len(X_train),
                        "test_samples": len(X_test),
                    },
                    model_id=logged_model.model_id,  # Link metrics to model
                )
                
                # Log additional metadata
                mlflow.log_params({
                    "model_family": "gradient_boosting",
                    "forecast_horizon_hours": 1,
                    "features": ",".join(feature_cols),
                    "training_timestamp": datetime.now(timezone.utc).isoformat(),
                })
                
                # Inspect the LoggedModel with metrics
                logged_model_with_metrics = mlflow.get_logged_model(model_info.model_id)
                print(f"Model metrics: {logged_model_with_metrics.metrics}")
                
                # Store the model_id and metadata for downstream use
                model_metadata = {
                    "model_id": logged_model.model_id,
                    "model_name": "price_forecast_gbr",
                    "model_family": "gradient_boosting",
                    "model_version": logged_model.version if hasattr(logged_model, 'version') else 1,
                    "params": logged_model.params,
                    "run_id": training_run.info.run_id,
                    "artifact_uri": model_info.artifact_uri,
                    "logged_at": datetime.now(timezone.utc).isoformat(),
                    "rmse": rmse,
                    "mae": mae,
                    "r2": r2,
                }
                
                return pl.DataFrame([model_metadata])
    
    # If not enough data, return empty result
    return pl.DataFrame(schema={
        "model_id": pl.Utf8,
        "model_name": pl.Utf8,
        "model_family": pl.Utf8,
        "model_version": pl.Int64,
        "params": pl.Utf8,
        "run_id": pl.Utf8,
        "artifact_uri": pl.Utf8,
        "logged_at": pl.Utf8,
        "rmse": pl.Float64,
        "mae": pl.Float64,
        "r2": pl.Float64,
    })


@asset(
    group_name="benchmarks",
    description="Query logged model metadata from MLflow",
    ins={
        "trained_model": AssetIn("trained_model_asset"),
    },
)
def model_metadata_asset(trained_model: pl.DataFrame) -> pl.DataFrame:
    """
    Query and display metadata from logged MLflow models.
    
    This demonstrates how to use mlflow.get_logged_model() to:
    - Retrieve model parameters
    - Check model metrics
    - Verify model lineage
    """
    _ensure_src_in_path()
    
    mlflow.set_tracking_uri("http://localhost:5000")
    
    metadata_results = []
    
    for row in trained_model.to_dicts():
        model_id = row.get("model_id")
        if not model_id:
            continue
            
        try:
            # Get logged model metadata
            logged_model = mlflow.get_logged_model(model_id)
            
            result = {
                "model_id": model_id,
                "model_name": row.get("model_name"),
                "params": str(logged_model.params),
                "metrics": str(logged_model.metrics) if logged_model.metrics else None,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "status": "success",
            }
        except Exception as e:
            result = {
                "model_id": model_id,
                "model_name": row.get("model_name"),
                "params": None,
                "metrics": None,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "status": f"error: {str(e)}",
            }
        
        metadata_results.append(result)
    
    return pl.DataFrame(metadata_results)