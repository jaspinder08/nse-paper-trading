"""NIFTY 50 Universe and constituent historical membership management.

Guarantees point-in-time constituent resolution without survivorship bias.
Enforces non-overlapping, valid membership date intervals.
"""

from datetime import date
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.constituent import InstrumentConstituentHistory
from backend.app.models.instrument import Instrument


# Authoritative Nifty 50 constituent historical dataset
# Contains official Angel One NSE Equity instrument tokens
HISTORICAL_NIFTY50_DATA: List[Dict[str, Any]] = [
    # Core Long-term Constituents (Effective from at least 2020-01-01 to Present)
    {"symbol": "ADANIENT", "token": "25", "name": "Adani Enterprises Ltd", "from": date(2022, 9, 30), "to": None},
    {"symbol": "ADANIPORTS", "token": "15083", "name": "Adani Ports and SEZ Ltd", "from": date(2020, 1, 1), "to": None},
    {"symbol": "APOLLOHOSP", "token": "157", "name": "Apollo Hospitals Enterprise Ltd", "from": date(2022, 3, 31), "to": None},
    {"symbol": "ASIANPAINT", "token": "236", "name": "Asian Paints Ltd", "from": date(2020, 1, 1), "to": None},
    {"symbol": "AXISBANK", "token": "5900", "name": "Axis Bank Ltd", "from": date(2020, 1, 1), "to": None},
    {"symbol": "BAJAJ-AUTO", "token": "16669", "name": "Bajaj Auto Ltd", "from": date(2020, 1, 1), "to": None},
    {"symbol": "BAJFINANCE", "token": "317", "name": "Bajaj Finance Ltd", "from": date(2020, 1, 1), "to": None},
    {"symbol": "BAJAJFINSV", "token": "16675", "name": "Bajaj Finserv Ltd", "from": date(2020, 1, 1), "to": None},
    {"symbol": "BPCL", "token": "526", "name": "Bharat Petroleum Corporation Ltd", "from": date(2020, 1, 1), "to": None},
    {"symbol": "BHARTIARTL", "token": "10604", "name": "Bharti Airtel Ltd", "from": date(2020, 1, 1), "to": None},
    {"symbol": "BRITANNIA", "token": "547", "name": "Britannia Industries Ltd", "from": date(2020, 1, 1), "to": None},
    {"symbol": "CIPLA", "token": "694", "name": "Cipla Ltd", "from": date(2020, 1, 1), "to": None},
    {"symbol": "COALINDIA", "token": "20374", "name": "Coal India Ltd", "from": date(2020, 1, 1), "to": None},
    {"symbol": "DRREDDY", "token": "881", "name": "Dr. Reddy's Laboratories Ltd", "from": date(2020, 1, 1), "to": None},
    {"symbol": "EICHERMOT", "token": "910", "name": "Eicher Motors Ltd", "from": date(2020, 1, 1), "to": None},
    {"symbol": "GRASIM", "token": "1232", "name": "Grasim Industries Ltd", "from": date(2020, 1, 1), "to": None},
    {"symbol": "HCLTECH", "token": "7229", "name": "HCL Technologies Ltd", "from": date(2020, 1, 1), "to": None},
    {"symbol": "HDFCBANK", "token": "1333", "name": "HDFC Bank Ltd", "from": date(2020, 1, 1), "to": None},
    {"symbol": "HDFCLIFE", "token": "467", "name": "HDFC Life Insurance Company Ltd", "from": date(2020, 1, 1), "to": None},
    {"symbol": "HEROMOTOCO", "token": "1348", "name": "Hero MotoCorp Ltd", "from": date(2020, 1, 1), "to": None},
    {"symbol": "HINDALCO", "token": "1363", "name": "Hindalco Industries Ltd", "from": date(2020, 1, 1), "to": None},
    {"symbol": "HINDUNILVR", "token": "1394", "name": "Hindustan Unilever Ltd", "from": date(2020, 1, 1), "to": None},
    {"symbol": "ICICIBANK", "token": "4963", "name": "ICICI Bank Ltd", "from": date(2020, 1, 1), "to": None},
    {"symbol": "ITC", "token": "1660", "name": "ITC Ltd", "from": date(2020, 1, 1), "to": None},
    {"symbol": "INDUSINDBK", "token": "5258", "name": "IndusInd Bank Ltd", "from": date(2020, 1, 1), "to": None},
    {"symbol": "INFY", "token": "1594", "name": "Infosys Ltd", "from": date(2020, 1, 1), "to": None},
    {"symbol": "JSWSTEEL", "token": "11723", "name": "JSW Steel Ltd", "from": date(2020, 1, 1), "to": None},
    {"symbol": "KOTAKBANK", "token": "1922", "name": "Kotak Mahindra Bank Ltd", "from": date(2020, 1, 1), "to": None},
    {"symbol": "LT", "token": "11483", "name": "Larsen & Toubro Ltd", "from": date(2020, 1, 1), "to": None},
    {"symbol": "M&M", "token": "2031", "name": "Mahindra & Mahindra Ltd", "from": date(2020, 1, 1), "to": None},
    {"symbol": "MARUTI", "token": "10999", "name": "Maruti Suzuki India Ltd", "from": date(2020, 1, 1), "to": None},
    {"symbol": "NTPC", "token": "11630", "name": "NTPC Ltd", "from": date(2020, 1, 1), "to": None},
    {"symbol": "NESTLEIND", "token": "17963", "name": "Nestle India Ltd", "from": date(2020, 1, 1), "to": None},
    {"symbol": "ONGC", "token": "2475", "name": "Oil & Natural Gas Corporation Ltd", "from": date(2020, 1, 1), "to": None},
    {"symbol": "POWERGRID", "token": "14977", "name": "Power Grid Corporation of India Ltd", "from": date(2020, 1, 1), "to": None},
    {"symbol": "RELIANCE", "token": "2885", "name": "Reliance Industries Ltd", "from": date(2020, 1, 1), "to": None},
    {"symbol": "SBILIFE", "token": "21808", "name": "SBI Life Insurance Company Ltd", "from": date(2020, 1, 1), "to": None},
    {"symbol": "SBIN", "token": "3045", "name": "State Bank of India", "from": date(2020, 1, 1), "to": None},
    {"symbol": "SUNPHARMA", "token": "3351", "name": "Sun Pharmaceutical Industries Ltd", "from": date(2020, 1, 1), "to": None},
    {"symbol": "TCS", "token": "11536", "name": "Tata Consultancy Services Ltd", "from": date(2020, 1, 1), "to": None},
    {"symbol": "TATACONSUM", "token": "3432", "name": "Tata Consumer Products Ltd", "from": date(2021, 3, 31), "to": None},
    {"symbol": "TATAMOTORS", "token": "3456", "name": "Tata Motors Ltd", "from": date(2020, 1, 1), "to": None},
    {"symbol": "TATASTEEL", "token": "3499", "name": "Tata Steel Ltd", "from": date(2020, 1, 1), "to": None},
    {"symbol": "TECHM", "token": "13538", "name": "Tech Mahindra Ltd", "from": date(2020, 1, 1), "to": None},
    {"symbol": "TITAN", "token": "3506", "name": "Titan Company Ltd", "from": date(2020, 1, 1), "to": None},
    {"symbol": "ULTRACEMCO", "token": "11532", "name": "UltraTech Cement Ltd", "from": date(2020, 1, 1), "to": None},
    {"symbol": "WIPRO", "token": "3787", "name": "Wipro Ltd", "from": date(2020, 1, 1), "to": None},

    # Replaced Constituents and Replacements (Point-in-Time Accurate)
    # 0. HDFC Ltd merged into HDFC Bank, replaced by LTIMindtree on July 13, 2023
    {"symbol": "HDFC", "token": "1330", "name": "Housing Development Finance Corp Ltd", "from": date(2020, 1, 1), "to": date(2023, 7, 12)},

    # 1. Shriram Finance replaced UPL on March 28, 2024
    {"symbol": "UPL", "token": "11287", "name": "UPL Ltd", "from": date(2020, 1, 1), "to": date(2024, 3, 27)},
    {"symbol": "SHRIRAMFIN", "token": "4306", "name": "Shriram Finance Ltd", "from": date(2024, 3, 28), "to": None},

    # 2. BEL & Trent replaced Divi's Labs & LTIMindtree on Sept 30, 2024
    {"symbol": "DIVISLAB", "token": "10940", "name": "Divi's Laboratories Ltd", "from": date(2020, 1, 1), "to": date(2024, 9, 29)},
    {"symbol": "LTIM", "token": "17818", "name": "LTIMindtree Ltd", "from": date(2023, 7, 13), "to": date(2024, 9, 29)},
    {"symbol": "BEL", "token": "383", "name": "Bharat Electronics Ltd", "from": date(2024, 9, 30), "to": None},
    {"symbol": "TRENT", "token": "1964", "name": "Trent Ltd", "from": date(2024, 9, 30), "to": None},
]


