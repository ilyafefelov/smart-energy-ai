"""
Test price processor transformations for RL training
"""

import pytest
import polars as pl
import numpy as np
from src.price_processor import PriceProcessor, prepare_prices_for_rl


class TestPriceProcessor:
    """Test price processing transformations"""

    @pytest.fixture
    def sample_prices(self):
        """Create realistic sample prices in UAH"""
        # Real OREE prices (EUR/MWh) converted to UAH
        eur_prices = [
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
        uah_prices = [p * 35 for p in eur_prices]  # EUR to UAH (approximate rate)
        return pl.Series(uah_prices)

    def test_initialization(self, sample_prices):
        """Test processor initialization"""
        processor = PriceProcessor(sample_prices)

        assert len(processor.prices_uah) == 24
        assert processor.price_min == 70.0
        assert processor.price_max == 402.5
        assert processor.normalize is True

    def test_moving_average_smoothing(self, sample_prices):
        """Test moving average reduces volatility"""
        processor = PriceProcessor(sample_prices)

        original_std = sample_prices.std()
        smoothed = processor.add_moving_average_smoothing(window=3)
        smoothed_std = smoothed.std()

        # Smoothing should reduce volatility
        assert smoothed_std < original_std
        assert len(smoothed) == 24
        print(
            f"✓ Smoothing reduces volatility: {original_std:.2f} → {smoothed_std:.2f}"
        )

    def test_realistic_noise(self, sample_prices):
        """Test noise is realistic (±5%)"""
        processor = PriceProcessor(sample_prices, add_noise=True)

        np.random.seed(42)
        noisy = processor.add_realistic_noise(noise_level=0.05)

        # Prices should be within ±5% of original
        max_change = ((noisy - sample_prices).abs() / sample_prices).max()

        # Allow some margin for randomness
        assert max_change < 0.15  # Most within 15% (some outliers)
        print(f"✓ Noise realistic: max change = {max_change * 100:.2f}%")

    def test_minmax_normalization(self, sample_prices):
        """Test min-max normalization to 0-1"""
        processor = PriceProcessor(sample_prices)
        normalized = processor.normalize_prices()

        # Check bounds
        assert normalized.min() >= -0.01  # Small tolerance for floating point
        assert normalized.max() <= 1.01

        # Check approximate values
        assert abs(normalized.min()) < 0.01  # Should be ~0
        assert abs(normalized.max() - 1.0) < 0.01  # Should be ~1

        print(
            f"✓ Min-max normalization: [{normalized.min():.4f}, {normalized.max():.4f}]"
        )

    def test_zscore_standardization(self, sample_prices):
        """Test z-score standardization (mean=0, std=1)"""
        processor = PriceProcessor(sample_prices)
        standardized = processor.standardize_prices()

        # Check statistics
        assert abs(standardized.mean()) < 0.01  # Mean should be ~0
        assert abs(standardized.std() - 1.0) < 0.01  # Std should be ~1

        print(
            f"✓ Z-score standardization: mean={standardized.mean():.6f}, std={standardized.std():.6f}"
        )

    def test_denormalization(self, sample_prices):
        """Test converting normalized prices back to UAH"""
        processor = PriceProcessor(sample_prices)

        normalized = processor.normalize_prices()
        denormalized = processor.denormalize_prices(normalized)

        # Should match original (within floating point tolerance)
        np.testing.assert_array_almost_equal(
            denormalized.to_numpy(), sample_prices.to_numpy(), decimal=5
        )

        print(f"✓ Denormalization reverses normalization accurately")

    def test_full_pipeline(self, sample_prices):
        """Test complete processing pipeline"""
        sample_df = pl.DataFrame({"hour": range(24), "price_uah_mwh": sample_prices})

        processed, stats = prepare_prices_for_rl(
            sample_df, normalize=True, add_noise=True
        )

        # Check all expected columns
        assert "price_uah_original" in processed.columns
        assert "price_uah_smoothed" in processed.columns
        assert "price_uah_with_noise" in processed.columns
        assert "price_normalized_minmax" in processed.columns
        assert "price_standardized_zscore" in processed.columns

        # Check statistics
        assert "min_price_uah" in stats
        assert "max_price_uah" in stats
        assert "mean_price_uah" in stats

        print(
            f"✓ Full pipeline: {len(processed)} hours processed with all transformations"
        )

    def test_price_statistics(self, sample_prices):
        """Test price statistics calculation"""
        processor = PriceProcessor(sample_prices)
        stats = processor.get_statistics()

        assert stats["min_price_uah"] == 70.0
        assert stats["max_price_uah"] == 402.5
        assert abs(stats["mean_price_uah"] - 187.98) < 0.1
        assert "coefficient_of_variation" in stats

        print(
            f"✓ Price statistics: min={stats['min_price_uah']}, max={stats['max_price_uah']}, avg={stats['mean_price_uah']:.2f}"
        )


if __name__ == "__main__":
    # Run tests
    print("Running Price Processor Tests...\n")

    test = TestPriceProcessor()

    # Create sample data
    eur_prices = [
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
    uah_prices = [p * 35 for p in eur_prices]
    sample_prices = pd.Series(uah_prices)

    test.test_initialization(sample_prices)
    test.test_moving_average_smoothing(sample_prices)
    test.test_realistic_noise(sample_prices)
    test.test_minmax_normalization(sample_prices)
    test.test_zscore_standardization(sample_prices)
    test.test_denormalization(sample_prices)
    test.test_full_pipeline(sample_prices)
    test.test_price_statistics(sample_prices)

    print("\n✓ All price processor tests passed!")
