# SignalBoard — Lessons Learned

> Updated after each correction or non-obvious discovery.

---

## Phase 1

### pykrx: load_dotenv must precede the import
pykrx 1.2.x builds a KRX session at module import time, reading `KRX_ID`/`KRX_PW` from the environment. If `load_dotenv` runs after `from pykrx import stock`, the credentials are missing and every API call silently returns empty data or a LOGOUT response.
**Rule:** Always call `load_dotenv(...)` before any `from pykrx import` line.

### Supabase default query cap is 1 000 rows
A plain `.select()` with no `.range()` or explicit limit returns at most 1 000 rows. On a 200-ticker × 25-date history fetch that's only 5 dates of data — exactly the oldest 5, not the latest 25.
**Rule:** For any history query, use the two-step pattern: one anchor-ticker query to get the last N distinct dates, then one query per date (each ≤ 200 rows). Never rely on a single bulk fetch for multi-date data.

### Tailwind v4: strip globals.css of CSS custom property overrides
`create-next-app` injects `--background: #fff` and `body { background: var(--background) }` into `globals.css`. In headless (light-mode) browsers these override Tailwind's `bg-gray-950`, making white text invisible on white background.
**Rule:** After scaffolding a new Next.js project, immediately remove all `--background`/`--foreground` variable declarations and the `body { background/color }` rules from `globals.css`. Leave only the `@theme inline` font block.

### Clearing .next cache after globals.css edits
Even with the dev server running, stale Turbopack CSS can be served from the `.next/` cache after a `globals.css` change. A browser refresh or HMR trigger isn't always enough.
**Rule:** If a CSS change isn't reflected, stop the server, `rm -rf .next`, and restart.

### setuptools pin for Python 3.13 + pykrx
Python 3.13 + `setuptools ≥ 71` breaks pykrx's dependency detection (removed `pkg_resources` shim). Pin `setuptools==70.3.0` in `requirements.txt`.

### Supabase upsert batching
Upserting all 200 rows in a single HTTP/2 request causes the connection to hang. Batch in chunks of 50 with a loop.
**Rule:** Use `UPSERT_BATCH = 50` for all Supabase upsert loops.
