"""OpenAlex scraper.

Primary: OpenAlex REST API (https://api.openalex.org/works?search=...).
Fallback: Playwright scrape of https://openalex.org/works?search=...

Returns enriched dict with doi, openalex_id, pdf_url (best OA), landing pages,
abstract, authors, citation counts.
"""

from __future__ import annotations

import urllib.parse
from typing import Any

import httpx

from .base import API_HEADERS, CONTACT_EMAIL, api_get, match_confidence, reconstruct_abstract, title_similarity

API_URL = "https://api.openalex.org/works"


def fetch_via_api(paper: dict[str, Any], client: httpx.Client | None = None) -> dict[str, Any]:
    title = paper.get("paper_name", "")
    # '?' in the search query makes OpenAlex return 400 — strip it.
    search_q = title.replace("?", "").replace("#", "")
    params = {"search": search_q, "per-page": 3, "mailto": CONTACT_EMAIL}
    close = False
    if client is None:
        client = httpx.Client(headers=API_HEADERS, timeout=30.0, follow_redirects=True)
        close = True
    try:
        try:
            r = api_get(client, API_URL, params=params)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 400:
                # fallback: plain normalized words
                from .base import normalize_title

                params = {"search": normalize_title(title), "per-page": 3, "mailto": CONTACT_EMAIL}
                r = api_get(client, API_URL, params=params)
            else:
                raise
        r.raise_for_status()
        data = r.json()
        results = data.get("results", [])
        if not results:
            return {"found": False, "site": "OpenAlex", "query": title}
        # OpenAlex `search` is full-text: rank candidates by title similarity
        # and take the best, so a fuzzy neighbour can't silently win.
        ranked = sorted(
            results,
            key=lambda w: title_similarity(title, w.get("title")),
            reverse=True,
        )
        w = ranked[0]
        sim = title_similarity(title, w.get("title"))
        conf = match_confidence(sim)
        # year sanity: a 5+ year gap almost always means a wrong neighbour
        # (e.g. 2025 query matching a 2019 paper) — downgrade to low.
        try:
            exp_year = int(paper.get("year") or 0)
            got_year = int(w.get("publication_year") or 0)
            if exp_year and got_year and abs(exp_year - got_year) > 2:
                conf = "low"
        except (TypeError, ValueError):
            pass
        best_oa = w.get("best_oa_location") or {}
        primary = w.get("primary_location") or {}
        authors = [
            (a.get("author") or {}).get("display_name", "")
            for a in w.get("authorships", [])
        ]
        # Collect every OA PDF candidate (best first, then alternate locations
        # e.g. PMC / repository copies when the publisher blocks direct fetch).
        pdf_candidates: list[str] = []
        for loc in [best_oa] + (w.get("locations") or []):
            u = (loc or {}).get("pdf_url")
            if u and u not in pdf_candidates:
                pdf_candidates.append(u)
        return {
            "found": True,
            "site": "OpenAlex",
            "query": title,
            "method": "api",
            "openalex_id": w.get("id"),
            "doi": w.get("doi"),
            "title_matched": w.get("title"),
            "title_similarity": round(sim, 3),
            "match_confidence": conf,
            "year": w.get("publication_year"),
            "venue": ((primary.get("source") or {}).get("display_name")),
            "authors": authors,
            "abstract": reconstruct_abstract(w.get("abstract_inverted_index")),
            "cited_by_count": w.get("cited_by_count"),
            "is_oa": w.get("open_access", {}).get("is_oa"),
            "pdf_url": best_oa.get("pdf_url"),
            "pdf_candidates": pdf_candidates,
            "landing_page_url": best_oa.get("landing_page_url") or (primary.get("landing_page_url")),
            "source_url": (primary.get("source") or {}).get("homepage_url"),
            "raw": w,
        }
    except Exception as e:
        return {"found": False, "site": "OpenAlex", "query": title, "method": "api", "error": str(e)}
    finally:
        if close:
            client.close()


def fetch_via_playwright(paper: dict[str, Any], context) -> dict[str, Any]:
    """Fallback: scrape OpenAlex web UI search page with Playwright."""
    title = paper.get("paper_name", "")
    q = urllib.parse.quote(title)
    url = f"https://openalex.org/works?search={q}"
    page = context.new_page()
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(4000)
        # Web UI is a JS app; grab first work link + JSON-LD if present
        content = page.content()
        links = page.eval_on_selector_all(
            "a[href*='/works/W']",
            "els => els.slice(0,5).map(e => ({href: e.href, text: e.innerText.slice(0,200)}))",
        )
        return {
            "found": bool(links),
            "site": "OpenAlex",
            "query": title,
            "method": "playwright",
            "search_url": url,
            "top_links": links,
            "note": "Playwright fallback only captures links; use API result as canonical.",
            "page_bytes": len(content),
        }
    except Exception as e:
        return {"found": False, "site": "OpenAlex", "query": title, "method": "playwright", "error": str(e)}
    finally:
        page.close()


def fetch(paper: dict[str, Any], httpx_client=None, pw_context=None) -> dict[str, Any]:
    result = fetch_via_api(paper, client=httpx_client)
    if result.get("found"):
        return result
    # API missed -> try browser fallback for diagnostics
    if pw_context is not None:
        fb = fetch_via_playwright(paper, pw_context)
        result["playwright_fallback"] = fb
    return result
