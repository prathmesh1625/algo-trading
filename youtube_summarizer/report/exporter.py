from __future__ import annotations

import io
from datetime import datetime


# ─── Markdown ────────────────────────────────────────────────────────────────

def to_markdown(report: dict) -> str:
    meta = report["meta"]
    url = report.get("url", "")
    lines: list[str] = []

    lines += [
        f"# {meta['title']}",
        f"",
        f"| | |",
        f"|---|---|",
        f"| **Channel** | {meta['channel']} |",
        f"| **Duration** | {meta['duration_fmt']} |",
        f"| **Video URL** | {url} |",
        f"| **Analyzed** | {report['analyzed_at'][:19].replace('T', ' ')} |",
        f"",
        f"---",
        f"",
    ]

    outlook = report.get("market_outlook", "neutral")
    lines += [
        f"## TL;DR",
        f"",
        f"> {report['tldr']}",
        f"",
        f"**Market Outlook:** {outlook.title()}  ",
    ]

    if report.get("indices"):
        lines.append(f"**Indices Mentioned:** {', '.join(report['indices'])}  ")
    if report.get("sectors"):
        lines.append(f"**Sectors:** {', '.join(report['sectors'])}  ")
    lines.append("")

    if report.get("key_concepts"):
        lines += ["---", "", "## Key Concepts", ""]
        for kc in report["key_concepts"]:
            lines.append(f"- **{kc.get('concept', '')}** — {kc.get('explanation', '')}")
        lines.append("")

    if report.get("tickers"):
        lines += ["---", "", "## Stocks & Tickers Mentioned (NSE/BSE)", ""]
        lines.append(
            "| Symbol | Company | Exchange | Sector | Sentiment | Target | Stop Loss | Timestamp |"
        )
        lines.append(
            "|--------|---------|----------|--------|-----------|--------|-----------|-----------|"
        )
        for t in report["tickers"]:
            s = t.get("sentiment", "neutral")
            arrow = "▲" if s == "bullish" else ("▼" if s == "bearish" else "●")
            lines.append(
                f"| **{t.get('symbol','')}** "
                f"| {t.get('company_name','')} "
                f"| {t.get('exchange','NSE')} "
                f"| {t.get('sector','—')} "
                f"| {arrow} {s.title()} "
                f"| {t.get('price_target') or '—'} "
                f"| {t.get('stop_loss') or '—'} "
                f"| {t.get('timestamp','')} |"
            )
        lines.append("")

    if report.get("summary_sections"):
        lines += ["---", "", "## Detailed Summary", ""]
        for sec in report["summary_sections"]:
            ts = sec.get("timestamp", "")
            title = sec.get("title", "")
            lines += [f"### [{ts}] {title}", "", sec.get("content", ""), ""]

    if report.get("notable_quotes"):
        lines += ["---", "", "## Notable Quotes", ""]
        for q in report["notable_quotes"]:
            lines += [f"> {q}", ""]

    lines += [
        "---",
        "",
        "*Auto-generated from video transcript. Not financial advice.*",
    ]
    return "\n".join(lines)


# ─── PDF ─────────────────────────────────────────────────────────────────────

def _ps(text) -> str:
    """Encode to latin-1, replacing unsupported characters (e.g. Devanagari) with '?'."""
    return str(text or "").encode("latin-1", errors="replace").decode("latin-1")


