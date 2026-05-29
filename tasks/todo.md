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
- [ ] Pipeline runs end-to-end without errors for at least 5 consecutive trading days
- [ ] Scores are non-trivial (distribution spread across grades, not all same grade)
- [ ] Dashboard loads correctly on mobile and desktop
- [ ] No credentials committed to git (`.env` in `.gitignore`)
- [ ] Cron job runs automatically without manual trigger

---

## Review
> Fill this in after Phase 1 is complete.

- What worked well?
- What took longer than expected?
- What would you do differently?
- Is the Signal Score producing interesting results?
- Ready for Phase 2 (alerts)? Y/N
