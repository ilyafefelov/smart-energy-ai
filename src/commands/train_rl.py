"""RL training command.

Wraps the existing RL training functionality from src/rl_training.py into a
CLI-command-compatible function with proper logging and error handling.
"""

from __future__ import annotations

import argparse
import logging
import sys
from typing import Optional

logger = logging.getLogger(__name__)


def train_rl_command(
    train_days: int = 7,
    timesteps: int = 2400,
    log_level: str = "INFO",
) -> bool:
    """Execute RL agent training as a CLI command.

    Args:
        train_days: Number of days of data to use for training
        timesteps: Total training timesteps
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)

    Returns:
        True if training succeeded, False otherwise
    """
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    logger.info(f"Starting RL training - {train_days} days, {timesteps} timesteps")

    try:
        from src.rl_training import train_rl_agent

        results = train_rl_agent(train_days=train_days)

        if results.get("training", {}).get("status") in ["completed", "completed_simple"]:
            logger.info("✅ RL training completed successfully")

            # Print summary
            print("\n=== TRAINING RESULTS ===")
            print(f"Status: {results['training']['status']}")
            if 'timesteps' in results['training']:
                print(f"Timesteps: {results['training']['timesteps']}")

            if 'evaluation' in results:
                eval_res = results['evaluation']
                if eval_res.get('status') == 'completed':
                    print("\n=== EVALUATION RESULTS ===")
                    print(f"Average Cost: {eval_res['avg_cost']:.1f} UAH")
                    print(f"Average Reward: {eval_res['avg_reward']:.2f}")
                    print(f"Min Cost: {eval_res['min_cost']:.1f} UAH")
                    print(f"Max Cost: {eval_res['max_cost']:.1f} UAH")

            return True
        else:
            logger.error(f"❌ RL training failed: {results.get('message', 'Unknown error')}")
            return False

    except Exception as e:
        logger.exception(f"Unexpected error during RL training: {e}")
        return False


def main(args: Optional[list[str]] = None) -> int:
    """CLI entry point for the train-rl command."""
    parser = argparse.ArgumentParser(description="Train RL agent for energy optimization")
    parser.add_argument(
        "--train-days",
        type=int,
        default=7,
        help="Number of days of data to use for training",
    )
    parser.add_argument(
        "--timesteps",
        type=int,
        default=2400,
        help="Total training timesteps",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level",
    )

    parsed = parser.parse_args(args)
    success = train_rl_command(
        train_days=parsed.train_days,
        timesteps=parsed.timesteps,
        log_level=parsed.log_level,
    )
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())