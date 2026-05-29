"""
Signal Score calculation for KOSPI 200 snapshots.

Reads history from Supabase snapshots table, computes 4 factors
cross-sectionally ranked within KOSPI 200, then writes signal_score
and grade back to the target date's rows.

Factors:
  Momentum  (30%)  — 5-day price return
  Volume    (25%)  — today's volume vs 20-day avg (z-score)
  Fund Flow (25%)  — (foreign + inst net buy) / market_cap
  Volatility (20%) — inverse of 20-day daily return std dev

Grades: S ≥ 90 | A ≥ 80 | B ≥ 65 | C ≥ 50 | D < 50

Usage:
    python pipeline/score.py [YYYYMMDD | YYYY-MM-DD]
"""

import os
import sys
from datetime import date, timedelta

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

sb = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_SERVICE_ROLE_KEY"],
)

WEIGHTS = {"momentum": 0.30, "volume": 0.25, "fund_flow": 0.25, "volatility": 0.20}
LOOKBACK = 25   # trading days to pull for rolling metrics
BATCH    = 50   # upsert batch size


def last_trading_day() -> str:
    d = date.today() - timedelta(days=1)
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d.strftime("%Y-%m-%d")


def to_iso(s: str) -> str:
    return f"{s[:4]}-{s[4:6]}-{s[6:]}" if len(s) == 8 else s


def assign_grade(score: float) -> str:
    if score >= 90: return "S"
    if score >= 80: return "A"
    if score >= 65: return "B"
    if score >= 50: return "C"
    return "D"


