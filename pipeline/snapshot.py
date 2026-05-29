"""
Daily KOSPI 200 snapshot pipeline.

Fetches price, volume, market cap, and investor flow from KRX (via pykrx),
then upserts to Supabase snapshots table.

Usage:
    python pipeline/snapshot.py [YYYYMMDD]   # defaults to last weekday
"""

import os
import sys
from datetime import date, timedelta

# load_dotenv must run before pykrx imports so KRX_ID/KRX_PW are set in time
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

from pykrx import stock  # noqa: E402
from supabase import create_client  # noqa: E402

sb = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_SERVICE_ROLE_KEY"],
)

KOSPI200_INDEX = "1028"


def last_trading_day() -> str:
    """Most recent weekday as YYYYMMDD (holiday-blind — close enough for cron)."""
    d = date.today() - timedelta(days=1)
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d.strftime("%Y%m%d")


def fetch_snapshot(date_str: str) -> list[dict]:
    print(f"[snapshot] date={date_str}")

    # KOSPI 200 constituent tickers
    tickers_200 = stock.get_index_portfolio_deposit_file(
        KOSPI200_INDEX, date_str, alternative=True
    )
    if not tickers_200:
        raise RuntimeError(f"Empty KOSPI 200 constituent list for {date_str}")
    print(f"  constituents: {len(tickers_200)}")

    # Bulk fetches — ~6 KRX API calls total for all 200 tickers
    ohlcv   = stock.get_market_ohlcv_by_ticker(date_str, market="KOSPI")
    caps    = stock.get_market_cap_by_ticker(date_str, market="KOSPI")
    # sector classifications also carries stock names (종목명)
    sectors = stock.get_market_sector_classifications(date_str, market="KOSPI")

    # Investor flow: one bulk call per investor type (value in KRW)
    foreign_df = stock.get_market_net_purchases_of_equities_by_ticker(
        date_str, date_str, "KOSPI", "외국인"
    )
    inst_df = stock.get_market_net_purchases_of_equities_by_ticker(
        date_str, date_str, "KOSPI", "기관합계"
    )

    sector_map = sectors["업종명"].to_dict()  if not sectors.empty else {}
    name_map   = sectors["종목명"].to_dict()  if not sectors.empty else {}

    iso_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
    rows = []
    skipped = 0

    for ticker in tickers_200:
        if ticker not in ohlcv.index:
            skipped += 1
            continue
        try:
            rows.append({
                "ticker": ticker,
                "name":   name_map.get(ticker) or stock.get_market_ticker_name(ticker),
                "date":   iso_date,
                "close":  int(ohlcv.loc[ticker, "종가"]),
                "volume": int(ohlcv.loc[ticker, "거래량"]),
                "market_cap": (
                    int(caps.loc[ticker, "시가총액"]) if ticker in caps.index else None
                ),
                "foreign_net_buy": (
                    int(foreign_df.loc[ticker, "순매수거래대금"])
                    if ticker in foreign_df.index else None
                ),
                "institution_net_buy": (
                    int(inst_df.loc[ticker, "순매수거래대금"])
                    if ticker in inst_df.index else None
                ),
                "sector": sector_map.get(ticker),
            })
        except Exception as e:
            print(f"  SKIP {ticker}: {e}")
            skipped += 1

    print(f"  collected {len(rows)}, skipped {skipped}")
    return rows


UPSERT_BATCH = 50


def store_snapshots(rows: list[dict]) -> None:
    if not rows:
        print("[snapshot] nothing to store")
        return
    total = 0
    for i in range(0, len(rows), UPSERT_BATCH):
        batch = rows[i : i + UPSERT_BATCH]
        result = (
            sb.table("snapshots")
            .upsert(batch, on_conflict="ticker,date")
            .execute()
        )
        total += len(result.data)
        print(f"  batch {i // UPSERT_BATCH + 1}: upserted {len(result.data)} rows")
    print(f"[snapshot] total upserted: {total}")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else last_trading_day()
    rows = fetch_snapshot(target)
    store_snapshots(rows)
    print("[snapshot] done")
