from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_legacy_ml_star_artifacts_are_removed() -> None:
    assert not (ROOT / "energy_ml/optimizer/COMPLETION_VERIFICATION.md").exists()
    assert not (ROOT / "energy_ml/optimizer/ML_STAR_COMPREHENSIVE_REPORT.md").exists()
    assert not (ROOT / "energy_ml/optimizer/ML_STAR_DELIVERY_SUMMARY.md").exists()
    assert not (ROOT / "energy_ml/optimizer/ML_STAR_PROJECT_INDEX.md").exists()
    assert not (ROOT / "energy_ml/optimizer/test_ml_star.py").exists()
    assert not (ROOT / "energy_ml/assets/ml_star_optimized_pipeline.py").exists()
    assert not (ROOT / "energy_ml/assets/ml_star_pipeline_support.py").exists()
    assert not (ROOT / "docs/technical/DEPLOYMENT_GUIDE.md").exists()
    assert not (ROOT / "scripts/validate_deployment.py").exists()


def test_docs_index_does_not_list_removed_deployment_guide() -> None:
    docs_index = (ROOT / "docs/README.md").read_text(encoding="utf-8")

    assert "technical/DEPLOYMENT_GUIDE.md" not in docs_index