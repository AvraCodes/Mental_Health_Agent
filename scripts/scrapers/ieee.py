"""IEEE Xplore scraper (Playwright-first).

IEEE has no open search API without a key, and article HTML/PDFs are
paywalled, so this module:

1. Uses Playwright to scrape the IEEE Xplore search page for metadata
   (title, authors, venue, year, document URL, DOI, abstract snippet).
2. Resolves an open-access PDF via OpenAlex (by title) so the pipeline can
   still save a PDF legally. It NEVER tries to bypass IEEE paywalls.

Search page: https://ieeexplore.ieee.org/search/searchresult.jsp?queryText=...
"""

from __future__ import annotations

import re
import urllib.parse
from typing import Any

import httpx

from .base import API_HEADERS, CONTACT_EMAIL, api_get, title_similarity

SEARCH_TMPL = "https://ieeexplore.ieee.org/search/searchresult.jsp?queryText={q}&highlight=true&returnType=SEARCH&matchPubs=true&rowsPerPage=10"


def _extract_art_number(url: str | None) -> str | None:
    if not url:
        return None
    m = re.search(r"document/(\d+)", url)
    return m.group(1) if m else None


def fetch_via_playwright(paper: dict[str, Any], context) -> dict[str, Any]:
    title = paper.get("paper_name", "")
    search_url = SEARCH_TMPL.format(q=urllib.parse.quote(title))
    page = context.new_page()
    try:
        try:
            page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
        except Exception as e:
            # IEEE's bot wall can stall navigation — parse whatever loaded
            print(f"    [ieee] search navigation slow/blocked ({e.__class__.__name__}), parsing anyway...")
        # IEEE is heavy JS; wait for results container or timeout gracefully
        try:
            page.wait_for_selector("xpl-results-item, .List-results-items, .result-item", timeout=15000)
        except Exception:
            page.wait_for_timeout(3000)
        page.wait_for_timeout(2000)

        data = page.evaluate(
            """() => {
              const items = Array.from(document.querySelectorAll('xpl-results-item, .List-results-items > *, .result-item')).slice(0,5);
              return items.map(el => {
                const t = el.querySelector('h2 a, h3 a, .result-item-title a, a[href*="/document/"]');
                const title = t ? t.innerText.trim() : el.innerText.slice(0,300).trim();
                const href = t ? t.href : null;
                const authors = Array.from(el.querySelectorAll('.author, [class*="author"]')).slice(0,10).map(a=>a.innerText.trim()).join('; ');
                const meta = el.innerText.slice(0, 800);
                return {title, href, authors, meta};
              });
            }"""
        )
        if not data:
            # fallback: any document links on page
            links = page.eval_on_selector_all(
                "a[href*='/document/']",
                "els => els.slice(0,10).map(e => ({href: e.href, text: e.innerText.slice(0,200)}))",
            )
            return {
                "found": bool(links),
                "site": "IEEE",
                "query": title,
                "method": "playwright-search",
                "search_url": search_url,
                "top_links": links,
                "note": "No structured result cards parsed; raw document links returned.",
            }

        top = data[0]
        doc_url = top.get("href")
        detail: dict[str, Any] = {}
        # Visit document page for DOI/abstract if we got a link
        if doc_url and "/document/" in doc_url:
            try:
                page.goto(doc_url, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(2500)
                detail = page.evaluate(
                    """() => {
                      const abs = document.querySelector('.abstract-text, [class*="abstract"]');
                      const doiEl = Array.from(document.querySelectorAll('a')).find(a => a.href.includes('doi.org'));
                      return {
                        pageTitle: document.title,
                        abstract: abs ? abs.innerText.slice(0, 2000) : null,
                        doi: doiEl ? doiEl.href : null,
                        text: document.body ? document.body.innerText.slice(0, 2000) : null,
                      };
                    }"""
                )
            except Exception as e:
                detail = {"detail_error": str(e)}

        return {
            "found": True,
            "site": "IEEE",
            "query": title,
            "method": "playwright-search",
            "search_url": search_url,
            "title_matched": top.get("title"),
            "authors_raw": top.get("authors"),
            "meta_snippet": top.get("meta"),
            "document_url": doc_url,
            "article_number": _extract_art_number(doc_url),
            "doi": detail.get("doi"),
            "abstract": detail.get("abstract"),
            "candidates": data,
        }
    except Exception as e:
        return {"found": False, "site": "IEEE", "query": title, "method": "playwright-search", "search_url": search_url, "error": str(e)}
    finally:
        page.close()


def resolve_oa_pdf(title: str, client: httpx.Client | None = None) -> dict[str, Any]:
    """Ask OpenAlex for an OA PDF for an IEEE paper (legal open copy)."""
    close = False
    if client is None:
        client = httpx.Client(headers=API_HEADERS, timeout=30.0, follow_redirects=True)
        close = True
    try:
        r = api_get(client, "https://api.openalex.org/works",
                    params={"search": title, "per-page": 1, "mailto": CONTACT_EMAIL})
        r.raise_for_status()
        results = r.json().get("results", [])
        if not results:
            return {"pdf_url": None, "landing_page_url": None}
        best = results[0].get("best_oa_location") or {}
        sim = title_similarity(title, results[0].get("title"))
        if sim < 0.6:
            # OA candidate is a different paper — don't attach its PDF.
            return {
                "pdf_url": None,
                "landing_page_url": None,
                "openalex_id": results[0].get("id"),
                "oa_title_similarity": round(sim, 3),
                "note": f"OA match too fuzzy (sim={sim:.2f}); PDF withheld.",
            }
        return {
            "pdf_url": best.get("pdf_url"),
            "landing_page_url": best.get("landing_page_url"),
            "openalex_id": results[0].get("id"),
            "doi": results[0].get("doi"),
            "oa_title_similarity": round(sim, 3),
        }
    except Exception as e:
        return {"pdf_url": None, "error": str(e)}
    finally:
        if close:
            client.close()


def fetch(paper: dict[str, Any], httpx_client=None, pw_context=None) -> dict[str, Any]:
    if pw_context is None:
        # No browser: still try OA resolution so runner can save something
        oa = resolve_oa_pdf(paper.get("paper_name", ""), client=httpx_client)
        return {
            "found": bool(oa.get("pdf_url") or oa.get("landing_page_url")),
            "site": "IEEE",
            "query": paper.get("paper_name", ""),
            "method": "oa-only (no browser)",
            "pdf_url": oa.get("pdf_url"),
            "landing_page_url": oa.get("landing_page_url"),
            "note": "Pass a Playwright context for full IEEE metadata scrape.",
            **oa,
        }
    meta = fetch_via_playwright(paper, pw_context)
    oa = resolve_oa_pdf(paper.get("paper_name", ""), client=httpx_client)
    meta["pdf_url"] = oa.get("pdf_url")  # legal OA copy, not IEEE paywalled PDF
    meta["oa_landing_page_url"] = oa.get("landing_page_url")
    if not meta.get("doi") and oa.get("doi"):
        meta["doi"] = oa["doi"]
    return meta
