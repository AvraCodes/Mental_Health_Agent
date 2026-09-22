"""Crossref scraper.

Primary: Crossref REST API (https://api.crossref.org/works?query.title=...).
Fallback: Playwright scrape of https://search.crossref.org/search/works?q=...
"""

from __future__ import annotations

import urllib.parse
from typing import Any

import httpx

from .base import API_HEADERS, CONTACT_EMAIL, api_get, match_confidence, title_similarity

API_URL = "https://api.crossref.org/works"


def _pdf_link(links: list[dict] | None) -> str | None:
    if not links:
        return None
    for l in links:
        if l.get("content-type") == "application/pdf" and l.get("URL"):
            return l["URL"]
    return None


def fetch_via_api(paper: dict[str, Any], client: httpx.Client | None = None) -> dict[str, Any]:
    title = paper.get("paper_name", "")
    params = {
        "query.title": title,
        "rows": 3,
        "mailto": CONTACT_EMAIL,
        "select": "DOI,title,author,published,abstract,URL,link,score,container-title,publisher",
    }
    close = False
    if client is None:
        client = httpx.Client(headers=API_HEADERS, timeout=30.0, follow_redirects=True)
        close = True
    try:
        r = api_get(client, API_URL, params=params)
        r.raise_for_status()
        items = r.json().get("message", {}).get("items", [])
        if not items:
            return {"found": False, "site": "Crossref", "query": title}
        # rank by title similarity so a fuzzy neighbour can't silently win
        items = sorted(
            items,
            key=lambda it: title_similarity(title, (it.get("title") or [None])[0]),
            reverse=True,
        )
        it = items[0]
        matched_title = (it.get("title") or [None])[0]
        sim = title_similarity(title, matched_title)
        authors = [
            f"{a.get('given', '')} {a.get('family', '')}".strip()
            for a in it.get("author", [])
        ]
        year = None
        pub = it.get("published") or it.get("created") or {}
        parts = (pub.get("date-parts") or [[]])[0]
        if parts:
            year = parts[0]
        conf = match_confidence(sim)
        try:
            exp_year = int(paper.get("year") or 0)
            if exp_year and year and abs(exp_year - int(year)) > 2:
                conf = "low"
        except (TypeError, ValueError):
            pass
        return {
            "found": True,
            "site": "Crossref",
            "query": title,
            "method": "api",
            "doi": it.get("DOI"),
            "doi_url": f"https://doi.org/{it.get('DOI')}" if it.get("DOI") else None,
            "title_matched": (it.get("title") or [None])[0],
            "title_similarity": round(sim, 3),
            "match_confidence": conf,
            "authors": authors,
            "year": year,
            "venue": (it.get("container-title") or [None])[0],
            "publisher": it.get("publisher"),
            "abstract": it.get("abstract"),
            "pdf_url": _pdf_link(it.get("link")),
            "landing_page_url": it.get("URL"),
            "score": it.get("score"),
            "raw": it,
        }
    except Exception as e:
        return {"found": False, "site": "Crossref", "query": title, "method": "api", "error": str(e)}
    finally:
        if close:
            client.close()


def fetch_via_playwright(paper: dict[str, Any], context) -> dict[str, Any]:
    title = paper.get("paper_name", "")
    url = f"https://search.crossref.org/search/works?q={urllib.parse.quote(title)}"
    page = context.new_page()
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(4000)
        rows = page.eval_on_selector_all(
            ".item, .result, tbody tr",
            "els => els.slice(0,5).map(e => e.innerText.slice(0,400))",
        )
        return {
            "found": bool(rows),
            "site": "Crossref",
            "query": title,
            "method": "playwright",
            "search_url": url,
            "top_rows": rows,
        }
    except Exception as e:
        return {"found": False, "site": "Crossref", "query": title, "method": "playwright", "error": str(e)}
    finally:
        page.close()


def fetch(paper: dict[str, Any], httpx_client=None, pw_context=None) -> dict[str, Any]:
    result = fetch_via_api(paper, client=httpx_client)
    if result.get("found"):
        return result
    if pw_context is not None:
        result["playwright_fallback"] = fetch_via_playwright(paper, pw_context)
    return result
