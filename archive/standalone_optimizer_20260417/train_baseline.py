import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error
import joblib
import logging

logger = logging.getLogger(__name__)

def train_baseline_with_real_data():
    """Train baseline model using REAL data"""
    print("--- Starting Baseline Training with REAL Data ---\n")
    
    # Import real data fetchers (fixed import path)
    try:
        from src.data_pipeline.ingest_prices import PriceIngester
    except ModuleNotFoundError:
        import sys
        import os
        # Add project root to path
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from src.data_pipeline.ingest_prices import PriceIngester
    
    logger.info("🔄 Fetching REAL price data for training...\n")
    
    # Fetch REAL prices
    ingester = PriceIngester()
    prices_df = ingester.fetch_oree_prices()
    used_fallback = prices_df is None or prices_df.empty
    
    if used_fallback:
        print("⚠️  OREE prices not available, using realistic fallback for demo...\n")
        # Create realistic fallback
        base_prices = [70, 77, 73, 70, 73, 98, 157, 217, 262, 238, 192, 175, 
                      168, 157, 147, 175, 262, 322, 402, 367, 297, 210, 157, 122]
        df = pd.DataFrame({
            'hour': list(range(24)),
            'price_uah_mwh': base_prices,
            'source': 'realistic_fallback'
        })
        df['price_eur_mwh'] = df['price_uah_mwh'] / 35
        print(f"Using realistic prices: range {df['price_eur_mwh'].min():.2f}-{df['price_eur_mwh'].max():.2f} EUR/MWh\n")
    else:
        print(f"✅ Loaded REAL prices from OREE: {len(prices_df)} hours\n")
        # Add hour column if not present
        if 'hour' not in prices_df.columns:
            prices_df['hour'] = range(len(prices_df))
        df = prices_df.copy()
    
    # Feature Engineering: Extract hour of the day (for hourly patterns)
    if 'hour' not in df.columns:
        df['hour'] = range(len(df))
    
    # Create additional features from hour
    df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
    df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)
    
    # Use price in EUR/MWh for training
    X = df[['hour', 'hour_sin', 'hour_cos']]
    y = df['price_eur_mwh']
    
    # Train model
    model = RandomForestRegressor(n_estimators=100, random_state=42, max_depth=5)
    model.fit(X, y)
    
    # Save the model
    import os
    model_dir = 'projects/smart-energy-ai/models'
    os.makedirs(model_dir, exist_ok=True)
    model_path = os.path.join(model_dir, 'baseline_price_model.joblib')
    joblib.dump(model, model_path)
    print(f"✅ Model trained and saved to {model_path}")
    
    # Feature importance
    print(f"\nFeature Importance:")
    for feature, importance in zip(X.columns, model.feature_importances_):
        print(f"  {feature}: {importance:.4f}")
    
    # Predictions for full day
    print(f"\n📊 Baseline Price Predictions for 24 hours:")
    print(f"{'Hour':>4} {'Predicted (EUR/MWh)':>20} {'Actual (EUR/MWh)':>20}")
    print("-" * 50)
    
    test_hours = np.arange(24).reshape(-1, 1)
    test_features = pd.DataFrame({
        'hour': test_hours.flatten(),
        'hour_sin': np.sin(2 * np.pi * test_hours.flatten() / 24),
        'hour_cos': np.cos(2 * np.pi * test_hours.flatten() / 24)
    })
    
    predictions = model.predict(test_features)
    
    for h in range(24):
        actual = y.iloc[h] if h < len(y) else np.nan
        pred = predictions[h]
        error = abs(actual - pred) if not np.isnan(actual) else 0
        print(f"{h:4d} {pred:20.2f} {actual:20.2f}")
    
    # Metrics
    y_pred = model.predict(X)
    mae = mean_absolute_error(y, y_pred)
    print(f"\nTraining MAE: {mae:.2f} EUR/MWh")
    print(f"\n✅ Baseline training complete")
    print(f"   Data source: {'Realistic fallback' if used_fallback else 'REAL OREE'}")
    print(f"   Hours trained: {len(df)}")
    
    return model

def train_baseline():
    """Legacy function - calls real data version"""
    return train_baseline_with_real_data()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    train_baseline_with_real_data()
