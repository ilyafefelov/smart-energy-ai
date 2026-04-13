from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_legacy_notion_script_is_removed() -> None:
    assert not (ROOT / "scripts/create_notion_docs.py").exists()