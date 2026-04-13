from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_active_docs_point_to_canonical_runtime_surfaces() -> None:
    stage2_plan = _read("docs/Stage 2/plan.md")
    project_schematic = _read("docs/technical/PROJECT_SCHEMATIC.md")
    configuration_system = _read("docs/technical/CONFIGURATION_SYSTEM.md")

    assert "ml_integration_api.py — current Python bridge" not in stage2_plan
    assert "energy_ml/ml_integration_api.py — current Python bridge" not in stage2_plan
    assert "ml_integration_api.py — canonical Python bridge" in stage2_plan

    assert "Method 3: Streamlit Dashboard (Recommended!)" not in configuration_system
    assert "streamlit run streamlit_dashboard/app_config.py" not in configuration_system
    assert "dashboard/ is the canonical operator UI" in configuration_system

    assert "There is no active root-level `nuxt_dashboard/` runtime anymore." in project_schematic