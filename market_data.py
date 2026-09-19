"""
market_data.py

Defines a clean provider interface for fetching NQ and US100 prices,
plus a concrete HTTP-based implementation driven entirely by
environment configuration (see config.py).

This module NEVER invents, hard-codes, or falls back to fake prices.
If live data is not configured or a request fails, it raises a
MarketDataError with a clear, user-facing message. The caller decides
how to handle that (the CLI shows the error and stops, or the user
can switch to --manual mode).
"""

from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import Optional

import requests

from config import Config

DEFAULT_TIMEOUT_SECONDS = 8


class MarketDataError(Exception):
    """Raised whenever live market data cannot be reliably obtained."""


@dataclass(frozen=True)
class PriceQuote:
    """A single validated price along with the symbol it came from."""

    symbol: str
    price: float


class MarketDataProvider(abc.ABC):
    """
    Abstract interface for a market data provider.

    Implementations must raise MarketDataError (not return None, not
    return 0.0, not return a stale/fake price) whenever a valid,
    current price cannot be obtained.
    """

    @abc.abstractmethod
    def get_nq_price(self) -> float:
        ...

    @abc.abstractmethod
    def get_us100_price(self) -> float:
        ...


class HttpMarketDataProvider(MarketDataProvider):
    """
    Generic HTTP JSON market data provider.

    Expects an API that, given `MARKET_DATA_API_URL`, accepts a query
    parameter `symbol` and an `Authorization: Bearer <key>` header, and
    returns JSON containing a numeric price field. This is intentionally
    generic — swap this class out (or adjust `_extract_price`) if your
    actual data vendor uses a different request/response shape. The rest
    of the application only depends on the `MarketDataProvider` interface,
    so replacing the implementation here does not require touching any
    other module.
    """

    # Field names we'll look for in the JSON response, in priority order.
    PRICE_FIELDS = ("price", "last", "lastPrice", "last_price", "value")

    def __init__(self, config: Config, timeout: int = DEFAULT_TIMEOUT_SECONDS):
        self._config = config
        self._timeout = timeout

    def get_nq_price(self) -> float:
        return self._get_price(self._require(self._config.nq_symbol, "NQ_SYMBOL"))

    def get_us100_price(self) -> float:
        return self._get_price(
            self._require(self._config.us100_symbol, "US100_SYMBOL")
        )

    @staticmethod
    def _require(value: Optional[str], name: str) -> str:
        if not value:
            raise MarketDataError(
                f"Live market data is not configured. Missing environment "
                f"variable: {name}."
            )
        return value

    def _get_price(self, symbol: str) -> float:
        if not self._config.market_data_api_url:
            raise MarketDataError("Live market data is not configured.")

        headers = {}
        if self._config.market_data_api_key:
            headers["Authorization"] = f"Bearer {self._config.market_data_api_key}"

        try:
            response = requests.get(
                self._config.market_data_api_url,
                params={"symbol": symbol},
                headers=headers,
                timeout=self._timeout,
            )
        except requests.exceptions.Timeout as exc:
            raise MarketDataError(
                f"Network timeout while fetching price for {symbol}."
            ) from exc
        except requests.exceptions.RequestException as exc:
            raise MarketDataError(
                f"Network error while fetching price for {symbol}: {exc}"
            ) from exc

        if response.status_code == 401 or response.status_code == 403:
            raise MarketDataError(
                "Market data API rejected the request (invalid or missing "
                "API key)."
            )
        if response.status_code != 200:
            raise MarketDataError(
                f"Market data API returned an unexpected status "
                f"({response.status_code}) for {symbol}."
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise MarketDataError(
                f"Market data API returned an invalid (non-JSON) response "
                f"for {symbol}."
            ) from exc

        price = self._extract_price(payload)
        if price is None:
            raise MarketDataError(
                f"Market data API response for {symbol} did not contain a "
                f"recognizable price field."
            )

        if price <= 0:
            raise MarketDataError(
                f"Market data API returned an invalid price for {symbol}: "
                f"{price}."
            )

        return float(price)

    @classmethod
    def _extract_price(cls, payload) -> Optional[float]:
        """Look for a numeric price in a handful of common JSON shapes."""
        if isinstance(payload, (int, float)):
            return float(payload)

        if isinstance(payload, dict):
            for field in cls.PRICE_FIELDS:
                if field in payload:
                    try:
                        return float(payload[field])
                    except (TypeError, ValueError):
                        continue
            # Some APIs nest the quote, e.g. {"data": {"price": ...}}
            for value in payload.values():
                if isinstance(value, (dict, list)):
                    nested = cls._extract_price(value)
                    if nested is not None:
                        return nested

        if isinstance(payload, list) and payload:
            return cls._extract_price(payload[0])

        return None


class ManualMarketDataProvider(MarketDataProvider):
    """A provider backed by two fixed values, used by --manual mode."""

    def __init__(self, nq_price: float, us100_price: float):
        self._nq_price = nq_price
        self._us100_price = us100_price

    def get_nq_price(self) -> float:
        return self._nq_price

    def get_us100_price(self) -> float:
        return self._us100_price


def build_live_provider(config: Config) -> MarketDataProvider:
    """
    Factory for the live provider. Raises MarketDataError immediately
    if the minimum required configuration is missing, rather than
    letting the caller discover it later on first use.
    """
    if not config.is_live_data_configured:
        raise MarketDataError("Live market data is not configured.")
    return HttpMarketDataProvider(config)
