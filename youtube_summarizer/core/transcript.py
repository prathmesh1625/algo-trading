import asyncio
from functools import partial

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
    CouldNotRetrieveTranscript,
)

from youtube_summarizer.config import MAX_TRANSCRIPT_CHARS

# Hindi first — primary use case, then English fallbacks
_LANG_PRIORITY = ["hi", "hi-IN", "en", "en-IN", "en-GB", "en-US"]


def _normalize(fetched) -> list[dict]:
    """Convert v1.x FetchedTranscript or list-of-dicts to list[dict]."""
    if hasattr(fetched, "to_raw_data"):
        return fetched.to_raw_data()
    result = []
    for entry in fetched:
        if isinstance(entry, dict):
            result.append(entry)
        else:
            result.append({
                "text": getattr(entry, "text", ""),
                "start": float(getattr(entry, "start", 0)),
                "duration": float(getattr(entry, "duration", 0)),
            })
    return result


def _sync_fetch(video_id: str) -> list[dict]:
    api = YouTubeTranscriptApi()

    # Step 1: try api.fetch() with preferred languages directly (fastest path)
    for lang in _LANG_PRIORITY:
        try:
            fetched = api.fetch(video_id, languages=[lang])
            entries = _normalize(fetched)
            if entries:
                return entries
        except (NoTranscriptFound, TranscriptsDisabled):
            continue
        except CouldNotRetrieveTranscript:
            continue
        except Exception:
            continue

    # Step 2: list all available transcripts and try each one
    try:
        transcript_list = api.list(video_id)
        all_transcripts = list(transcript_list)
    except TranscriptsDisabled:
        raise ValueError("Captions are disabled for this video.")
    except VideoUnavailable:
        raise ValueError("This video is unavailable or private.")
    except CouldNotRetrieveTranscript as e:
        raise ValueError(f"Could not retrieve transcript: {e}")
    except Exception as e:
        raise ValueError(f"Could not access video transcripts: {e}")

    if not all_transcripts:
        raise ValueError("No captions available for this video.")

    # Prefer manually-created over auto-generated
    for want_generated in (False, True):
        for t in all_transcripts:
            if t.is_generated == want_generated:
                try:
                    fetched = api.fetch(video_id, languages=[t.language_code])
                    entries = _normalize(fetched)
                    if entries:
                        return entries
                except Exception:
                    continue

    raise ValueError(
        "No usable captions found. The video may only have auto-generated captions "
        "in an unsupported language."
    )


async def fetch_transcript(video_id: str) -> list[dict]:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, partial(_sync_fetch, video_id))


def fmt_ts(seconds: float) -> str:
    s = int(seconds)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{sec:02d}"
    return f"{m}:{sec:02d}"


def entries_to_text(entries: list[dict]) -> str:
    return "\n".join(f"[{fmt_ts(e['start'])}] {e['text']}" for e in entries)


def sample_transcript(entries: list[dict], max_chars: int) -> list[dict]:
    """Uniformly sample entries so entries_to_text output stays within max_chars."""
    if not entries:
        return entries
    full = entries_to_text(entries)
    if len(full) <= max_chars:
        return entries
    ratio = max_chars / len(full)
    n = max(5, int(len(entries) * ratio))
    if n >= len(entries):
        return entries
    step = (len(entries) - 1) / (n - 1)
    indices = sorted({round(i * step) for i in range(n)})
    return [entries[i] for i in indices]


def chunk_transcript(entries: list[dict]) -> list[str]:
    full = entries_to_text(entries)
    if len(full) <= MAX_TRANSCRIPT_CHARS:
        return [full]

    chunks, current, current_len = [], [], 0
    for e in entries:
        line = f"[{fmt_ts(e['start'])}] {e['text']}\n"
        if current_len + len(line) > MAX_TRANSCRIPT_CHARS and current:
            chunks.append("".join(current))
            current, current_len = [], 0
        current.append(line)
        current_len += len(line)
    if current:
        chunks.append("".join(current))
    return chunks
