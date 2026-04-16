from src.data_pipeline.synthetic_market import _generate_synthetic_prices


def test_generate_synthetic_prices_returns_expected_shape_and_ranges() -> None:
    result = _generate_synthetic_prices()

    assert len(result) == 48
    assert {"timestamp", "price_eur_mwh", "price_uah_mwh", "volume_mwh", "source"}.issubset(result[0].keys())
    assert all(record["source"] == "SYNTHETIC" for record in result)
    assert all(record["price_eur_mwh"] >= 20 for record in result)
    assert all(record["price_uah_mwh"] > 0 for record in result)
    assert all(record["volume_mwh"] >= 100.0 for record in result)