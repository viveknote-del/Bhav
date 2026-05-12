# Bhav — Quickstart

> Indian-stock breakout screener. Scans NSE/BSE daily, ranks breakouts,
> writes AI commentary. Single-user, runs locally.

---

## 0. What you'll have running at the end

Five things on your machine, each in its own window:

```
┌─ Docker Desktop ─────────────────────────────────────────┐
│  ai-starter-postgres-1   port 5434  (DB)                 │
│  ai-starter-redis-1      port 6381  (queue + cache)      │
└──────────────────────────────────────────────────────────┘
┌─ Terminal 1 ─────────────────────────────────────────────┐
│  uvicorn main:app    port 8765      (REST API)           │
└──────────────────────────────────────────────────────────┘
┌─ Terminal 2 ─────────────────────────────────────────────┐
│  arq workers.WorkerSettings        (scans + commentary)  │
└──────────────────────────────────────────────────────────┘
┌─ Terminal 3 ─────────────────────────────────────────────┐
│  pnpm dev            port 3000      (Next.js dashboard)  │
└──────────────────────────────────────────────────────────┘
```

Open `http://localhost:3000` in a browser when all four are up.

---

## 1. Prerequisites

Install these once. **Skip anything you already have.**

| Tool | Why | Where |
|---|---|---|
| **Docker Desktop** | Runs Postgres + Redis | https://docker.com/products/docker-desktop |
| **Python 3.12 or 3.13** | Backend runtime. 3.14 also works after a dep bump (already in `requirements.txt`). | https://python.org/downloads |
| **Node.js 20+** | Frontend runtime | https://nodejs.org |
| **pnpm** | Frontend package manager | After Node is installed: `npm install -g pnpm` |
| **Git** | Code | https://git-scm.com/downloads |

Verify each:
```powershell
docker --version
python --version
node --version
pnpm --version
git --version
```

If any command says "not recognized", install that tool before continuing.

---

## 2. Clone the repo

```powershell
cd %USERPROFILE%\Documents          # or wherever you keep code
git clone https://github.com/viveknote-del/Bhav.git
cd Bhav
```

If you already have it, `git pull` to get the latest.

---

## 3. Configure `.env`

```powershell
copy .env.example .env
```

Open `.env` in any editor (Notepad is fine) and set **at minimum** this one line:

```
MARKET_DATA_PROVIDER=yahoo_direct
```

`yahoo_direct` needs no API key and isn't rate-limited like the yfinance library.

**Optional** (commented out by default — uncomment + fill in to enable):

```
ANTHROPIC_API_KEY=sk-ant-...        # AI commentary on each breakout + EOD digest
NEWSAPI_KEY=...                      # News headlines per breakout (free at newsapi.org)
TELEGRAM_BOT_TOKEN=...               # Push alerts on score≥80 breakouts
TELEGRAM_CHAT_ID=...
```

Everything works without these — you just won't get AI commentary, news, or alerts.

---

## 4. Start Docker (one-time per boot)

```powershell
docker compose up -d
```

Wait ~10 seconds, then verify both containers are healthy:

```powershell
docker ps
```

You should see `ai-starter-postgres-1` and `ai-starter-redis-1` both `Up (healthy)`.

---

## 5. Apply database migrations (one-time per fresh DB)

```powershell
make migrate
```

If you don't have `make` on Windows, run each migration manually:

```powershell
docker exec -i ai-starter-postgres-1 psql -U postgres -d bhav < packages\database\migrations\0000_initial.sql
docker exec -i ai-starter-postgres-1 psql -U postgres -d bhav < packages\database\migrations\0001_job_tracking.sql
docker exec -i ai-starter-postgres-1 psql -U postgres -d bhav < packages\database\migrations\0002_news_cache.sql
docker exec -i ai-starter-postgres-1 psql -U postgres -d bhav < packages\database\migrations\0003_alerted_at.sql
```

You should see `CREATE TABLE` lines for each.

---

## 6. Set up backend Python environment (one-time)

```powershell
cd services\api
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install --only-binary=":all:" -r requirements.txt
cd ..\..
```

The `--only-binary=":all:"` flag tells pip to use prebuilt wheels — important on
Python 3.14 where `pydantic-core` and `asyncpg` won't compile from source on
Windows without a Rust toolchain.

