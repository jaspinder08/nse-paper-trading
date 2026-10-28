"""Angel One SmartAPI market data provider implementation.

STRICT SAFETY MANDATE:
This provider is restricted exclusively to read-only market data:
- Instrument master retrieval
- Historical candlestick ingestion
- Provider health checking

Under NO circumstances are broker order placement, modification, or cancellation APIs
implemented or permitted in this provider.
"""

import asyncio
import base64
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import hmac
import logging
import os
import random
import struct
import time
from typing import Any, Callable, Dict, List, Optional
import httpx
from trading_engine.market_data.base import AbstractMarketDataProvider
from trading_engine.market_data.rate_limiter import AsyncTokenBucketRateLimiter
from trading_engine.market_data.types import HistoricalCandle, InstrumentRecord
from shared.market_time import IST_ZONE, to_ist

logger = logging.getLogger("angel_one_provider")


def generate_totp(secret: str) -> str:
    """Generate RFC 6238 TOTP 6-digit passcode without external pyotp dependency."""
    cleaned_secret = secret.strip().replace(" ", "").upper()
    missing_padding = len(cleaned_secret) % 8
    if missing_padding:
        cleaned_secret += "=" * (8 - missing_padding)

    key = base64.b32decode(cleaned_secret, casefold=True)
    counter = struct.pack(">Q", int(time.time() // 30))
    mac = hmac.new(key, counter, hashlib.sha1).digest()
    offset = mac[-1] & 0x0F
    code = (struct.unpack(">I", mac[offset : offset + 4])[0] & 0x7FFFFFFF) % 1000000
    return str(code).zfill(6)


class AngelOneMarketDataProvider(AbstractMarketDataProvider):
    """Production market-data client for Angel One SmartAPI."""

    SCRIP_MASTER_URL = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
    BASE_API_URL = "https://apiconnect.angelone.in"

    # Map application timeframe strings to Angel One SmartAPI parameters
    TIMEFRAME_MAP = {
        "1m": "ONE_MINUTE",
        "3m": "THREE_MINUTE",
        "5m": "FIVE_MINUTE",
        "10m": "TEN_MINUTE",
        "15m": "FIFTEEN_MINUTE",
        "30m": "THIRTY_MINUTE",
        "1h": "ONE_HOUR",
        "1d": "ONE_DAY",
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        client_code: Optional[str] = None,
        password: Optional[str] = None,
        totp_key: Optional[str] = None,
        rate_limit_rps: float = 3.0,
    ) -> None:
        self.api_key = api_key or os.getenv("SMARTAPI_API_KEY", "")
        self.client_code = client_code or os.getenv("SMARTAPI_CLIENT_CODE", "")
        self.password = password or os.getenv("SMARTAPI_PASSWORD", "")
        self.totp_key = totp_key or os.getenv("SMARTAPI_TOTP_KEY", "")

        self._rate_limiter = AsyncTokenBucketRateLimiter(rate_limit_per_second=rate_limit_rps)
        self._jwt_token: Optional[str] = None
        self._feed_token: Optional[str] = None
        self._client: Optional[httpx.AsyncClient] = None
        self._connected: bool = False

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=httpx.Timeout(20.0, connect=10.0))
        return self._client

    async def connect(self) -> None:
        await self._get_client()
        self._connected = True

    async def disconnect(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
        self._connected = False
        self._jwt_token = None

    def is_connected(self) -> bool:
        return self._connected

    async def authenticate(self) -> None:
        """Authenticate with Angel One SmartAPI using TOTP and API Key."""
        if not self.api_key or not self.client_code or not self.password:
            raise ValueError(
                "Missing Angel One SmartAPI credentials. SMARTAPI_API_KEY, "
                "SMARTAPI_CLIENT_CODE, and SMARTAPI_PASSWORD must be configured in environment."
            )

        totp_code = generate_totp(self.totp_key) if self.totp_key else ""
        url = f"{self.BASE_API_URL}/rest/auth/angelbroking/user/v1/loginByPassword"
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-UserType": "USER",
            "X-SourceID": "WEB",
            "X-ClientLocalIP": "127.0.0.1",
            "X-ClientPublicIP": "127.0.0.1",
            "X-MACAddress": "02:00:00:00:00:00",
            "X-PrivateKey": self.api_key,
        }
        payload = {
            "clientcode": self.client_code,
            "password": self.password,
            "totp": totp_code,
        }

        await self._rate_limiter.acquire()
        client = await self._get_client()
        response = await client.post(url, headers=headers, json=payload)

        if response.status_code != 200:
            raise RuntimeError(f"Angel One SmartAPI login failed with HTTP {response.status_code}")

        res_json = response.json()
        if not res_json.get("status"):
            err_msg = res_json.get("message", "Authentication error")
            raise RuntimeError(f"Angel One SmartAPI authentication rejected: {err_msg}")

        data = res_json.get("data", {})
        self._jwt_token = data.get("jwtToken")
        self._feed_token = data.get("feedToken")
        self._connected = True
        logger.info("Angel One SmartAPI authenticated successfully (Session established).")

    async def health(self) -> bool:
        """Check provider connectivity without disclosing secrets."""
        try:
            client = await self._get_client()
            resp = await client.get(f"{self.BASE_API_URL}/health", timeout=5.0)
            return resp.status_code in (200, 404)  # Server reachable
        except Exception:
            return False

    async def fetch_instruments(self) -> List[InstrumentRecord]:
        """Download and parse verified NSE instruments from Angel One Scrip Master."""
        await self._rate_limiter.acquire()
        client = await self._get_client()
        logger.info("Downloading official Angel One OpenAPI Scrip Master...")

        resp = await client.get(self.SCRIP_MASTER_URL)
        if resp.status_code != 200:
            raise RuntimeError(f"Failed to fetch Scrip Master: HTTP {resp.status_code}")

        records = resp.json()
        instruments: List[InstrumentRecord] = []

        for item in records:
            if item.get("exch_seg") != "NSE":
                continue

            symbol = item.get("symbol", "")
            # Filter standard equity listings (ending in -EQ)
            if not symbol.endswith("-EQ") and item.get("instrumenttype") != "EQ":
                continue

            clean_symbol = symbol[:-3] if symbol.endswith("-EQ") else symbol
            token = str(item.get("token", ""))
            name = item.get("name", clean_symbol)

            try:
                lotsize = int(item.get("lotsize", 1) or 1)
            except (ValueError, TypeError):
                lotsize = 1

            try:
                # Angel One tick size is given in paise or decimal; standardize to 0.05
                raw_tick = float(item.get("tick_size", 5.0) or 5.0)
                tick_decimal = Decimal("0.05") if raw_tick >= 1.0 else Decimal(str(raw_tick))
            except (ValueError, TypeError):
                tick_decimal = Decimal("0.05")

            instruments.append(
                InstrumentRecord(
                    exchange="NSE",
                    symbol=clean_symbol,
                    name=name,
                    token=token,
                    instrument_type="EQUITY",
                    lot_size=lotsize,
                    tick_size=tick_decimal,
                    active=True,
                )
            )

        logger.info("Parsed %d NSE equity instruments from Scrip Master.", len(instruments))
        return instruments

    async def fetch_historical_candles(
        self,
        *,
        exchange: str,
        token: str,
        interval: str,
        start: datetime,
        end: datetime,
    ) -> List[HistoricalCandle]:
        """Fetch historical candlesticks from Angel One Historical Candle API with backoff."""
        if not self._jwt_token:
            await self.authenticate()

        smart_interval = self.TIMEFRAME_MAP.get(interval)
        if not smart_interval:
            raise ValueError(f"Unsupported timeframe '{interval}'. Allowed: {list(self.TIMEFRAME_MAP.keys())}")

        # Format dates as YYYY-MM-DD HH:MM
        from_str = to_ist(start).strftime("%Y-%m-%d %H:%M")
        to_str = to_ist(end).strftime("%Y-%m-%d %H:%M")

        url = f"{self.BASE_API_URL}/rest/secure/angelbroking/historical/v1/getCandleData"
        headers = {
            "Authorization": f"Bearer {self._jwt_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-UserType": "USER",
            "X-SourceID": "WEB",
            "X-ClientLocalIP": "127.0.0.1",
            "X-ClientPublicIP": "127.0.0.1",
            "X-MACAddress": "02:00:00:00:00:00",
            "X-PrivateKey": self.api_key,
        }
        payload = {
            "exchange": exchange,
            "symboltoken": token,
            "interval": smart_interval,
            "fromdate": from_str,
            "todate": to_str,
        }

        # Bounded exponential backoff retry loop
        max_retries = 3
        backoff_seconds = 1.0
        last_error = None

        for attempt in range(max_retries):
            await self._rate_limiter.acquire()
            client = await self._get_client()
            try:
                resp = await client.post(url, headers=headers, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    if not data.get("status"):
                        err_msg = data.get("message", "Unknown provider response")
                        # If session expired, re-authenticate on next retry
                        if "token" in err_msg.lower() or "unauthorized" in err_msg.lower():
                            await self.authenticate()
                            headers["Authorization"] = f"Bearer {self._jwt_token}"
                            continue
                        raise RuntimeError(f"SmartAPI historical candle error: {err_msg}")

                    raw_candles = data.get("data", [])
                    result: List[HistoricalCandle] = []

                    for c in raw_candles:
                        # Format: [timestamp_str, open, high, low, close, volume]
                        ts_str, o, h, l, cl, v = c[0], c[1], c[2], c[3], c[4], c[5]
                        dt = datetime.fromisoformat(ts_str)
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=IST_ZONE)

                        result.append(
                            HistoricalCandle(
                                timestamp=dt,
                                open=Decimal(str(o)),
                                high=Decimal(str(h)),
                                low=Decimal(str(l)),
                                close=Decimal(str(cl)),
                                volume=int(v),
                                complete=True,
                            )
                        )
                    return result

                elif resp.status_code == 429:
                    jitter = random.uniform(0.1, 0.5)
                    await asyncio.sleep(backoff_seconds + jitter)
                    backoff_seconds *= 2.0
                    continue
                else:
                    last_error = RuntimeError(f"SmartAPI returned HTTP {resp.status_code}: {resp.text}")
                    await asyncio.sleep(backoff_seconds)
                    backoff_seconds *= 2.0

            except (httpx.RequestError, asyncio.TimeoutError) as exc:
                last_error = exc
                await asyncio.sleep(backoff_seconds)
                backoff_seconds *= 2.0

        raise RuntimeError(f"Failed to fetch historical candles after {max_retries} attempts: {last_error}")

    async def subscribe_ticks(self, symbols: List[str], callback: Callable[[Dict[str, Any]], None]) -> None:
        raise NotImplementedError("Live WebSocket streaming is deferred to Phase 3.")

    async def unsubscribe_ticks(self, symbols: List[str]) -> None:
        raise NotImplementedError("Live WebSocket streaming is deferred to Phase 3.")
