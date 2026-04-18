#!/usr/bin/env python3
"""Unified CLI entry point for Smart Energy AI.

Provides a single command interface for all major operations:

    python -m src.cli ingest-weather [--latitude LAT] [--longitude LON]
    python -m src.cli ingest-prices
    python -m src.cli optimize [--scenario SCENARIO]
    python -m src.cli train-rl [--train-days DAYS] [--timesteps STEPS]

Can also be installed as a console script entry point via pip/setuptools.
"""

from __future__ import annotations

import argparse
import logging
import sys
from typing import Optional

logger = logging.getLogger(__name__)


def create_parser() -> argparse.ArgumentParser:
    """Create the main argument parser with all subcommands."""
    parser = argparse.ArgumentParser(
        prog="smart-energy-ai",
        description="Smart Energy AI - Intelligent energy management and optimization system",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 1.0.0",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        title="commands",
        description="Available commands",
        required=True,
    )

    # ingest-weather command
    weather_parser = subparsers.add_parser(
        "ingest-weather",
        help="Ingest weather data from Open-Meteo API",
        description="Fetch 24-hour weather forecast and store in PostgreSQL",
    )
    weather_parser.add_argument(
        "--latitude",
        type=float,
        default=50.45,
        help="Location latitude (default: Kyiv 50.45)",
    )
    weather_parser.add_argument(
        "--longitude",
        type=float,
        default=30.52,
        help="Location longitude (default: Kyiv 30.52)",
    )
    weather_parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level",
    )

    # ingest-prices command
    prices_parser = subparsers.add_parser(
        "ingest-prices",
        help="Ingest electricity prices from OREE Ukraine",
        description="Fetch Day-Ahead Market prices and store in PostgreSQL",
    )
    prices_parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level",
    )

    # optimize command
    optimize_parser = subparsers.add_parser(
        "optimize",
        help="Run energy optimization with real data",
        description="Execute battery scheduling optimization using real market data",
    )
    optimize_parser.add_argument(
        "--scenario",
        type=str,
        default="Normal",
        choices=["Normal", "Winter", "Blackout"],
        help="Optimization scenario",
    )
    optimize_parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level",
    )

    # train-rl command
    rl_parser = subparsers.add_parser(
        "train-rl",
        help="Train RL agent for energy optimization",
        description="Train a PPO reinforcement learning agent for battery control",
    )
    rl_parser.add_argument(
        "--train-days",
        type=int,
        default=7,
        help="Number of days of data to use for training",
    )
    rl_parser.add_argument(
        "--timesteps",
        type=int,
        default=2400,
        help="Total training timesteps",
    )
    rl_parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level",
    )

    return parser


def main(args: Optional[list[str]] = None) -> int:
    """Main CLI entry point."""
    parser = create_parser()
    parsed = parser.parse_args(args)

    # Setup basic logging
    logging.basicConfig(
        level=getattr(logging, parsed.log_level.upper(), logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stderr,
    )

    command = parsed.command

    if command == "ingest-weather":
        from src.commands.ingest_weather import ingest_weather_command
        success = ingest_weather_command(
            latitude=parsed.latitude,
            longitude=parsed.longitude,
            log_level=parsed.log_level,
        )
    elif command == "ingest-prices":
        from src.commands.ingest_prices import ingest_prices_command
        success = ingest_prices_command(log_level=parsed.log_level)
    elif command == "optimize":
        from src.commands.optimize import optimize_command
        success = optimize_command(
            scenario=parsed.scenario,
            log_level=parsed.log_level,
        )
    elif command == "train-rl":
        from src.commands.train_rl import train_rl_command
        success = train_rl_command(
            train_days=parsed.train_days,
            timesteps=parsed.timesteps,
            log_level=parsed.log_level,
        )
    else:
        logger.error(f"Unknown command: {command}")
        parser.print_help()
        return 1

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())