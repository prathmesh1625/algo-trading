import json
import asyncio

from youtube_summarizer.config import (
    LLM_PROVIDER,
    ANTHROPIC_API_KEY, CLAUDE_MODEL,
    OPENAI_API_KEY, OPENAI_MODEL,
    GROQ_API_KEY, GROQ_MODEL,
)

_SYSTEM_PROMPT = """You are a senior financial analyst specializing in Indian stock markets (NSE/BSE).
Analyze the transcript of a YouTube video and extract structured financial information.

The transcript is formatted as lines like:
  [M:SS] spoken text here

CRITICAL TIMESTAMP RULE: Every "timestamp" field in your JSON MUST be the M:SS value from a [M:SS] marker that appears in the transcript — copy the digits only, WITHOUT the square brackets (e.g. write "5:27" not "[5:27]"). Do NOT estimate, round, or invent timestamps. Find the actual line in the transcript and use its value.

Focus on:
- Indian stocks (NSE/BSE listed), indices (NIFTY, BANKNIFTY, SENSEX, FINNIFTY, MIDCAP, SMALLCAP)
- Trading concepts: technical analysis, fundamental analysis, options, futures, support/resistance
- Sector and macro commentary relevant to Indian markets

Return ONLY valid JSON with this exact structure (no markdown, no extra keys):
{
  "tldr": "5-7 sentence comprehensive overview covering what stocks/topics are discussed, what the analyst recommends, and the overall market view",
  "summary_sections": [
    {
      "title": "Descriptive section title (5-8 words)",
      "content": "5-7 sentence detailed summary. Include specific stock names, price levels, reasoning given by the analyst, and any buy/sell recommendations mentioned in this part of the video.",
      "timestamp": "5:27"
    }
  ],
  "key_concepts": [
    {
      "concept": "Concept name",
      "explanation": "2-3 sentence explanation of how this concept is used or discussed in this specific video"
    }
  ],
  "tickers_mentioned": [
    {
      "symbol": "RELIANCE",
      "company_name": "Reliance Industries Ltd",
      "context": "Specific reason mentioned — include price levels, chart pattern, or news catalyst if stated",
      "sentiment": "bullish",
      "price_target": "Rs.2800",
      "stop_loss": null,
      "timestamp": "5:27"
    }
  ],
  "indices_mentioned": ["NIFTY", "BANKNIFTY"],
  "sectors_mentioned": ["IT", "Banking"],
  "notable_quotes": [
    "Translate any Hindi quotes to English and include the key insight or recommendation"
  ],
  "market_outlook": "bullish"
}

Rules:
- summary_sections: create 6-9 sections covering the full video from start to finish chronologically
- Each section content must be 5-7 sentences — be specific about stocks, levels, and reasoning
- sentiment must be one of: "bullish", "bearish", "neutral"
- market_outlook must be one of: "bullish", "bearish", "neutral", "mixed"
- price_target and stop_loss: use "Rs.XXXX" format or null if not mentioned
- Include ALL stocks mentioned even briefly — do not filter aggressively
- If the video is in Hindi, translate all content to English in your output
- Return an empty but valid JSON object matching the schema if the video has no financial content"""


def _handle_error(e: Exception) -> None:
    err = str(e)
    provider = LLM_PROVIDER.upper()
    if "insufficient_quota" in err or "quota" in err.lower() or "credit" in err.lower():
        raise ValueError(f"Your {provider} account has no remaining credits. Please check your billing.")
    if "invalid_api_key" in err or "authentication" in err.lower() or "401" in err or "api_key" in err.lower():
        raise ValueError(f"Invalid {provider} API key. Check your .env file.")
    if "request too large" in err.lower() or "413" in err:
        raise ValueError("The video transcript is too long for this API tier. Try a shorter video.")
    if "rate_limit" in err.lower() or "429" in err or "overloaded" in err.lower():
        raise ValueError("Rate limit hit. Please wait a moment and try again.")
    raise ValueError(f"LLM API error ({provider}): {e}")


async def _call_claude(messages: list[dict]) -> dict:
    from anthropic import AsyncAnthropic
    if not ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY is not set. Add it to your .env file.")
    client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

    system = next((m["content"] for m in messages if m["role"] == "system"), "")
    user_msgs = [m for m in messages if m["role"] != "system"]
    # Prefill with "{" to force JSON output
    prefill_msgs = user_msgs + [{"role": "assistant", "content": "{"}]

    try:
        response = await client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=8000,  # detailed schema (6-9 sections + tickers) needs headroom; 2000 truncated the JSON
            temperature=0.1,
            system=system,
            messages=prefill_msgs,
        )
    except Exception as e:
        _handle_error(e)

    if response.stop_reason == "max_tokens":
        raise ValueError(
            "The analysis was cut off because it exceeded the output limit. "
            "Try a shorter video, or raise max_tokens in analyzer.py."
        )

    raw = "{" + (response.content[0].text if response.content else "}")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


async def _call_openai_compat(messages: list[dict]) -> dict:
    if LLM_PROVIDER == "groq":
        from groq import AsyncGroq
        if not GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY is not set. Add it to your .env file.")
        client, model = AsyncGroq(api_key=GROQ_API_KEY), GROQ_MODEL
    else:
        from openai import AsyncOpenAI
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is not set. Add it to your .env file.")
        client, model = AsyncOpenAI(api_key=OPENAI_API_KEY), OPENAI_MODEL

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=2000,
        )
    except Exception as e:
        _handle_error(e)

    raw = response.choices[0].message.content or "{}"
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


async def _call_llm(messages: list[dict]) -> dict:
    if LLM_PROVIDER == "claude":
        return await _call_claude(messages)
    return await _call_openai_compat(messages)


async def analyze_transcript(title: str, channel: str, transcript_text: str) -> dict:
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"Video Title: {title}\nChannel: {channel}\n\nTranscript:\n{transcript_text}",
        },
    ]
    return await _call_llm(messages)


async def analyze_chunks(title: str, channel: str, chunks: list[str]) -> dict:
    if len(chunks) == 1:
        return await analyze_transcript(title, channel, chunks[0])

    chunk_results = await asyncio.gather(
        *[analyze_transcript(title, channel, chunk) for chunk in chunks]
    )

    combined = "\n\n---\n\n".join(
        f"Chunk {i + 1} of {len(chunks)}:\n{json.dumps(r, ensure_ascii=False, indent=2)}"
        for i, r in enumerate(chunk_results)
    )

    synthesis_user = (
        f"The video '{title}' by '{channel}' was too long and was analyzed in "
        f"{len(chunks)} chunks. Here are the individual chunk analyses:\n\n"
        f"{combined}\n\n"
        "Synthesize these into ONE coherent final report following the same JSON schema. "
        "Merge duplicate tickers (keep the richest entry), combine and deduplicate "
        "concepts/sections/quotes, and write a unified tldr."
    )

    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": synthesis_user},
    ]
    return await _call_llm(messages)
