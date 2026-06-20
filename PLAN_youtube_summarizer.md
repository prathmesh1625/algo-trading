# Plan — YouTube Video Summarizer (Module 1 of the Algo-Trading Suite)

> Status: **Planning only. No code yet.**
> This is the first module of a larger algo-trading project. It is built as a
> standalone, self-contained component so the rest of the project can grow
> around it later without rework.

---

## 1. Goal

A tool where a user **pastes a YouTube video link** and gets back a
**detailed report** of the video. For a finance/trading channel the report
must specifically surface:

- A clean overall summary of what the video is about.
- **Key concepts** discussed (e.g. "RSI divergence", "position sizing", "Fed rate cut").
- **Stocks / tickers mentioned** (e.g. AAPL, TSLA, RELIANCE, NIFTY) — with the
  context in which each was mentioned (bullish/bearish/neutral, target price if any).
- Timestamps for important points (so the user can jump back to the source).

---

## 2. Scope for "today" (v1)

**In scope**
- Single video at a time, link pasted manually.
- Works on videos that have captions/transcript available (the common case).
- Generate a structured report on screen + downloadable (Markdown / PDF).
- Basic, clean UI.

**Out of scope (for now, noted for later)**
- Bulk / playlist processing.
- User accounts / login (history is saved, but not per-user — single shared local history for v1).
- Videos with NO captions (would need audio download + speech-to-text — heavier, see §8).
- Live integration with the trading engine (later module).
- Real-time price lookup for mentioned tickers (later enhancement, see §8).

---

## 3. How it works (high-level flow)

```
User pastes URL
      │
      ▼
[1] Validate URL  ──►  extract video ID
      │
      ▼
[2] Fetch metadata (title, channel, duration, description)
      │
      ▼
[3] Fetch transcript (captions) with timestamps
      │
      ▼
[4] Pre-process transcript (clean, chunk if very long)
      │
      ▼
[5] LLM analysis  ──►  summary + key concepts + tickers + sentiment + timestamps
      │
      ▼
[6] Post-process / validate tickers (optional symbol check)
      │
      ▼
[7] Render report in UI  +  allow download (MD / PDF)
```

---

## 4. Recommended tech stack

Chosen to match an algo-trading project (Python-centric) and to stay simple.

| Layer | Choice | Why |
|-------|--------|-----|
| Language | **Python 3.11+** | Same language the rest of the algo project will use. |
| Backend | **FastAPI** + Uvicorn | Real website with a proper HTTP API. Clean separation of frontend/backend; the same API can later be consumed by the trading engine. |
| Frontend | **HTML + CSS + vanilla JS** (Jinja2 templates served by FastAPI) | A genuine website, no Streamlit. Single-page form: paste link → see report → download / view history. Can swap to React later if it grows. |
| Transcript | **`youtube-transcript-api`** | Pulls captions + timestamps directly, no API key, no video download. Prefers Hindi/English/auto captions (common on Indian finance channels). |
| Metadata | **`yt-dlp`** (metadata-only mode) | Reliable title/channel/duration without downloading the video. |
| LLM analysis | **OpenAI API (`openai` SDK)** | User-chosen. Structured extraction via JSON mode / structured outputs. Model: `gpt-4o` (quality) or `gpt-4o-mini` (cheaper/faster first pass). User provides the API key. |
| Ticker validation | **local NSE/BSE symbol list** + optional `yfinance` (`.NS`/`.BO` suffixes) | Validate against Indian listed symbols; cuts false positives. |
| History storage | **SQLite** (via SQLAlchemy or `sqlite3`) | Lightweight, file-based, zero setup. Stores every analyzed video + its report JSON; re-opening a past link is instant. |
| Report export | `markdown` + `weasyprint`/`reportlab` for PDF | Downloadable report (both Markdown and PDF). |
| Config / secrets | `.env` via `python-dotenv` | Keep the OpenAI API key out of code. |

> Note: An **OpenAI API key** is required (user will provide it). Stored in `.env`, never committed.

---

## 5. Proposed project structure

```
algo-trading/
├── PLAN_youtube_summarizer.md      ← this file
├── .env.example                    ← template for API keys (no secrets)
├── .gitignore
├── requirements.txt
├── README.md
└── youtube_summarizer/
    ├── __init__.py
    ├── main.py                     ← FastAPI app: routes + startup
    ├── config.py                   ← loads env vars (OpenAI key), model names
    ├── api/
    │   ├── routes.py               ← POST /analyze, GET /history, GET /report/{id}, GET /download/{id}
    │   └── schemas.py              ← Pydantic request/response models
    ├── core/
    │   ├── url_parser.py           ← validate URL, extract video ID
    │   ├── metadata.py             ← title/channel/duration via yt-dlp
    │   ├── transcript.py           ← fetch + clean + chunk transcript
    │   ├── analyzer.py             ← OpenAI calls, prompt building, JSON parsing
    │   └── tickers.py              ← NSE/BSE ticker extraction + validation
    ├── report/
    │   ├── builder.py              ← assemble report data object
    │   └── exporter.py             ← render to Markdown / PDF
    ├── db/
    │   ├── models.py               ← SQLite tables (Video, Report)
    │   └── store.py                ← save/fetch history
    ├── data/
    │   └── nse_bse_symbols.csv     ← Indian symbol master list (for validation)
    ├── templates/                  ← Jinja2 HTML (index, report, history)
    │   ├── index.html
    │   ├── report.html
    │   └── history.html
    └── static/                     ← CSS + JS
        ├── style.css
        └── app.js
```

