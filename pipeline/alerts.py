"""
Daily Telegram alert digest for SignalBoard.

Compares today's grades and radar positions against the previous trading day,
then sends a single summary message to a Telegram chat.

Sections (omitted when empty):
  🟢 Upgrades        — grade improved (e.g. C → A)
  🔴 Downgrades      — grade fell
  🎯 New Radar       — entered today's top-20 by signal_score
  📤 Exited Radar    — dropped out of top-20
  Quiet day          — brief confirmation when nothing changed

Usage:
    python pipeline/alerts.py [YYYYMMDD | YYYY-MM-DD]   # defaults to last weekday
"""

import os
import sys
from datetime import date, timedelta

import httpx
from dotenv import load_dotenv
from supabase import create_client

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

sb = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_SERVICE_ROLE_KEY"],
)

GRADE_ORDER: dict[str, int] = {"S": 5, "A": 4, "B": 3, "C": 2, "D": 1}
RADAR_SIZE  = 20
MAX_SECTION = 10   # truncate long sections in the message


def last_trading_day() -> str:
    d = date.today() - timedelta(days=1)
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d.strftime("%Y-%m-%d")


def to_iso(s: str) -> str:
    return f"{s[:4]}-{s[4:6]}-{s[6:]}" if len(s) == 8 else s


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def get_last_two_dates(anchor: str = "005930") -> tuple[str, str] | None:
    """Return (today, yesterday) ISO dates, or None if <2 dates exist."""
    resp = (
        sb.table("snapshots")
        .select("date")
        .eq("ticker", anchor)
        .order("date", desc=True)
        .limit(2)
        .execute()
    )
    if not resp.data or len(resp.data) < 2:
        return None
    return resp.data[0]["date"], resp.data[1]["date"]


def _fetch_grades(iso_date: str) -> list[dict]:
    """Full grade snapshot for a single date."""
    resp = (
        sb.table("snapshots")
        .select("ticker, name, signal_score, grade")
        .eq("date", iso_date)
        .not_.is_("grade", "null")
        .execute()
    )
    return resp.data or []


def _fetch_radar(iso_date: str) -> list[dict]:
    """Top RADAR_SIZE tickers by signal_score for a date."""
    resp = (
        sb.table("snapshots")
        .select("ticker, name, signal_score, grade")
        .eq("date", iso_date)
        .not_.is_("signal_score", "null")
        .order("signal_score", desc=True)
        .limit(RADAR_SIZE)
        .execute()
    )
    return resp.data or []


# ---------------------------------------------------------------------------
# Change detection
# ---------------------------------------------------------------------------

def get_grade_changes(
    today: str, yesterday: str
) -> tuple[list[dict], list[dict]]:
    """Return (upgrades, downgrades) sorted by signal_score descending."""
    today_rows = _fetch_grades(today)
    prev_map   = {r["ticker"]: r["grade"] for r in _fetch_grades(yesterday)}

    upgrades:   list[dict] = []
    downgrades: list[dict] = []

    for r in today_rows:
        old = prev_map.get(r["ticker"])
        if old is None or old == r["grade"]:
            continue
        old_rank = GRADE_ORDER.get(old, 0)
        new_rank = GRADE_ORDER.get(r["grade"] or "", 0)
        change = {**r, "old_grade": old}
        if new_rank > old_rank:
            upgrades.append(change)
        else:
            downgrades.append(change)

    key = lambda x: x["signal_score"] or 0
    return sorted(upgrades, key=key, reverse=True), sorted(downgrades, key=key, reverse=True)


def get_radar_changes(
    today: str, yesterday: str
) -> tuple[list[dict], list[dict]]:
    """Return (new_entries, exits)."""
    today_radar     = _fetch_radar(today)
    yesterday_radar = _fetch_radar(yesterday)

    today_set     = {r["ticker"] for r in today_radar}
    yesterday_set = {r["ticker"] for r in yesterday_radar}

    today_map = {r["ticker"]: r for r in today_radar}
    prev_map  = {r["ticker"]: r for r in yesterday_radar}

    new_entries = [today_map[t] for t in today_set - yesterday_set]
    exits       = [prev_map[t]  for t in yesterday_set - today_set]

    key = lambda x: x["signal_score"] or 0
    return sorted(new_entries, key=key, reverse=True), sorted(exits, key=key, reverse=True)


