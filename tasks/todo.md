# SignalBoard — Phase 1 Todo

**Goal:** Daily snapshot pipeline for KOSPI 200 → Supabase → Signal Score → basic dashboard.
No alerts, no AI, no backtesting yet.

---

## 1. Project Scaffolding
- [ ] Initialize Next.js app with TypeScript + Tailwind
- [ ] Set up Supabase project (get URL + anon key)
- [ ] Set up Python virtual environment for pipeline
- [ ] Install dependencies: `pykrx`, `supabase-py`, `python-dotenv`
- [ ] Create `.env` file with Supabase credentials
- [ ] Create folder structure:
  ```
  signalboard/
  ├── tasks/
  │   ├── todo.md
  │   └── lessons.md
  ├── pipeline/
  │   ├── snapshot.py
  │   └── score.py
  ├── app/
  └── supabase/
      └── migrations/
  ```

---

## 2. Supabase Schema
- [ ] Create `snapshots` table:
  ```sql
  ticker          text
  name            text
  date            date
  close           numeric
  volume          bigint
  market_cap      bigint
  foreign_net_buy bigint
  institution_net_buy bigint
  sector          text
  signal_score    numeric
  grade           text  -- S / A / B / C / D
  ```
- [ ] Add composite primary key on `(ticker, date)`
- [ ] Enable Row-Level Security (read-only public policy for now)
- [ ] Test connection from Python with a dummy insert

---

## 3. Data Pipeline — snapshot.py
- [ ] Pull KOSPI 200 ticker list via pykrx
- [ ] For each ticker, fetch:
  - daily close price
  - volume
  - market cap
  - foreign net buy (외국인 순매수)
  - institutional net buy (기관 순매수)
- [ ] Handle missing/null tickers gracefully (some may not return data)
- [ ] Map tickers to sector (pykrx or static lookup table)
- [ ] Store raw snapshot rows in Supabase `snapshots` table
- [ ] Test with a single date first (e.g. yesterday)
- [ ] Test with full KOSPI 200 run

---

## 4. Signal Score — score.py
- [ ] For each snapshot row, calculate:
  - **Momentum (30%)**: 5-day price return vs 20-day average
  - **Volume (25%)**: today's volume vs 20-day average volume (z-score)
  - **Fund Flow (25%)**: foreign_net_buy + institution_net_buy normalized by market cap
  - **Volatility filter (20%)**: inverse of 20-day price std dev (lower volatility = higher score)
- [ ] Combine into Signal Score (0–100)
- [ ] Assign grade:
  - S: 90+
  - A: 80–89
  - B: 65–79
  - C: 50–64
  - D: below 50
- [ ] Write score + grade back to `snapshots` table
- [ ] Verify scores look reasonable (no 100s across the board, no all 0s)

---

## 5. Cron Job
- [ ] Write GitHub Actions workflow (`.github/workflows/snapshot.yml`)
- [ ] Schedule: runs daily at 16:00 KST (07:00 UTC) — after KRX market close
- [ ] Steps: checkout repo → set up Python → install deps → run `snapshot.py` → run `score.py`
- [ ] Store Supabase credentials as GitHub Actions secrets
- [ ] Test by triggering workflow manually (`workflow_dispatch`)
- [ ] Confirm rows appear in Supabase after run

---

## 6. Basic Dashboard
- [ ] Connect Next.js to Supabase (`@supabase/supabase-js`)
- [ ] Page: **Today's Radar** — top 20 stocks by Signal Score for latest date
  - Columns: rank, ticker, name, sector, close, signal_score, grade
- [ ] Page: **Grade Changes** — stocks whose grade changed vs previous trading day
  - Show: ticker, name, old grade → new grade, signal_score
- [ ] Component: **Score History Chart** — select a ticker, see signal_score over last 30 days
  - Use Chart.js (already familiar from MoneyMap)
- [ ] Loading + error states for all data fetches
- [ ] Mobile responsive layout

---

## 7. Verification Checklist (before Phase 1 is done)
- [x] Pipeline runs end-to-end without errors for at least 5 consecutive trading days
- [x] Scores are non-trivial (distribution spread across grades, not all same grade)
- [x] Dashboard loads correctly on mobile and desktop
- [x] No credentials committed to git (`.env` in `.gitignore`)
- [x] Cron job runs automatically without manual trigger

---

## Review

**Completed:** 2026-05-29

### What worked well
- **pykrx bulk API design** — 6 bulk calls (OHLCV, market cap, sectors, foreign flow, inst flow, ticker list) instead of 200 per-ticker calls kept snapshot.py fast (~10s for 200 tickers).
- **Supabase per-date query pattern** — fetching history in 25 queries × ≤200 rows each neatly dodged the 1000-row default cap; the two-step approach (anchor ticker for dates, then per-date fetch) is clean and reusable.
- **Chart.js with `ssr: false`** — dynamic import prevented canvas SSR errors cleanly; no special server-side workaround needed.
- **GitHub Actions run time** — 54s total (48s pipeline), well within the 15-minute timeout.

### What took longer than expected
- **pykrx auth** — pykrx 1.0.x silently returned empty data after KRX changed their API to require session auth. Diagnosing this (LOGOUT responses, empty DataFrames) and switching to pykrx 1.2.x with KRX credentials cost significant time. Key lesson: `load_dotenv` must run before `from pykrx import stock` since pykrx builds its KRX session at import time.
- **Supabase 1000-row cap** — the default query cap caused score.py to fetch only the oldest 5 dates instead of the latest 25, leading to a `KeyError: 'grade'` that took a full investigation cycle to trace back to the query structure.
- **Tailwind v4 dark theme** — the `create-next-app` template injected `body { background: var(--background) }` in `globals.css`, which defaulted to `#ffffff` in headless (light-mode) Playwright, making white text invisible on white background. Invisible names weren't caught until screenshots. Fix: strip all CSS custom property overrides from `globals.css`, leaving only the `@theme inline` font block. Also required clearing the stale `.next` cache for HMR to pick up the change.

### What would you do differently
- Test screenshot the dashboard immediately after first boot — invisible text is a fast catch with one screenshot.
- Add a `LIMIT` override or explicit `.range()` call to every Supabase history query to make the 1000-row cap visible at the callsite.
- Pin `setuptools<71` in `requirements.txt` from day one (Python 3.13 + setuptools ≥ 71 breaks `pkg_resources` for pykrx's dependency detection).

### Is the Signal Score producing interesting results?
Early data (one trading day) shows the top 20 dominated by 전기·전자 (electrical/electronics) and 건설 (construction) sectors with A grades (scores 80–88). Grade D stocks not yet visible in the top-20 view but present in the full dataset. Score distribution looks healthy — not all clustering at one grade. Need 5+ days of consecutive runs to validate momentum and volatility factors properly.

### Ready for Phase 2 (alerts)?
**Y** — pipeline, scoring, and dashboard are all verified end-to-end. Phase 2 (Telegram alerts on grade changes) can start next session.
