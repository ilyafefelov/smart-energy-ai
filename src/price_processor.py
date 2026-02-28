"""
Price data processing for RL training
Handles real UAH prices with optional transformations for neural network input
"""

import polars as pl
import numpy as np
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class PriceProcessor:
    """Process real price data for RL training"""

    def __init__(
        self, prices_uah: pl.Series, normalize: bool = True, add_noise: bool = False
    ):
        """
        Initialize price processor

        Args:
            prices_uah: Series of prices in UAH/MWh (real market prices)
            normalize: Whether to normalize prices to 0-1 range
            add_noise: Whether to add realistic noise (±5% variation)
        """
        self.original_prices = prices_uah.clone()  # Keep original for reference
        self.prices_uah = prices_uah.clone()
        self.normalize = normalize
        self.add_noise = add_noise

        # Store normalization bounds for later denormalization
        self.price_min = self.prices_uah.min()
        self.price_max = self.prices_uah.max()
        self.price_mean = self.prices_uah.mean()
        self.price_std = self.prices_uah.std()

    def add_moving_average_smoothing(self, window: int = 3) -> pl.Series:
        """
        Smooth price volatility with moving average

        Args:
            window: Window size for moving average (default 3 hours)

        Returns:
            Smoothed prices
        """
        smoothed = self.prices_uah.rolling_mean(
            window_size=window, center=True, min_samples=1
        )

        logger.info(f"Applied {window}-hour moving average smoothing")
        logger.info(f"Original volatility (std): {self.prices_uah.std():.2f}")
        logger.info(f"Smoothed volatility (std): {smoothed.std():.2f}")

        return smoothed

    def add_realistic_noise(self, noise_level: float = 0.05) -> pl.Series:
        """
        Add realistic noise to prices (±5% variation)
        Models forecasting errors and intraday market volatility

        Args:
            noise_level: Percentage noise (default 0.05 = ±5%)

        Returns:
            Prices with added noise
        """
        noise = np.random.normal(0, noise_level, size=len(self.prices_uah))
        noisy_prices = self.prices_uah * (1 + noise)

        logger.info(f"Added realistic noise (±{noise_level * 100:.1f}%)")
        logger.info(f"Noise std: {(self.prices_uah * noise_level).std():.2f} UAH/MWh")

        return noisy_prices

    def normalize_prices(self, prices: pl.Series = None) -> pl.Series:
        """
        Min-max normalization to 0-1 range
        Better for neural network input

        Args:
            prices: Prices to normalize (uses self.prices_uah if None)

        Returns:
            Normalized prices (0-1 range)
        """
        if prices is None:
            prices = self.prices_uah

        normalized = (prices - self.price_min) / (self.price_max - self.price_min)

        logger.info(f"Normalized prices to 0-1 range")
        logger.info(f"Min: {normalized.min():.4f}, Max: {normalized.max():.4f}")

        return normalized

    def standardize_prices(self, prices: pl.Series = None) -> pl.Series:
        """
        Z-score standardization (mean=0, std=1)
        Alternative normalization approach

        Args:
            prices: Prices to standardize (uses self.prices_uah if None)

        Returns:
            Standardized prices
        """
        if prices is None:
            prices = self.prices_uah

        standardized = (prices - self.price_mean) / self.price_std

        logger.info(f"Standardized prices (z-score)")
        logger.info(f"Mean: {standardized.mean():.6f}, Std: {standardized.std():.6f}")

        return standardized

    def denormalize_prices(
        self, normalized_prices: pl.Series or np.ndarray
    ) -> pl.Series or np.ndarray:
        """
        Convert normalized prices back to UAH/MWh
        Used for converting RL agent actions back to real prices

        Args:
            normalized_prices: Normalized price values (0-1)

        Returns:
            Prices in UAH/MWh
        """
        if isinstance(normalized_prices, pl.Series):
            denormalized = (
                normalized_prices * (self.price_max - self.price_min) + self.price_min
            )
            return denormalized
        else:
            denormalized = (
                normalized_prices * (self.price_max - self.price_min) + self.price_min
            )
            return denormalized

    def destandardize_prices(
        self, standardized_prices: pl.Series or np.ndarray
    ) -> pl.Series or np.ndarray:
        """
        Convert standardized prices back to UAH/MWh

        Args:
            standardized_prices: Standardized price values (z-score)

        Returns:
            Prices in UAH/MWh
        """
        if isinstance(standardized_prices, pl.Series):
            denormalized = (standardized_prices * self.price_std) + self.price_mean
            return denormalized
        else:
            denormalized = (standardized_prices * self.price_std) + self.price_mean
            return denormalized

    def process_for_training(self) -> pl.DataFrame:
        """
        Full pipeline: smoothing → noise → normalization

        Returns:
            DataFrame with original prices and all transformations
        """
        result = pl.DataFrame()

        # 1. Original prices (keep for reference)
        result = result.with_columns([self.original_prices.alias("price_uah_original")])

        # 2. Apply smoothing
        smoothed = self.add_moving_average_smoothing(window=3)
        result = result.with_columns([smoothed.alias("price_uah_smoothed")])

        # 3. Add realistic noise
        if self.add_noise:
            noisy = self.add_realistic_noise(noise_level=0.05)
            result = result.with_columns([noisy.alias("price_uah_with_noise")])
            training_prices = noisy
        else:
            training_prices = smoothed

        # 4. Normalize for NN input
        if self.normalize:
            normalized = self.normalize_prices(training_prices)
            standardized = self.standardize_prices(training_prices)

            result = result.with_columns(
                [
                    normalized.alias("price_normalized_minmax"),  # 0-1 range
                    standardized.alias("price_standardized_zscore"),  # mean=0, std=1
                ]
            )

            logger.info("Processing complete: original → smoothed → noise → normalized")
            logger.info(f"Recommended RL input: price_normalized_minmax (0-1 range)")

        return result

    def get_statistics(self) -> dict:
        """Get price statistics for analysis"""
        return {
            "min_price_uah": float(self.price_min),
            "max_price_uah": float(self.price_max),
            "mean_price_uah": float(self.price_mean),
            "std_price_uah": float(self.price_std),
            "price_range_uah": float(self.price_max - self.price_min),
            "coefficient_of_variation": float(self.price_std / self.price_mean),
        }