# ---------------------------------------------------------------------------
# Message formatting
# ---------------------------------------------------------------------------

def _fmt_score(score) -> str:
    return f"{float(score):.1f}" if score is not None else "—"


def _section(header: str, lines: list[str]) -> str:
    return f"{header}\n" + "\n".join(lines)


def format_message(
    iso_date:   str,
    upgrades:   list[dict],
    downgrades: list[dict],
    new_entries: list[dict],
    exits:      list[dict],
) -> str:
    parts = [f"📊 *SignalBoard — {iso_date}*"]

    def truncated(rows: list[dict], n: int) -> tuple[list[dict], int]:
        return rows[:n], max(0, len(rows) - n)

    if upgrades:
        rows, extra = truncated(upgrades, MAX_SECTION)
        lines = [
            f"▲ {r['name']} ({r['ticker']}) {r['old_grade']}→{r['grade']}  {_fmt_score(r['signal_score'])}"
            for r in rows
        ]
        if extra:
            lines.append(f"…and {extra} more")
        parts.append(_section(f"🟢 *Upgrades ({len(upgrades)})*", lines))

    if downgrades:
        rows, extra = truncated(downgrades, MAX_SECTION)
        lines = [
            f"▼ {r['name']} ({r['ticker']}) {r['old_grade']}→{r['grade']}  {_fmt_score(r['signal_score'])}"
            for r in rows
        ]
        if extra:
            lines.append(f"…and {extra} more")
        parts.append(_section(f"🔴 *Downgrades ({len(downgrades)})*", lines))

    if new_entries:
        rows, extra = truncated(new_entries, MAX_SECTION)
        lines = [
            f"• {r['name']} ({r['ticker']}) {r['grade']}  {_fmt_score(r['signal_score'])}"
            for r in rows
        ]
        if extra:
            lines.append(f"…and {extra} more")
        parts.append(_section(f"🎯 *New Radar Entries ({len(new_entries)})*", lines))

    if exits:
        rows, extra = truncated(exits, MAX_SECTION)
        lines = [f"• {r['name']} ({r['ticker']})" for r in rows]
        if extra:
            lines.append(f"…and {extra} more")
        parts.append(_section(f"📤 *Exited Radar ({len(exits)})*", lines))

    if len(parts) == 1:
        # Nothing changed — quiet day
        return f"_SignalBoard {iso_date} — pipeline ran, no changes today_"

    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Telegram delivery
# ---------------------------------------------------------------------------

def send_telegram(text: str, token: str, chat_id: str) -> None:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    resp = httpx.post(
        url,
        json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
        timeout=10,
    )
    resp.raise_for_status()
    print(f"[alerts] Telegram message sent (chat_id={chat_id})")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    iso_date = to_iso(sys.argv[1] if len(sys.argv) > 1 else last_trading_day())
    print(f"[alerts] date={iso_date}")

    token   = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]

    dates = get_last_two_dates()
    if dates is None:
        msg = f"_SignalBoard {iso_date} — first run, no previous day to compare_"
        print(f"[alerts] no previous date found, sending first-run notice")
    else:
        today, yesterday = dates
        print(f"  comparing {yesterday} → {today}")

        upgrades, downgrades = get_grade_changes(today, yesterday)
        new_entries, exits   = get_radar_changes(today, yesterday)

        print(f"  upgrades={len(upgrades)} downgrades={len(downgrades)} "
              f"new_radar={len(new_entries)} exits={len(exits)}")

        msg = format_message(today, upgrades, downgrades, new_entries, exits)

    print("\n--- message preview ---")
    print(msg)
    print("--- end preview ---\n")

    send_telegram(msg, token, chat_id)
    print("[alerts] done")
