#!/usr/bin/env python3
"""Render supervisor-facing medallion markdown or JSON artifacts."""

from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _load_medallion_module():
    module_name = "smart_energy_ai_medallion_catalog"
    module_path = PROJECT_ROOT / "src" / "data_pipeline" / "medallion_catalog.py"
    module_spec = importlib.util.spec_from_file_location(module_name, module_path)
    if module_spec is None or module_spec.loader is None:
        raise ImportError(f"Unable to load medallion helpers from {module_path}")

    module = sys.modules.get(module_name)
    if module is None:
        module = importlib.util.module_from_spec(module_spec)
        sys.modules[module_name] = module
        module_spec.loader.exec_module(module)
    return module


try:
    from src.data_pipeline.medallion_catalog import render_output, write_output
except (ImportError, KeyError):
    _MEDALLION_MODULE = _load_medallion_module()
    render_output = _MEDALLION_MODULE.render_output
    write_output = _MEDALLION_MODULE.write_output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render medallion catalog markdown or JSON artifacts")
    parser.add_argument("--manifest", required=True, help="Path to the medallion dataset manifest")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown", help="Output format")
    parser.add_argument("--output", required=True, help="Destination file path")
    parser.add_argument("--case-study-tenant", help="Optional tenant id override for the case-study slice")
    parser.add_argument("--include-experiments", action="store_true", help="Force experiment-scorecard rendering for markdown outputs")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rendered = render_output(
        args.manifest,
        output_format=args.format,
        output_path=args.output,
        case_study_tenant=args.case_study_tenant,
        include_experiments=args.include_experiments,
    )
    output_path = write_output(args.output, rendered)
    print(output_path)


if __name__ == "__main__":
    main()