This takes ~2 minutes on first run.

---

## 7. Seed the universe (one-time per fresh DB)

```powershell
make seed
```

Or manually:
```powershell
cd services\api
.venv\Scripts\activate
python -m scripts.seed
cd ..\..
```

You should see `Inserted: 50  Updated: 0  Failed: 0` — that's NIFTY 50 in your DB.

---

## 8. Set up frontend (one-time)

```powershell
cd apps\web
pnpm install
cd ..\..
```

Takes ~30 seconds on first run.

---

## 9. Run it — three terminals, leave each open

### Terminal 1 — API
```powershell
cd services\api
.venv\Scripts\activate
uvicorn main:app --port 8765
```
You should see `Uvicorn running on http://127.0.0.1:8765`. Leave this running.

> **Why port 8765?** Many machines have something else on port 8000.
> If you know yours is free, use 8000 instead.

### Terminal 2 — Worker
```powershell
cd services\api
.venv\Scripts\activate
arq workers.WorkerSettings
```
You should see `Starting worker for 5 functions: scan_eod, commentary_for_scan, ...`. Leave this running.

### Terminal 3 — Frontend
```powershell
cd apps\web
pnpm dev
```
You should see `Local: http://localhost:3000`. Leave this running.

---

## 10. First scan

Open a **fourth** terminal (the other three are busy serving):

```powershell
curl -X POST http://localhost:8765/v1/scans -H "Content-Type: application/json" -d "{\"scan_type\":\"EOD\"}"
```

You'll get a JSON response with `"status": "RUNNING"`. The worker picks up the
job; takes ~30-60 seconds for NIFTY 50.

---

## 11. Open the dashboard

http://localhost:3000

**Home page** — today's breakouts ranked by composite score. Click any to see:
- 180-day candle chart with the breakout level marked
- Indicator stats (price, volume ratio, score)
- Claude commentary (if `ANTHROPIC_API_KEY` set)
- News links (if `NEWSAPI_KEY` set)
- Add-to-watchlist button

**Other pages:**
- `/scans` — scan history, manually trigger new scans
- `/instruments` — NIFTY 50 browser
- `/watchlist` — personal symbol list
- `/backtests` — replay detectors over historical bars (needs cache built up by a few scans first)

---

## Daily usage (after first-time setup)

You can leave Docker, the API, and the worker running indefinitely. They use
minimal resources when idle. The cron in the worker auto-triggers a scan
every weekday at 15:35 IST (10:05 UTC).

To start a scan manually any time:
- Click "Run scan now" on the `/scans` page, or
- `curl -X POST http://localhost:8765/v1/scans`

To stop everything:
```powershell
docker compose down            # stops DB and Redis
# Ctrl+C in each of the API / worker / frontend terminals
```

---

## Troubleshooting

**"Connection refused" on http://localhost:3000**
The frontend (Terminal 3) isn't running. Restart it.

**"Connection refused" on http://localhost:8765**
The API (Terminal 1) isn't running. Restart it.

**Breakouts page shows "No scans yet"**
Run a scan (step 10), wait for it to finish.

**Scan completes with 0 breakouts**
Could be a quiet market day — that's normal. If it happens for several days
in a row and you see `yahoo_direct.fetch_failed` in worker logs, your IP
might be blocked by Yahoo. Switch to a different network or swap
`MARKET_DATA_PROVIDER` (see `.env.example` for alternatives).

**Worker logs "ANTHROPIC_API_KEY is not set"**
Expected if you haven't set it. Commentary is opt-in.

**Port already in use**
Something else is on 5434/6381/8765/3000. Either stop that thing, or change
the port in `docker-compose.yml` / `uvicorn --port` / `.env`.

**`pnpm` is not recognized**
Install Node.js, then `npm install -g pnpm`.

---

## What it costs

| Component | Cost |
|---|---|
| Yahoo direct provider | Free, no key |
| NewsAPI free tier | Free, 100 req/day (we cache per symbol/day) |
| Claude commentary (Sonnet 4.6) | ~$0.03 per scan with prompt caching |
| Telegram alerts | Free |
| Hardware | Your machine + ~200 MB RAM for the whole stack |

If you don't set `ANTHROPIC_API_KEY`, total cost is **zero**.
