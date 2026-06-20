import asyncio
import json
import urllib.parse
import urllib.request
from functools import partial

import yt_dlp

from youtube_summarizer.config import yt_dlp_proxy_url


def _oembed_fallback(url: str) -> dict:
    """Lightweight metadata via YouTube oEmbed (not bot-blocked like yt-dlp).

    Only returns title/channel/thumbnail; duration/views are unavailable here.
    """
    oembed = "https://www.youtube.com/oembed?" + urllib.parse.urlencode(
        {"url": url, "format": "json"}
    )
    proxy = yt_dlp_proxy_url()
    if proxy:
        opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({"http": proxy, "https": proxy})
        )
    else:
        opener = urllib.request.build_opener()
    with opener.open(oembed, timeout=15) as resp:
        info = json.loads(resp.read().decode("utf-8"))

    return {
        "title": info.get("title") or "Unknown Title",
        "channel": info.get("author_name") or "Unknown Channel",
        "duration": 0,
        "description": "",
        "thumbnail": info.get("thumbnail_url") or "",
        "upload_date": "",
        "view_count": 0,
    }


def _sync_fetch(url: str) -> dict:
    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": False,
        "socket_timeout": 15,
    }
    proxy = yt_dlp_proxy_url()
    if proxy:
        opts["proxy"] = proxy

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception:
        # yt-dlp blocked/failed (common on cloud IPs) — fall back to oEmbed
        return _oembed_fallback(url)

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
