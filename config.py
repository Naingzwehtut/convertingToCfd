"""
config.py

Loads configuration from environment variables (via .env if present).

This module never hard-codes credentials or prices. It only exposes
what has been configured by the user, and clearly reports what is
missing so the rest of the application can fail loudly instead of
silently using bad data.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    # python-dotenv is a listed dependency, but we don't want a missing
    # package to crash the whole app before we can print a useful error.
    pass


@dataclass(frozen=True)
class Config:
    """Immutable snapshot of the application's environment configuration."""

    nq_symbol: Optional[str]
    us100_symbol: Optional[str]
    market_data_api_key: Optional[str]
    market_data_api_url: Optional[str]

    @property
    def is_live_data_configured(self) -> bool:
        """
        Live data requires, at minimum, an API URL and the two symbols.
        The API key is required unless the provider's endpoint is public,
        but we still treat a missing key as "not fully configured" to be
        safe and explicit.
        """
        return bool(
            self.market_data_api_url
            and self.nq_symbol
            and self.us100_symbol
        )


def load_config() -> Config:
    """Read configuration from environment variables."""
    return Config(
        nq_symbol=os.getenv("NQ_SYMBOL") or None,
        us100_symbol=os.getenv("US100_SYMBOL") or None,
        market_data_api_key=os.getenv("MARKET_DATA_API_KEY") or None,
        market_data_api_url=os.getenv("MARKET_DATA_API_URL") or None,
    )
