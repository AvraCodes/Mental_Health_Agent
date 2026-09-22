"""Last-resort enrichment: when a paper is not found on its listed `site`,
look it up on Crossref (200M+ works, unthrottled) so the record still ends
up with verified metadata + DOI instead of a bare MISS.

Only accepts medium/high-confidence title matches (similarity + year guard);
anything fuzzier is returned as an unaudited attempt and NOT merged.
"""

from __future__ import annotations

from typing import Any

import httpx

from .base import API_HEADERS, CONTACT_EMAIL, api_get, match_confidence, title_similarity
from .crossref import _pdf_link

API_URL = "https://api.crossref.org/works"


def crossref_lookup(paper: dict[str, Any], client: httpx.Client | None = None) -> dict[str, Any]:
    title = paper.get("paper_name", "")
    params = {
        "query.title": title,
        "rows": 5,
        "mailto": CONTACT_EMAIL,
        "select": "DOI,title,author,published,URL,link,score,container-title,publisher",
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
            return {"found": False, "query": title, "method": "crossref-fallback"}
        items = sorted(
            items,
            key=lambda it: title_similarity(title, (it.get("title") or [None])[0]),
            reverse=True,
        )
        it = items[0]
        matched = (it.get("title") or [None])[0]
        sim = title_similarity(title, matched)
        conf = match_confidence(sim)
        authors = [f"{a.get('given', '')} {a.get('family', '')}".strip() for a in it.get("author", [])]
        year = None
        parts = ((it.get("published") or it.get("created") or {}).get("date-parts") or [[]])[0]
        if parts:
            year = parts[0]
        try:
            exp = int(paper.get("year") or 0)
            if exp and year and abs(exp - int(year)) > 2:
                conf = "low"
        except (TypeError, ValueError):
            pass
        return {
            "found": conf in ("high", "medium"),
            "query": title,
            "method": "crossref-fallback",
            "doi": it.get("DOI"),
            "doi_url": f"https://doi.org/{it.get('DOI')}" if it.get("DOI") else None,
            "title_matched": matched,
            "title_similarity": round(sim, 3),
            "match_confidence": conf,
            "authors": authors,
            "year": year,
            "venue": (it.get("container-title") or [None])[0],
            "publisher": it.get("publisher"),
            "pdf_url": _pdf_link(it.get("link")),
            "landing_page_url": it.get("URL"),
        }
    except Exception as e:
        return {"found": False, "query": title, "method": "crossref-fallback", "error": str(e)}
    finally:
        if close:
            client.close()
