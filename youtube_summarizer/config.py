import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent.parent  # algo-trading/
load_dotenv(BASE_DIR / ".env")

# ── LLM provider ──────────────────────────────────────────────
# LLM_PROVIDER options: "claude" | "groq" | "openai"
LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "groq").lower()

ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL: str = os.getenv("CLAUDE_MODEL", "claude-haiku-4-5-20251001")

OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# ── YouTube access proxy ──────────────────────────────────────
# YouTube blocks requests from cloud/datacenter IPs ("Sign in to confirm
# you're not a bot"). Route requests through a residential proxy when deployed.
# Option 1 — Webshare (residential plan): set username + password.
WEBSHARE_PROXY_USERNAME: str = os.getenv("WEBSHARE_PROXY_USERNAME", "")
WEBSHARE_PROXY_PASSWORD: str = os.getenv("WEBSHARE_PROXY_PASSWORD", "")
# Option 2 — any generic proxy: set a full URL, e.g. http://user:pass@host:port
YT_PROXY_URL: str = os.getenv("YT_PROXY_URL", "")


def yt_dlp_proxy_url() -> str:
    """Proxy URL for yt-dlp (and oEmbed), or '' if none configured."""
    if WEBSHARE_PROXY_USERNAME and WEBSHARE_PROXY_PASSWORD:
        # Webshare residential rotating endpoint (matches youtube-transcript-api)
        return (
            f"http://{WEBSHARE_PROXY_USERNAME}-rotate:"
            f"{WEBSHARE_PROXY_PASSWORD}@p.webshare.io:80"
        )
    return YT_PROXY_URL


# ── App ───────────────────────────────────────────────────────
DB_PATH: Path = BASE_DIR / "data" / "history.db"
MAX_TRANSCRIPT_CHARS: int = 80_000
# Groq free tier: 6,000 TPM. Hindi text ≈ 0.53 tokens/char.
# Budget: 6000 - ~800 system - ~2000 output = ~3200 tokens ≈ 5500 chars.
GROQ_MAX_TRANSCRIPT_CHARS: int = 5_500
# Claude has 200K context — no sampling needed for normal videos.
CLAUDE_MAX_TRANSCRIPT_CHARS: int = 80_000
