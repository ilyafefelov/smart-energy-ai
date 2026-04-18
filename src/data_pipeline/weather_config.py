"""Weather configuration helpers shared by orchestration and pipeline modules.

This module is deprecated - use src.infrastructure.settings.get_weather_coords() instead.
Kept for backward compatibility with existing callers.
"""

from __future__ import annotations

from typing import Tuple

from src.infrastructure.settings import get_weather_coords


def _resolve_weather_location() -> Tuple[float, float, str]:
    """Resolve location and timezone for weather fetches (uses centralized settings)."""
    return get_weather_coords()


__all__ = ["_resolve_weather_location"]
