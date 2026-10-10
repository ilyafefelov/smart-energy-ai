import pandas as pd
import datetime
import logging

logger = logging.getLogger(__name__)

def fetch_sample_energy_data():
    """
    DEPRECATED: This function creates sample/dummy data
    
    For REAL data, use:
    - WeatherIngester: src.data_pipeline.ingest_weather
    - PriceIngester: src.data_pipeline.ingest_prices
    
    This function is kept for backwards compatibility only.
    """
    print("⚠️  WARNING: Using SAMPLE/DUMMY DATA from fetch_sample_energy_data()")
    print("   This is DEPRECATED - use real data APIs instead!\n")
    
    logger.warning("fetch_sample_energy_data() called - using dummy data (DEPRECATED)")
    
    print("Initializing SAMPLE data collection (testing only)...")
    # Create 24 hours of SAMPLE data
    base = datetime.datetime(2024, 1, 1, 0, 0)
    timestamps = [base + datetime.timedelta(hours=x) for x in range(24)]
    
    # Sample price curve (low at night, peak in morning and evening)
    prices = [65.2, 58.1, 55.0, 52.3, 54.0, 60.5, 75.2, 88.0, 95.1, 92.0, 85.5, 80.0, 
              78.2, 77.5, 82.0, 90.5, 110.2, 125.0, 115.3, 105.0, 95.5, 88.0, 80.2, 70.0]
              
    # Sample solar curve (peak at noon)
    solar = [0, 0, 0, 0, 0, 5, 25, 60, 120, 180, 220, 240, 
             235, 210, 160, 90, 30, 5, 0, 0, 0, 0, 0, 0]
             
    df = pd.DataFrame({
        'timestamp': timestamps,
        'price_eur_mwh': prices,
        'solar_gen_kw': solar,
        'source': 'sample_data_dummy'  # Mark as sample
    })
    
    output_path = 'projects/smart-energy-ai/data/raw/sample_energy_data.csv'
    df.to_csv(output_path, index=False)
    print(f"⚠️  SAMPLE data saved to {output_path}")
    print("   ⚠️  This is DUMMY DATA - not for production!\n")
    print("--- SAMPLE DATA PREVIEW (DUMMY) ---")
    print(df.head(10))
    return df

def fetch_real_energy_data():
    """
    Fetch REAL energy data from APIs
    
    Uses:
    - WeatherIngester for real weather
    - PriceIngester for real OREE prices
    """
    from src.data_pipeline.ingest_weather import WeatherIngester
    from src.data_pipeline.ingest_prices import PriceIngester
    
    logger.info("🔄 Fetching REAL energy data...")
    
    # Fetch weather
    weather_ingester = WeatherIngester()
    weather_data = weather_ingester.fetch_weather()
    
    if not weather_data:
        logger.error("Failed to fetch weather")
        return None
    
    weather_df = weather_ingester.parse_weather_data(weather_data)
    
    # Fetch prices
    price_ingester = PriceIngester()
    prices_df = price_ingester.fetch_oree_prices()
    
    if prices_df is None or prices_df.empty:
        logger.warning("OREE prices not available, using realistic fallback")
        # Create realistic fallback
        prices_df = pd.DataFrame({
            'price_eur_mwh': [70/35, 77/35, 73/35, 70/35, 73/35, 98/35, 157/35, 217/35, 262/35, 238/35, 192/35, 175/35,
                            168/35, 157/35, 147/35, 175/35, 262/35, 322/35, 402/35, 367/35, 297/35, 210/35, 157/35, 122/35],
            'source': 'realistic_fallback'
        })
    
    # Merge weather and prices
    df = pd.concat([weather_df.reset_index(drop=True), prices_df.reset_index(drop=True)], axis=1)
    
    logger.info(f"✅ REAL data fetched: {len(df)} hours")
    return df

if __name__ == "__main__":
    import sys
    
    # Default: use REAL data
    print("Data Fetcher - Energy Optimization System")
    print("=" * 50)
    
    if '--sample' in sys.argv or '--dummy' in sys.argv:
        print("\n📝 Using SAMPLE/DUMMY data (for testing only)...\n")
        fetch_sample_energy_data()
    else:
        print("\n🌐 Using REAL data from APIs...\n")
        df = fetch_real_energy_data()
        if df is not None:
            print("\n--- REAL DATA PREVIEW ---")
            print(df.head(10))
        else:
            print("Failed to fetch real data, trying sample fallback...")
            fetch_sample_energy_data()
