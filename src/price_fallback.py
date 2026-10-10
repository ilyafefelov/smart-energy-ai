"""
Price fallback for when OREE is unreachable
"""
import pandas as pd
from datetime import datetime

def get_sample_prices():
    """Generate realistic sample prices for demo"""
    prices = [
        14.24, 5.50, 3.80, 2.90, 2.45, 3.20, 8.90, 12.50,
        15.30, 11.20, 8.50, 6.70, 5.40, 4.90, 7.30, 10.80,
        13.60, 14.90, 12.30, 9.70, 7.20, 5.80, 4.50, 3.90
    ]
    
    now = datetime.now()
    return pd.DataFrame([
        {
            'hour': h,
            'timestamp': now.replace(hour=h, minute=0, second=0, microsecond=0),
            'price_eur_mwh': prices[h],
            'price_uah_mwh': prices[h] * 35,
            'source': 'sample'
        }
        for h in range(24)
    ])

def get_prices_with_fallback():
    """Try real OREE, fallback to samples"""
    try:
        from src.oree_real_prices import OREERealPriceFetcher
        fetcher = OREERealPriceFetcher()
        prices_df = fetcher.fetch_oree_prices()
        if prices_df is not None and len(prices_df) > 0:
            return prices_df, True
    except:
        pass
    
    # Fallback
    return get_sample_prices(), False