This keeps each responsibility in its own file so the algo-trading modules
added later can reuse `core/` pieces (e.g. the ticker extractor) and the
FastAPI endpoints independently of the website UI.

---

## 6. The report — what it contains

The generated report should have these sections:

1. **Header** — video title, channel, duration, link, date analyzed.
2. **TL;DR** — 3–5 sentence overview.
3. **Detailed summary** — section-by-section, with timestamps.
4. **Key concepts** — bulleted list, each with a one-line explanation.
5. **Stocks / tickers mentioned** — a table (Indian market focus, NSE/BSE):

   | Symbol (NSE/BSE) | Company name | Context | Sentiment | Price target (if any) | Timestamp |
   |------------------|--------------|---------|-----------|----------------------|-----------|

   Also captures index mentions (NIFTY, BANKNIFTY, SENSEX) and sectors.

6. **Notable quotes / claims** — direct lines worth flagging.
7. **Disclaimer** — "Not financial advice; auto-generated from transcript."

The LLM step will be asked to return this as **structured JSON**, which we then
render — this avoids messy free-text parsing and makes the data reusable by
later trading modules.

---

## 7. Build phases (order of work)

- **Phase 0 — Setup**: repo scaffolding, `requirements.txt`, `.env.example`, virtualenv, FastAPI "hello world".
- **Phase 1 — Input + transcript**: URL parsing, metadata fetch, transcript fetch. Verify end-to-end on a real Indian finance video (print raw transcript).
- **Phase 2 — LLM analysis**: prompt design, JSON schema, call OpenAI (structured output), parse result into data classes.
- **Phase 3 — Ticker handling**: load NSE/BSE symbol list, clean/validate extracted symbols, attach sentiment & context.
- **Phase 4 — Report rendering**: build the Markdown report, add PDF export (both download options).
- **Phase 5 — History (SQLite)**: save each analyzed video + report JSON; fetch past reports by ID; skip re-analysis if already cached.
- **Phase 6 — Website UI**: FastAPI routes + Jinja2/HTML/CSS/JS — home page with link input + "Analyze", report page (on-screen view), download buttons (MD/PDF), history page.
- **Phase 7 — Polish**: error handling (no captions, invalid link, very long videos), loading states, basic input guards.

Each phase is independently testable before moving on.

---

## 8. Known challenges & how we'll handle them

- **No captions on a video** → v1 shows a clear message. Later: download audio with
  `yt-dlp` + transcribe (Whisper / a speech-to-text API). Flagged for v2.
- **Very long videos** → transcript may exceed the model context. Strategy: chunk
  the transcript, summarize chunks, then summarize the summaries (map-reduce).
- **False-positive tickers** → words mistaken for symbols. Mitigate with a known
  symbol list + asking the LLM to only include tickers it is confident about.
- **API cost** → use a cheaper model (Haiku) for first pass; optionally upgrade to
  Opus for the final report. Cache results per video ID.
- **YouTube rate limits / blocking** → keep requests light (metadata + captions only,
  no full download in v1).

---

## 9. Future hooks (so this fits the bigger algo project)

- Output report JSON can feed a **watchlist** of mentioned tickers.
- Add **live price lookup** for each mentioned ticker (yfinance / broker API).
- Add **sentiment aggregation** across many videos/channels over time.
- Wire the extracted signals into the trading engine modules added later.
- Optional database to store every analyzed video + extracted signals.

---

## 10. Decisions (locked in)

1. **UI** — ✅ Real **website** (FastAPI + HTML/CSS/JS). No Streamlit.
2. **LLM** — ✅ **OpenAI API**. User provides the API key (stored in `.env`).
3. **Market** — ✅ **Indian (NSE/BSE)**; indices NIFTY/BANKNIFTY/SENSEX included.
4. **Output** — ✅ **Both** on-screen view **and** downloadable (Markdown + PDF).
5. **Storage** — ✅ **Save history** in SQLite (single shared local history for v1).

Remaining minor choice (can default): OpenAI model — `gpt-4o` (better) vs
`gpt-4o-mini` (cheaper). Default: start with `gpt-4o-mini`, allow switching in config.

---

### Next step
Decisions are locked. When you say go, I'll start with **Phase 0 + Phase 1**
(scaffold the FastAPI project, then get URL → metadata → transcript working
end-to-end on a real Indian finance video). You can hand over the OpenAI API
key when we reach Phase 2.
