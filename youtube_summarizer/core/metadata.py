import asyncio
from functools import partial

import yt_dlp


def _sync_fetch(url: str) -> dict:
    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": False,
        "socket_timeout": 15,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)

    upload_date = info.get("upload_date", "")
    if upload_date and len(upload_date) == 8:
        upload_date = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:]}"

    thumbnail = ""
    thumbnails = info.get("thumbnails") or []
    for t in reversed(thumbnails):
        if t.get("url"):
            thumbnail = t["url"]
            break
    if not thumbnail:
        thumbnail = f"https://img.youtube.com/vi/{info.get('id', '')}/mqdefault.jpg"

    return {
        "title": info.get("title") or "Unknown Title",
        "channel": info.get("uploader") or info.get("channel") or "Unknown Channel",
        "duration": info.get("duration") or 0,
        "description": (info.get("description") or "")[:1500],
        "thumbnail": thumbnail,
        "upload_date": upload_date,
        "view_count": info.get("view_count") or 0,
    }


async def fetch_metadata(url: str) -> dict:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, partial(_sync_fetch, url))