def prepare_prices_for_rl(
    df: pl.DataFrame, normalize: bool = True, add_noise: bool = False
) -> Tuple[pl.DataFrame, dict]:
    """
    Main function: Prepare prices for RL training

    Args:
        df: DataFrame with 'price_uah_mwh' column
        normalize: Apply normalization to 0-1 range
        add_noise: Add ±5% realistic noise

    Returns:
        Processed DataFrame, Statistics dict
    """
    processor = PriceProcessor(
        df["price_uah_mwh"], normalize=normalize, add_noise=add_noise
    )

    processed_df = processor.process_for_training()
    stats = processor.get_statistics()

    logger.info("\n=== Price Processing Complete ===")
    logger.info(f"Statistics:\n{stats}")

    return processed_df, stats


if __name__ == "__main__":
    # Test with REAL data
    logging.basicConfig(level=logging.INFO)

    print("🔄 Fetching REAL price data from OREE Ukraine...\n")

    # Import real data fetcher
    try:
        from src.data_pipeline.ingest_prices import PriceIngester

        ingester = PriceIngester()
        prices_df = ingester.fetch_oree_prices()
    except:
        prices_df = None

    if prices_df is None or prices_df.is_empty():
        print("⚠️  OREE not available, using realistic simulation...\n")
        # Fallback: realistic market pattern
        base_prices_eur = [
            2.5,
            2.2,
            2.1,
            2.0,
            2.1,
            2.8,
            4.5,
            6.2,
            7.5,
            6.8,
            5.5,
            5.0,
            4.8,
            4.5,
            4.2,
            5.0,
            7.5,
            9.2,
            11.5,
            10.5,
            8.5,
            6.0,
            4.5,
            3.5,
        ]
        prices_uah = [p * 35 for p in base_prices_eur]
        sample_df = pl.DataFrame(
            {
                "hour": range(24),
                "price_uah_mwh": prices_uah,
                "source": "realistic_simulation",
            }
        )
        print(f"Using realistic prices (UAH): {prices_uah}\n")
    else:
        sample_df = prices_df.clone()
        print(f"✅ Got REAL prices from OREE")
        print(f"   Hours: {len(sample_df)}")
        print(
            f"   Range: {sample_df['price_uah_mwh'].min():.2f} - {sample_df['price_uah_mwh'].max():.2f} UAH/MWh"
        )
        print(f"   Source: {sample_df.get_column('source').to_list()[0]}\n")

    # Process for RL training
    processed, stats = prepare_prices_for_rl(sample_df, normalize=True, add_noise=True)

    print("\n=== Processed Prices ===")
    print(processed.head(10))
    print("\n=== Statistics ===")
    for key, value in stats.items():
        print(f"{key}: {value}")
    print(
        f"\n✅ Price processor test complete (using {'REAL' if prices_df is not None else 'realistic'} data)"
    )
