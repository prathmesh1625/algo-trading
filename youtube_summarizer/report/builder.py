from datetime import datetime

from youtube_summarizer.core.tickers import enrich_tickers


def _fmt_duration(seconds: int | None) -> str:
    if not seconds:
        return "Unknown"
    s = int(seconds)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    if h:
        return f"{h}h {m:02d}m {sec:02d}s"
    return f"{m}m {sec:02d}s"


def _clean_ts(ts: str) -> str:
    """Strip brackets the LLM copies from transcript markers, e.g. '[5:27]' → '5:27'."""
    return str(ts or "").strip().strip("[]")


def _ts_to_secs(ts: str) -> int:
    """Convert 'M:SS' or 'H:MM:SS' to total seconds for sorting."""
    parts = _clean_ts(ts).split(":")
    try:
        parts = [int(p) for p in parts]
    except ValueError:
        return 0
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    if len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    return 0


def build_report(metadata: dict, analysis: dict, url: str) -> dict:
    tickers = enrich_tickers(analysis.get("tickers_mentioned") or [])

    # Clean timestamps on tickers
    for t in tickers:
        if t.get("timestamp"):
            t["timestamp"] = _clean_ts(t["timestamp"])

    # Clean and sort summary sections chronologically
    sections = []
    for s in (analysis.get("summary_sections") or []):
        sections.append({**s, "timestamp": _clean_ts(s.get("timestamp", ""))})
    sections.sort(key=lambda s: _ts_to_secs(s["timestamp"]))

    return {
        "url": url,
        "meta": {
            "title": metadata.get("title", ""),
            "channel": metadata.get("channel", ""),
            "duration": metadata.get("duration", 0),
            "duration_fmt": _fmt_duration(metadata.get("duration")),
            "thumbnail": metadata.get("thumbnail", ""),
            "upload_date": metadata.get("upload_date", ""),
            "view_count": metadata.get("view_count", 0),
        },
        "tldr": analysis.get("tldr", ""),
        "market_outlook": analysis.get("market_outlook", "neutral"),
        "summary_sections": sections,
        "key_concepts": analysis.get("key_concepts") or [],
        "tickers": tickers,
        "indices": analysis.get("indices_mentioned") or [],
        "sectors": analysis.get("sectors_mentioned") or [],
        "notable_quotes": analysis.get("notable_quotes") or [],
        "analyzed_at": datetime.now().isoformat(),
    }