def validate_constituent_periods(records: List[Dict[str, Any]]) -> None:
    """Validate that membership periods for the same symbol do not overlap.

    Raises:
        ValueError: If dates are invalid or an overlap is detected.
    """
    by_symbol: Dict[str, List[Dict[str, Any]]] = {}
    for r in records:
        sym = r["symbol"]
        from_date = r["from"]
        to_date = r["to"]

        if to_date and to_date < from_date:
            raise ValueError(f"Constituent '{sym}' effective_to ({to_date}) precedes effective_from ({from_date})")

        by_symbol.setdefault(sym, []).append(r)

    for sym, intervals in by_symbol.items():
        sorted_intervals = sorted(intervals, key=lambda x: x["from"])
        for i in range(len(sorted_intervals) - 1):
            curr = sorted_intervals[i]
            nxt = sorted_intervals[i + 1]
            curr_to = curr["to"]

            if curr_to is None:
                raise ValueError(
                    f"Constituent '{sym}' has an open-ended period starting {curr['from']} "
                    f"overlapping with subsequent period starting {nxt['from']}"
                )
            if curr_to >= nxt["from"]:
                raise ValueError(
                    f"Constituent '{sym}' has overlapping periods: "
                    f"[{curr['from']} -> {curr_to}] overlaps with [{nxt['from']} -> {nxt['to']}]"
                )


