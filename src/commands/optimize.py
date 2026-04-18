"""Optimization command.

Wraps the existing RealDataOptimizer from src/optimizer_real.py into a
CLI-command-compatible function with proper logging and error handling.
"""

from __future__ import annotations

import argparse
import logging
import sys
from typing import Optional

logger = logging.getLogger(__name__)


def optimize_command(
    scenario: str = "Normal",
    log_level: str = "INFO",
) -> bool:
    """Execute energy optimization as a CLI command.

    Args:
        scenario: Optimization scenario (Normal, Winter, Blackout)
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)

    Returns:
        True if optimization succeeded, False otherwise
    """
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    logger.info(f"Starting optimization - Scenario: {scenario}")

    try:
        from src.optimizer_real import RealDataOptimizer

        optimizer = RealDataOptimizer()
        df = optimizer.run_optimization(scenario=scenario)

        if df is not None:
            logger.info(f"✅ Optimization completed: {len(df)} hours")
            # Print summary
            print(f"\n{'='*70}")
            print(f"✅ {scenario.upper()} SCENARIO - OPTIMIZATION RESULTS")
            print(f"{'='*70}")
            print(df[["Hour", "Price_UAH", "Solar", "Load", "Action", "SOC"]].to_string(index=False))
            return True
        else:
            logger.error("❌ Optimization failed - no results generated")
            return False

    except Exception as e:
        logger.exception(f"Unexpected error during optimization: {e}")
        return False


def main(args: Optional[list[str]] = None) -> int:
    """CLI entry point for the optimize command."""
    parser = argparse.ArgumentParser(description="Run energy optimization with real data")
    parser.add_argument(
        "--scenario",
        type=str,
        default="Normal",
        choices=["Normal", "Winter", "Blackout"],
        help="Optimization scenario",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level",
    )

    parsed = parser.parse_args(args)
    success = optimize_command(
        scenario=parsed.scenario,
        log_level=parsed.log_level,
    )
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())