def to_pdf(report: dict) -> bytes:
    try:
        from fpdf import FPDF, XPos, YPos
    except ImportError:
        raise RuntimeError("fpdf2 is not installed. Run: pip install fpdf2")

    meta = report["meta"]
    url = report.get("url", "")

    class PDF(FPDF):
        def header(self):
            self.set_fill_color(10, 20, 50)
            self.set_text_color(255, 255, 255)
            self.set_font("Helvetica", "B", 11)
            self.cell(0, 10, "TradeLens  |  Indian Market Video Analysis", fill=True,
                      align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.ln(2)

        def footer(self):
            self.set_y(-14)
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(120, 120, 120)
            self.cell(0, 10, f"Page {self.page_no()}  |  Not financial advice", align="C")

    pdf = PDF()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    W = pdf.w - pdf.l_margin - pdf.r_margin  # usable width (~190 mm)

    def heading(text: str, size: int = 13):
        pdf.set_font("Helvetica", "B", size)
        pdf.set_text_color(10, 20, 50)
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(W, 7, _ps(text))
        pdf.ln(1)

    def body(text: str, size: int = 10):
        pdf.set_font("Helvetica", "", size)
        pdf.set_text_color(30, 30, 30)
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(W, 6, _ps(text))
        pdf.ln(1)

    def rule():
        pdf.set_draw_color(180, 180, 180)
        pdf.line(pdf.get_x(), pdf.get_y(), pdf.get_x() + 190, pdf.get_y())
        pdf.ln(3)

    # Title block
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(10, 20, 50)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(W, 9, _ps(meta["title"]))
    pdf.ln(2)

    body(f"Channel: {meta['channel']}   |   Duration: {meta['duration_fmt']}")
    body(f"URL: {url}")
    body(f"Analyzed: {report['analyzed_at'][:19].replace('T', ' ')}")
    rule()

    # TL;DR
    heading("TL;DR")
    body(report.get("tldr", ""))
    outlook = report.get("market_outlook", "neutral")
    body(f"Market Outlook: {outlook.title()}")
    if report.get("indices"):
        body(f"Indices: {', '.join(report['indices'])}")
    if report.get("sectors"):
        body(f"Sectors: {', '.join(report['sectors'])}")
    rule()

    # Key Concepts
    if report.get("key_concepts"):
        heading("Key Concepts")
        for kc in report["key_concepts"]:
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(30, 30, 30)
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(W, 6, _ps(f"  {kc.get('concept', '')}"))
            body(f"    {kc.get('explanation', '')}")
        rule()

    # Tickers table
    if report.get("tickers"):
        heading("Stocks & Tickers Mentioned")
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_fill_color(220, 230, 245)
        pdf.set_text_color(10, 20, 50)
        col_w = [22, 52, 18, 22, 20, 20, 18, 18]
        headers = ["Symbol", "Company", "Exch.", "Sector", "Sentiment", "Target", "SL", "Time"]
        for i, h in enumerate(headers):
            pdf.cell(col_w[i], 7, h, border=1, fill=True, align="C")
        pdf.ln()

        for t in report["tickers"]:
            s = t.get("sentiment", "neutral")
            if s == "bullish":
                pdf.set_text_color(0, 120, 60)
            elif s == "bearish":
                pdf.set_text_color(180, 20, 20)
            else:
                pdf.set_text_color(150, 100, 0)
            pdf.set_font("Helvetica", "B", 8)
            row = [
                t.get("symbol", ""),
                (t.get("company_name") or "")[:28],
                t.get("exchange", "NSE"),
                (t.get("sector") or "")[:12],
                s.title(),
                t.get("price_target") or "-",
                t.get("stop_loss") or "-",
                t.get("timestamp") or "",
            ]
            for i, cell in enumerate(row):
                pdf.cell(col_w[i], 6, _ps(cell), border=1)
            pdf.ln()
        pdf.set_text_color(30, 30, 30)
        pdf.ln(3)
        rule()

    # Detailed Summary
    if report.get("summary_sections"):
        heading("Detailed Summary")
        for sec in report["summary_sections"]:
            ts = sec.get("timestamp", "")
            title = sec.get("title", "")
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(10, 20, 50)
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(W, 6, _ps(f"[{ts}] {title}"))
            body(sec.get("content", ""))
        rule()

    # Notable Quotes
    if report.get("notable_quotes"):
        heading("Notable Quotes")
        for q in report["notable_quotes"]:
            pdf.set_font("Helvetica", "I", 10)
            pdf.set_text_color(60, 60, 60)
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(W, 6, _ps(f'"{q}"'))
            pdf.ln(2)
        rule()

    body("Auto-generated from video transcript. Not financial advice.")

    buf = io.BytesIO()
    buf.write(pdf.output())
    return buf.getvalue()
