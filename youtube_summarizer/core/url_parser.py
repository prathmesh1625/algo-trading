import re
from urllib.parse import urlparse, parse_qs

_PATTERNS = [
    r'(?:youtube\.com/watch\?.*v=)([a-zA-Z0-9_-]{11})',
    r'(?:youtu\.be/)([a-zA-Z0-9_-]{11})',
    r'(?:youtube\.com/embed/)([a-zA-Z0-9_-]{11})',
    r'(?:youtube\.com/shorts/)([a-zA-Z0-9_-]{11})',
    r'(?:youtube\.com/v/)([a-zA-Z0-9_-]{11})',
]

def extract_video_id(url: str) -> str | None:
    url = url.strip()
    for pattern in _PATTERNS:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    try:
        parsed = urlparse(url)
        if 'youtube' in parsed.netloc:
            qs = parse_qs(parsed.query)
            if 'v' in qs:
                vid = qs['v'][0]
                if len(vid) == 11:
                    return vid
    except Exception:
        pass
    return None

def is_valid_youtube_url(url: str) -> bool:
    return extract_video_id(url) is not None

def canonical_url(video_id: str) -> str:
    return f"https://www.youtube.com/watch?v={video_id}"