def pct_rank(series: pd.Series) -> pd.Series:
    """Percentile rank within valid values → 0–100. NaN stays NaN."""
    return series.rank(method="average", pct=True).mul(100)


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_history(iso_date: str) -> tuple[pd.DataFrame, list[dict]]:
    """
    Returns:
      df         — long-format history (last LOOKBACK dates, all 200 tickers)
      target_rows — full snapshot dicts for iso_date (used for upsert)
    """
    target_resp = (
        sb.table("snapshots").select("*").eq("date", iso_date).execute()
    )
    target_rows = target_resp.data
    if not target_rows:
        raise RuntimeError(
            f"No snapshot rows for {iso_date}. Run snapshot.py first."
        )

    tickers = [r["ticker"] for r in target_rows]

    # Find last LOOKBACK available dates using one anchor ticker (cheap query)
    dates_resp = (
        sb.table("snapshots")
        .select("date")
        .eq("ticker", tickers[0])
        .lte("date", iso_date)
        .order("date", desc=True)
        .limit(LOOKBACK)
        .execute()
    )
    lookback_dates = sorted([r["date"] for r in dates_resp.data])

    # Fetch per date so each query stays well under the 1000-row default cap
    all_rows: list[dict] = []
    for d in lookback_dates:
        resp = (
            sb.table("snapshots")
            .select("ticker,date,close,volume,market_cap,foreign_net_buy,institution_net_buy")
            .in_("ticker", tickers)
            .eq("date", d)
            .execute()
        )
        all_rows.extend(resp.data)

    df = pd.DataFrame(all_rows)
    df["date"] = pd.to_datetime(df["date"])
    for col in ["close", "volume", "market_cap", "foreign_net_buy", "institution_net_buy"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.sort_values(["ticker", "date"]).reset_index(drop=True)

    n_dates = df["date"].nunique()
    print(f"  history: {len(df)} rows across {n_dates} trading days")
    if n_dates < 6:
        print(
            f"  NOTE: only {n_dates} day(s) of history — rolling metrics need 6+.\n"
            "  Run snapshot.py for more past dates to get accurate scores.\n"
            "  Fund Flow factor will still be meaningful today."
        )

    return df, target_rows


# ---------------------------------------------------------------------------
# Score computation
# ---------------------------------------------------------------------------

def compute_scores(df: pd.DataFrame, iso_date: str) -> pd.DataFrame:
    target_dt = pd.Timestamp(iso_date)
    tickers = df[df["date"] == target_dt]["ticker"].tolist()

    close_w = df.pivot(index="date", columns="ticker", values="close").sort_index()
    vol_w   = df.pivot(index="date", columns="ticker", values="volume").sort_index()
    n       = len(close_w)

    # -- Momentum: 5-day return --
    if n >= 6:
        m_raw = (close_w.iloc[-1] - close_w.iloc[-6]) / close_w.iloc[-6].replace(0, np.nan)
    else:
        m_raw = pd.Series(np.nan, index=close_w.columns)

    # -- Volume: z-score vs prior 20-day avg (excluding today) --
    prior_vol = vol_w.iloc[:-1]
    if len(prior_vol) >= 2:
        vstd = prior_vol.std().replace(0, np.nan)
        v_raw = (vol_w.iloc[-1] - prior_vol.mean()) / vstd
    else:
        v_raw = pd.Series(np.nan, index=vol_w.columns)

    # -- Volatility: negative of 20-day return std dev (lower vol = better) --
    prior_ret = close_w.pct_change().iloc[:-1]
    if len(prior_ret) >= 2:
        vlt_raw = -prior_ret.std()
    else:
        vlt_raw = pd.Series(np.nan, index=close_w.columns)

    # -- Fund Flow: (foreign + inst net buy) / market_cap --
    today = df[df["date"] == target_dt].set_index("ticker")
    ff_raw = (
        today["foreign_net_buy"].fillna(0) + today["institution_net_buy"].fillna(0)
    ) / today["market_cap"].replace(0, np.nan)

    # Percentile rank each factor across the 200 tickers
    def rank(s: pd.Series) -> pd.Series:
        return pct_rank(s.reindex(tickers))

    sm  = rank(m_raw)
    sv  = rank(v_raw)
    svl = rank(vlt_raw)
    sf  = rank(ff_raw)

    # Weighted sum — NaN factors fall back to neutral 50
    signal = (
        sm.fillna(50.0)  * WEIGHTS["momentum"]
        + sv.fillna(50.0)  * WEIGHTS["volume"]
        + sf.fillna(50.0)  * WEIGHTS["fund_flow"]
        + svl.fillna(50.0) * WEIGHTS["volatility"]
    )

    rows = [
        {"ticker": t, "signal_score": round(float(signal[t]), 2), "grade": assign_grade(signal[t])}
        for t in tickers
    ]
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def write_scores(scores: pd.DataFrame, target_rows: list[dict], iso_date: str) -> None:
    score_map = scores.set_index("ticker")[["signal_score", "grade"]].to_dict("index")
    updated = []
    for row in target_rows:
        t = row["ticker"]
        if t in score_map:
            row["signal_score"] = score_map[t]["signal_score"]
            row["grade"]        = score_map[t]["grade"]
            updated.append(row)

    total = 0
    for i in range(0, len(updated), BATCH):
        res = sb.table("snapshots").upsert(updated[i:i+BATCH], on_conflict="ticker,date").execute()
        total += len(res.data)
    print(f"[score] upserted {total} rows with scores")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    iso_date = to_iso(sys.argv[1] if len(sys.argv) > 1 else last_trading_day())
    print(f"[score] date={iso_date}")

    df_hist, target_rows = load_history(iso_date)
    scores = compute_scores(df_hist, iso_date)

    print(f"\nGrade distribution:\n{scores['grade'].value_counts().sort_index().to_string()}")
    print(f"\nTop 10:\n{scores.nlargest(10, 'signal_score')[['ticker','signal_score','grade']].to_string(index=False)}")
    print(f"\nBottom 5:\n{scores.nsmallest(5, 'signal_score')[['ticker','signal_score','grade']].to_string(index=False)}")
    print(f"\nScore range: {scores['signal_score'].min():.1f} – {scores['signal_score'].max():.1f}")

    write_scores(scores, target_rows, iso_date)
    print("[score] done")
