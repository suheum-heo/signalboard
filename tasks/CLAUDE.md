# SignalBoard — Claude Code Instructions

## Project Overview

**SignalBoard** is a Korean equity signal platform built by Suheum.

It snapshots KOSPI 200 stock data daily, calculates a proprietary Signal Score, detects grade changes, sends Telegram alerts, and backtests whether the signals actually predicted gains.

### Stack
- **Frontend**: Next.js + TypeScript + Tailwind
- **Database**: Supabase (Postgres + Row-Level Security)
- **Cron**: Vercel Cron or GitHub Actions
- **Data pipeline**: Python (pykrx, OpenDART API)
- **Notifications**: Telegram Bot
- **AI memos**: Claude API (Phase 4 only)
- **Deployment**: Vercel

### Data Sources
- **pykrx** — price, volume, foreign/institutional flow for KOSPI 200
- **OpenDART API** — financial statements, disclosures, filings
- **Bank of Korea ECOS / FRED** — macro indicators
- **yfinance** — S&P 500, NASDAQ, VIX as benchmark/context

---

## Build Phases

### Phase 1 — Data Foundation (current)
- Daily snapshot pipeline for KOSPI 200
- Supabase storage: `ticker, name, date, close, volume, market_cap, foreign_net_buy, institution_net_buy, sector`
- Signal Score formula (momentum 30% + volume 25% + fund flow 25% + volatility filter 20%)
- Grade system: S (90+), A (80–89), B (65–79), C (50–64), D (below 50)
- Basic dashboard: today's top stocks, grade changes, score history

### Phase 2 — Alerts
- Detect grade changes (e.g. C → B) and radar entries
- Telegram bot: one daily message after market close (KST 15:30) summarizing all changes
- Threshold alerts for macro indicators (sector-wide institutional outflow spikes)

### Phase 3 — Backtesting
- Track returns after 5, 20, 60 trading days from radar entry
- Benchmark-adjusted (vs KOSPI/KOSDAQ)
- Answer: does the Signal Score actually predict gains?

### Phase 4 — AI Memos
- Claude API explains why a stock entered the radar
- Bull case / bear case / risks / disclosure summary
- Only built after Phase 3 validates the pipeline

---

## Workflow Rules

### Planning
- Enter plan mode for ANY non-trivial task (3+ steps or architectural decisions)
- Write the plan to `tasks/todo.md` with checkable items before touching code
- Check in with Suheum before starting implementation
- If something goes sideways mid-task, STOP and re-plan — don't keep pushing
- Write detailed specs upfront to reduce ambiguity

### Subagents
- Use subagents liberally to keep the main context window clean
- Offload research, exploration, and parallel analysis to subagents
- For complex problems, use multiple focused subagents (one task per subagent)

### Self-Improvement
- After ANY correction from Suheum: update `tasks/lessons.md` with the pattern
- Write rules that prevent the same mistake from recurring
- Review `tasks/lessons.md` at the start of each session

### Verification
- Never mark a task complete without proving it works
- Run tests, check logs, demonstrate correctness
- Ask: "Would a staff engineer approve this?"

### Code Quality
- **Simplicity first** — make every change as simple as possible
- **Minimal impact** — only touch what's necessary; avoid introducing bugs
- **No laziness** — find root causes, no temporary fixes
- For non-trivial changes, pause and ask: "Is there a more elegant solution?"
- Skip over-engineering for simple, obvious fixes

### Bug Fixing
- When given a bug report: just fix it
- Point at logs, errors, failing tests — then resolve them
- No hand-holding required from Suheum

---

## Task Management

1. **Plan first** — write plan to `tasks/todo.md`
2. **Check in** — confirm with Suheum before building
3. **Track progress** — mark items complete as you go
4. **Explain changes** — high-level summary at each step
5. **Document results** — add review section to `tasks/todo.md`
6. **Capture lessons** — update `tasks/lessons.md` after any correction

---

## Important Constraints

- **Do NOT scrape FRoGie or any site whose ToS prohibits it**
- **Do NOT use real money-based logic** until Phase 3 backtest validates the Signal Score
- Signal alerts are sent once daily (post market close), not intraday
- This is a swing trade tool — holding days to weeks, not minutes
- The Signal Score weights are a starting hypothesis; treat them as unvalidated until backtested
- Fundamentals (OpenDART) are Phase 2+ only — skip for Phase 1 MVP

---

## File Structure (planned)

```
signalboard/
├── tasks/
│   ├── todo.md
│   └── lessons.md
├── pipeline/          # Python data pipeline
│   ├── snapshot.py    # daily pykrx pull + score calc
│   └── alerts.py      # diff + Telegram dispatch
├── app/               # Next.js frontend
│   ├── dashboard/
│   ├── screener/
│   └── backtest/
├── supabase/
│   └── migrations/
└── CLAUDE.md
```
