"""Google Scholar scraper (Playwright-first; Scholar has no public API).

Scholar aggressively blocks bots (HTTP 403 / "Sorry... unusual traffic"
CAPTCHA). This module:
  - uses a real Chromium context with Scholar-friendly headers,
  - detects block pages and backs off instead of hammering,
  - parses result cards: title, link, authors, venue, year, cited-by,
    snippet, and the [PDF]/[HTML] side link when present.

Typical output per result::
    {"title": ..., "url": ..., "authors": [...], "venue": ...,
     "year": ..., "cited_by": ..., "snippet": ..., "pdf_url": ...}
"""

from __future__ import annotations

import re
import urllib.parse
from typing import Any

SEARCH_TMPL = "https://scholar.google.com/scholar?hl=en&as_sdt=0,5&q={q}&start={start}"

BLOCK_MARKERS = (
    "our systems have detected unusual traffic",
    "please show you're not a robot",
    "sorry, we can't verify",
)


def is_blocked(page) -> bool:
    try:
        url = (page.url or "").lower()
        if "sorry" in url:
            return True
        body = page.evaluate(
            "() => document.body ? document.body.innerText.slice(0, 1000).toLowerCase() : ''"
        )
        return any(m in body for m in BLOCK_MARKERS)
    except Exception:
        return False


def parse_result_cards(page) -> list[dict[str, Any]]:
    try:
        return page.evaluate(
            """() => Array.from(document.querySelectorAll('div.gs_r.gs_or.gs_scl')).map(el => {
              const t = el.querySelector('h3.gs_rt');
              const a = t ? t.querySelector('a') : null;
              const meta = el.querySelector('div.gs_a');
              const snip = el.querySelector('div.gs_rs');
              const cite = Array.from(el.querySelectorAll('div.gs_fl a'))
                .find(x => (x.innerText || '').startsWith('Cited by'));
              const side = el.querySelector('div.gs_ggs a');
              return {
                title: t ? t.innerText.trim() : null,
                url: a ? a.href : null,
                meta_raw: meta ? meta.innerText.trim() : null,
                snippet: snip ? snip.innerText.trim().slice(0, 600) : null,
                cited_by_text: cite ? cite.innerText.trim() : null,
                cited_by_url: cite ? cite.href : null,
                pdf_url: side ? side.href : null,
                side_label: side ? side.innerText.trim().slice(0, 40) : null,
              };
            })"""
        )
    except Exception:
        return []


def split_meta(meta_raw: str | None) -> dict[str, Any]:
    """'A Author, B Author… - Journal Name, 2023 - publisher' -> parts.

    Handles Scholar's ellipsis-truncated author lists and year suffixes.
    """
    out: dict[str, Any] = {"authors": [], "venue": None, "year": None}
    if not meta_raw:
        return out
    # Scholar separates chunks with nbsp+hyphen ("AA Alalwan…\xa0-\xa0Journal");
    # normalize all whitespace first or the split misses.
    meta_raw = re.sub(r"\s+", " ", meta_raw.replace(" ", " ")).strip()
    m = re.search(r"\b((?:19|20)\d{2})\b", meta_raw)
    if m:
        out["year"] = int(m.group(1))
    parts = [p.strip() for p in meta_raw.split(" - ")]
    if parts:
        authors = []
        for a in parts[0].split(","):
            a = a.replace("…", "").replace("...", "").strip()
            if not a or re.fullmatch(r"(19|20)\d{2}", a):
                continue
            authors.append(a)
        out["authors"] = authors
    # venue = chunk holding ", YEAR" (typical `Journal, 2023` shape)
    for p in parts[1:]:
        if re.search(r",\s*(19|20)\d{2}\s*$", p):
            out["venue"] = re.sub(r",\s*(19|20)\d{2}\s*$", "", p).strip()[:200] or None
            break
    if out["venue"] is None and len(parts) >= 2:
        # fall back to first non-year, non-URL middle chunk
        for p in parts[1:]:
            if re.fullmatch(r"(19|20)\d{2}", p) or p.startswith("http") or len(p) > 200:
                continue
            out["venue"] = p
            break
    return out


def cited_count(text: str | None) -> int | None:
    if not text:
        return None
    m = re.search(r"Cited by (\d+)", text)
    return int(m.group(1)) if m else None


def search(query: str, context, max_results: int = 20) -> dict[str, Any]:
    """Run one Scholar query, following pagination until max_results."""
    page = context.new_page()
    results: list[dict[str, Any]] = []
    start = 0
    blocked = False
    try:
        while len(results) < max_results:
            url = SEARCH_TMPL.format(q=urllib.parse.quote(query), start=start)
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=45000)
            except Exception as e:
                return {
                    "query": query, "results": results, "blocked": False,
                    "error": f"navigation failed: {type(e).__name__}",
                }
            page.wait_for_timeout(4000)
            if is_blocked(page):
                blocked = True
                break
            cards = parse_result_cards(page)
            if not cards:
                break
            for c in cards:
                meta = split_meta(c.get("meta_raw"))
                results.append(
                    {
                        "title": c.get("title"),
                        "url": c.get("url"),
                        "authors": meta["authors"],
                        "venue": meta["venue"],
                        "year": meta["year"],
                        "cited_by": cited_count(c.get("cited_by_text")),
                        "cited_by_url": c.get("cited_by_url"),
                        "snippet": c.get("snippet"),
                        "pdf_url": c.get("pdf_url"),
                        "side_label": c.get("side_label"),
                        "query": query,
                    }
                )
                if len(results) >= max_results:
                    break
            # Scholar shows 10/page; stop if the page had fewer (last page)
            if len(cards) < 10:
                break
            start += 10
            page.wait_for_timeout(3000)
        return {"query": query, "results": results, "blocked": blocked}
    finally:
        page.close()
