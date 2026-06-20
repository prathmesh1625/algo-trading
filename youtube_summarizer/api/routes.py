from pathlib import Path

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from youtube_summarizer.api.schemas import AnalyzeRequest, AnalyzeResponse
from youtube_summarizer.core.url_parser import extract_video_id, canonical_url
from youtube_summarizer.core.metadata import fetch_metadata
from youtube_summarizer.core.transcript import fetch_transcript, chunk_transcript, sample_transcript
from youtube_summarizer.config import (
    LLM_PROVIDER, MAX_TRANSCRIPT_CHARS,
    GROQ_MAX_TRANSCRIPT_CHARS, CLAUDE_MAX_TRANSCRIPT_CHARS,
)
from youtube_summarizer.core.analyzer import analyze_chunks
from youtube_summarizer.report.builder import build_report
from youtube_summarizer.report.exporter import to_markdown, to_pdf
from youtube_summarizer.db.store import (
    save_analysis,
    get_analysis,
    get_by_video_id,
    get_history,
    delete_analysis,
)

_BASE = Path(__file__).parent.parent
templates = Jinja2Templates(directory=str(_BASE / "templates"))

router = APIRouter()


# ─── Pages ───────────────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    recent = get_history(limit=5)
    return templates.TemplateResponse(request, "index.html", {"recent": recent})


@router.get("/history", response_class=HTMLResponse)
async def history_page(request: Request):
    items = get_history(limit=100)
    return templates.TemplateResponse(request, "history.html", {"items": items})


@router.get("/report/{aid}", response_class=HTMLResponse)
async def report_page(request: Request, aid: str):
    entry = get_analysis(aid)
    if not entry:
        raise HTTPException(status_code=404, detail="Report not found")
    return templates.TemplateResponse(
        request,
        "report.html",
        {"entry": entry, "report": entry["report"]},
    )


# ─── API ─────────────────────────────────────────────────────────────────────

@router.post("/api/analyze")
async def analyze(body: AnalyzeRequest):
    url = body.url.strip()

    video_id = extract_video_id(url)
    if not video_id:
        raise HTTPException(status_code=400, detail="Invalid YouTube URL. Please check the link and try again.")

    # Return cached result if this video was already analyzed
    cached = get_by_video_id(video_id)
    if cached:
        return {"id": cached["id"], "title": cached["title"], "channel": cached["channel"], "cached": True}

    canonical = canonical_url(video_id)

    # Fetch metadata
    try:
        metadata = await fetch_metadata(canonical)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Could not fetch video metadata: {e}")

    # Fetch transcript
    try:
        entries = await fetch_transcript(video_id)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Could not fetch transcript: {e}")

    if not entries:
        raise HTTPException(status_code=422, detail="The transcript for this video is empty.")

    # Sample transcript to fit within LLM token budget, then chunk
    char_limit = {
        "groq": GROQ_MAX_TRANSCRIPT_CHARS,
        "claude": CLAUDE_MAX_TRANSCRIPT_CHARS,
    }.get(LLM_PROVIDER, MAX_TRANSCRIPT_CHARS)
    entries = sample_transcript(entries, max_chars=char_limit)
    chunks = chunk_transcript(entries)
    try:
        analysis = await analyze_chunks(metadata["title"], metadata["channel"], chunks)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"AI analysis failed: {e}")

    # Build and save report
    report = build_report(metadata, analysis, canonical)
    aid = save_analysis(
        video_id=video_id,
        url=canonical,
        title=metadata["title"],
        channel=metadata["channel"],
        duration=metadata.get("duration", 0),
        thumbnail=metadata.get("thumbnail", ""),
        report=report,
    )

    return {"id": aid, "title": metadata["title"], "channel": metadata["channel"], "cached": False}


@router.get("/api/history")
async def api_history():
    return get_history(limit=100)


@router.delete("/api/report/{aid}")
async def delete_report(aid: str):
    if not delete_analysis(aid):
        raise HTTPException(status_code=404, detail="Report not found")
    return {"deleted": True}


# ─── Downloads ───────────────────────────────────────────────────────────────

@router.get("/download/{aid}/markdown")
async def download_markdown(aid: str):
    entry = get_analysis(aid)
    if not entry:
        raise HTTPException(status_code=404, detail="Report not found")
    md = to_markdown(entry["report"])
    safe_title = "".join(c if c.isalnum() or c in " _-" else "_" for c in entry["title"])[:60]
    filename = f"report_{safe_title}.md"
    return StreamingResponse(
        iter([md.encode("utf-8")]),
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/download/{aid}/pdf")
async def download_pdf(aid: str):
    entry = get_analysis(aid)
    if not entry:
        raise HTTPException(status_code=404, detail="Report not found")
    pdf_bytes = to_pdf(entry["report"])
    safe_title = "".join(c if c.isalnum() or c in " _-" else "_" for c in entry["title"])[:60]
    filename = f"report_{safe_title}.pdf"
    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
