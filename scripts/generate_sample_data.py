"""
Sample data generator for RL training
Creates 7 days of realistic weather + price data
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.db import SessionLocal
from src.models import WeatherForecast, MarketPrice
import logging

logger = logging.getLogger(__name__)


class SampleDataGenerator:
    """Generate realistic training data"""

    def __init__(self):
        self.session = SessionLocal()

    def generate_weather_data(self, days=7, start_date=None):
        """Generate realistic weather forecast data"""
        if start_date is None:
            start_date = datetime.now()

        data = []
        for day in range(days):
            date = start_date + timedelta(days=day)
            
            # Winter pattern: low solar, cloudy
            for hour in range(24):
                timestamp = date.replace(hour=hour)
                
                # Temperature: -5°C baseline + daily variation
                temp = -5 + 8 * np.sin(hour / 12 * np.pi) + np.random.normal(0, 1)
                
                # Solar radiation: peak at noon, very low in winter
                if 6 <= hour <= 18:
                    radiation = 400 * np.sin((hour - 6) / 12 * np.pi) * (1 - 0.7)  # 70% clouds
                    radiation = max(0, radiation + np.random.normal(0, 50))
                else:
                    radiation = 0

                # Cloudcover: high in winter (70-95%)
                cloudcover = 80 + np.random.normal(0, 10)
                cloudcover = np.clip(cloudcover, 0, 100)

                # Wind: moderate (2-5 m/s)
                wind = 3 + np.random.normal(0, 1)
                wind = np.clip(wind, 0, 15)

                # Humidity: high (60-80%)
                humidity = 70 + np.random.normal(0, 8)
                humidity = np.clip(humidity, 0, 100)

                data.append({
                    'timestamp': timestamp,
                    'temperature': temp,
                    'solar_radiation': radiation,
                    'cloudcover': cloudcover,
                    'wind_speed': wind,
                    'humidity': humidity
                })

        return pd.DataFrame(data)

    def generate_price_data(self, days=7, start_date=None):
        """Generate realistic DAM prices"""
        if start_date is None:
            start_date = datetime.now()

        data = []
        for day in range(days):
            date = start_date + timedelta(days=day)
            
            # Ukrainian market pattern
            for hour in range(24):
                timestamp = date.replace(hour=hour)
                
                # Base hourly pattern (peak morning + evening)
                if 7 <= hour <= 10:  # Morning peak
                    base_price = 8.0 + np.random.normal(0, 0.5)
                elif 17 <= hour <= 21:  # Evening peak
                    base_price = 10.0 + np.random.normal(0, 0.8)
                elif 0 <= hour <= 6:  # Night (cheapest)
                    base_price = 2.5 + np.random.normal(0, 0.3)
                else:  # Daytime off-peak
                    base_price = 5.0 + np.random.normal(0, 0.4)

                # Add day-of-week effect (Monday-Friday higher)
                dow = date.weekday()
                if dow < 5:  # Weekday
                    base_price *= 1.05
                else:  # Weekend
                    base_price *= 0.95

                # Ensure realistic bounds
                price_eur = np.clip(base_price, 0.5, 20.0)
                price_uah = price_eur * 35  # Rough conversion

                data.append({
                    'timestamp': timestamp,
                    'price_eur_mwh': price_eur,
                    'price_uah_mwh': price_uah,
                    'min_price': price_eur * 0.95,
                    'max_price': price_eur * 1.05,
                    'source': 'sample_generated'
                })

        return pd.DataFrame(data)

    def store_weather_data(self, df):
        """Store weather data in PostgreSQL"""
        count = 0
        try:
            for _, row in df.iterrows():
                record = WeatherForecast(
                    timestamp=row['timestamp'],
                    temperature=row['temperature'],
                    solar_radiation=row['solar_radiation'],
                    cloudcover=row['cloudcover'],
                    wind_speed=row['wind_speed'],
                    humidity=row['humidity']
                )
                self.session.add(record)
                count += 1

            self.session.commit()
            logger.info(f"✓ Stored {count} weather records")
            return count
        except Exception as e:
            self.session.rollback()
            logger.error(f"✗ Failed to store weather data: {e}")
            return 0

    def store_price_data(self, df):
        """Store price data in PostgreSQL"""
        count = 0
        try:
            for _, row in df.iterrows():
                record = MarketPrice(
                    timestamp=row['timestamp'],
                    price_eur_mwh=row['price_eur_mwh'],
                    price_uah_mwh=row['price_uah_mwh'],
                    min_price=row['min_price'],
                    max_price=row['max_price'],
                    source=row['source']
                )
                self.session.add(record)
                count += 1

            self.session.commit()
            logger.info(f"✓ Stored {count} price records")
            return count
        except Exception as e:
            self.session.rollback()
            logger.error(f"✗ Failed to store price data: {e}")
            return 0

    def generate_and_store(self, days=7):
        """Generate and store sample data"""
        logger.info(f"Generating sample data for {days} days...")

        # Generate data
        weather_df = self.generate_weather_data(days)
        price_df = self.generate_price_data(days)

        # Store
        weather_count = self.store_weather_data(weather_df)
        price_count = self.store_price_data(price_df)

        # Save to CSV for reference
        weather_df.to_csv('data/training/sample_weather.csv', index=False)
        price_df.to_csv('data/training/sample_prices.csv', index=False)

        logger.info(f"✓ Generated and stored sample data")
        logger.info(f"  Weather: {weather_count} records")
        logger.info(f"  Prices: {price_count} records")

        self.session.close()

        return weather_df, price_df


def main():
    """Main entry point"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    generator = SampleDataGenerator()
    weather_df, price_df = generator.generate_and_store(days=7)

    print("\n📊 Sample Data Generated")
    print(f"\nWeather Data (first 3 rows):")
    print(weather_df.head(3))
    print(f"\nPrice Data (first 3 rows):")
    print(price_df.head(3))
    print(f"\nTotal records generated:")
    print(f"  Weather: {len(weather_df)} rows (7 days × 24 hours)")
    print(f"  Prices: {len(price_df)} rows (7 days × 24 hours)")
    print(f"\nCSV files saved:")
    print(f"  data/training/sample_weather.csv")
    print(f"  data/training/sample_prices.csv")


if __name__ == "__main__":
    main()
