"""Tests for src.price_processor module."""
import numpy as np
import polars as pl
import pytest
from src.price_processor import PriceProcessor


class TestPriceProcessor:
    """Tests for PriceProcessor class."""
    
    @pytest.fixture
    def sample_prices(self):
        """Create sample price data."""
        return pl.Series("price_uah", [25.0, 30.0, 35.0, 40.0, 45.0, 50.0, 55.0, 60.0])
    
    def test_init_normalize_true(self, sample_prices):
        """Test initialization with normalization enabled."""
        processor = PriceProcessor(sample_prices, normalize=True)
        
        assert processor.normalize is True
        assert processor.price_min == 25.0
        assert processor.price_max == 60.0
    
    def test_init_normalize_false(self, sample_prices):
        """Test initialization with normalization disabled."""
        processor = PriceProcessor(sample_prices, normalize=False)
        
        assert processor.normalize is False
    
    def test_normalize_prices_default(self, sample_prices):
        """Test default normalization uses internal prices."""
        processor = PriceProcessor(sample_prices, normalize=True)
        normalized = processor.normalize_prices()
        
        assert normalized.min() >= 0.0
        assert normalized.max() <= 1.0
    
    def test_standardize_prices(self, sample_prices):
        """Test standardization."""
        processor = PriceProcessor(sample_prices, normalize=True)
        standardized = processor.standardize_prices()
        
        assert abs(standardized.mean()) < 0.01
        assert abs(standardized.std() - 1.0) < 0.01
    
    def test_moving_average_smoothing(self, sample_prices):
        """Test moving average smoothing."""
        processor = PriceProcessor(sample_prices, normalize=False)
        smoothed = processor.add_moving_average_smoothing(window=3)
        
        assert len(smoothed) == len(sample_prices)
    
    def test_add_noise(self, sample_prices):
        """Test adding noise."""
        processor = PriceProcessor(sample_prices, normalize=False, add_noise=True)
        noisy = processor.add_realistic_noise(noise_level=0.05)
        
        assert len(noisy) == len(sample_prices)
    
    def test_denormalize_prices(self, sample_prices):
        """Test denormalization."""
        processor = PriceProcessor(sample_prices, normalize=True)
        normalized = processor.normalize_prices()
        denormalized = processor.denormalize_prices(normalized)
        
        assert abs(denormalized.min() - 25.0) < 0.01
        assert abs(denormalized.max() - 60.0) < 0.01
    
    def test_original_prices_preserved(self, sample_prices):
        """Test that original prices are preserved."""
        processor = PriceProcessor(sample_prices, normalize=True)
        
        assert processor.original_prices is not None
        assert len(processor.original_prices) == len(sample_prices)