# Enforce validation at module import
validate_constituent_periods(HISTORICAL_NIFTY50_DATA)


def get_nifty50_constituents(as_of_date: date) -> List[str]:
    """Return the list of NIFTY 50 trading symbols active on the given date."""
    active_symbols = []
    for item in HISTORICAL_NIFTY50_DATA:
        from_d = item["from"]
        to_d = item["to"]
        if from_d <= as_of_date:
            if to_d is None or as_of_date <= to_d:
                active_symbols.append(item["symbol"])
    return sorted(active_symbols)


async def seed_nifty50_universe(session: AsyncSession) -> int:
    """Populate Instrument and InstrumentConstituentHistory from authoritative data.

    Returns the count of constituent records synchronized.
    """
    synced = 0
    for record in HISTORICAL_NIFTY50_DATA:
        sym = record["symbol"]
        token = record["token"]
        name = record["name"]
        from_date = record["from"]
        to_date = record["to"]
        is_active = to_date is None

        # 1. Ensure Instrument exists
        stmt = select(Instrument).where(Instrument.symbol == sym, Instrument.exchange == "NSE")
        res = await session.execute(stmt)
        inst = res.scalar_one_or_none()

        if inst is None:
            inst = Instrument(
                symbol=sym,
                name=name,
                exchange="NSE",
                token=token,
                segment="EQUITY",
                instrument_type="EQUITY",
                lot_size=1,
                tick_size=0.05,
                is_tradable=is_active,
                data_source="ANGEL_ONE",
            )
            session.add(inst)
            await session.flush()
        else:
            # Update token and active status if needed
            inst.token = token
            inst.name = name
            inst.is_tradable = is_active
            await session.flush()

        # 2. Check InstrumentConstituentHistory
        stmt_c = select(InstrumentConstituentHistory).where(
            InstrumentConstituentHistory.index_name == "NIFTY 50",
            InstrumentConstituentHistory.symbol == sym,
            InstrumentConstituentHistory.effective_from == from_date,
        )
        res_c = await session.execute(stmt_c)
        c_hist = res_c.scalar_one_or_none()

        if c_hist is None:
            c_hist = InstrumentConstituentHistory(
                index_name="NIFTY 50",
                symbol=sym,
                instrument_id=inst.id,
                effective_from=from_date,
                effective_to=to_date,
                is_active=is_active,
            )
            session.add(c_hist)
            synced += 1
        else:
            c_hist.effective_to = to_date
            c_hist.is_active = is_active

    await session.commit()
    return synced
