"""Configuration module for Energy ML system."""
import os
from dotenv import load_dotenv

load_dotenv()

# OpenWeatherAPI Configuration
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")
KYIV_LAT = float(os.getenv("OPENWEATHER_LAT", "50.45"))
KYIV_LON = float(os.getenv("OPENWEATHER_LON", "30.52"))
OPENWEATHER_UNITS = os.getenv("OPENWEATHER_UNITS", "metric")
OPENWEATHER_CACHE_TTL = int(os.getenv("OPENWEATHER_CACHE_TTL", "21600"))  # 6 hours

# OREE Configuration (Ukrainian energy market)
OREE_API_URL = os.getenv("OREE_API_URL", "https://www.oree.com.ua/api/")

# Model Configuration
XGBOOST_PARAMS = {
    "n_estimators": 100,
    "max_depth": 6,
    "learning_rate": 0.1,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
}

# Data paths
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
MODELS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "models")

# Ensure directories exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(MODELS_DIR, exist_ok=True)

print(f"✅ Config loaded: Weather API key present: {bool(OPENWEATHER_API_KEY)}")
print(f"✅ Location: Kyiv ({KYIV_LAT}°N, {KYIV_LON}°E)")
