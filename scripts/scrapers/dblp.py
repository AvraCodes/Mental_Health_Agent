"""DBLP scraper.

Primary: DBLP JSON API (https://dblp.org/search/publ/api?q=...&format=json).
Fallback: Playwright scrape of https://dblp.org/search?q=...
"""

from __future__ import annotations

import urllib.parse
from typing import Any

import httpx

from .base import API_HEADERS

API_URL = "https://dblp.org/search/publ/api"


def _as_list(x):
    if x is None:
        return []
    return x if isinstance(x, list) else [x]


def fetch_via_api(paper: dict[str, Any], client: httpx.Client | None = None) -> dict[str, Any]:
    title = paper.get("paper_name", "")
    params = {"q": title, "format": "json", "h": 5}
    close = False
    if client is None:
        client = httpx.Client(headers=API_HEADERS, timeout=30.0, follow_redirects=True)
        close = True
    try:
        r = client.get(API_URL, params=params)
        r.raise_for_status()
        hits = r.json().get("result", {}).get("hits", {}).get("hit", [])
        if not hits:
            return {"found": False, "site": "DBLP", "query": title}
        info = hits[0].get("info", {})
        authors = [a for a in _as_list((info.get("authors") or {}).get("author"))]
        ee = info.get("ee")
        if isinstance(ee, list):
            ee_links = ee
            ee_first = ee[0] if ee else None
        else:
            ee_links = [ee] if ee else []
            ee_first = ee
        return {
            "found": True,
            "site": "DBLP",
            "query": title,
            "method": "api",
            "dblp_key": info.get("key"),
            "title_matched": info.get("title"),
            "authors": authors,
            "year": int(info["year"]) if str(info.get("year", "")).isdigit() else info.get("year"),
            "venue": info.get("venue"),
            "doi": info.get("doi"),
            "doi_url": f"https://doi.org/{info.get('doi')}" if info.get("doi") else None,
            "ee": ee_first,
            "ee_links": ee_links,
            "dblp_url": info.get("url"),
            "pdf_url": next((u for u in ee_links if u and u.lower().endswith(".pdf")), None),
            "landing_page_url": ee_first or info.get("url"),
            "raw": info,
        }
    except Exception as e:
        return {"found": False, "site": "DBLP", "query": title, "method": "api", "error": str(e)}
    finally:
        if close:
            client.close()


def _challenge_present(page) -> bool:
    try:
        title = page.title().lower()
        if "not a bot" in title or "just a moment" in title or "attention required" in title:
            return True
        body = page.evaluate("() => document.body ? document.body.innerText.slice(0, 500) : ''").lower()
        return "not a bot" in body and ("anubis" in body or "calculating" in body)
    except Exception:
        return False


def _parse_results(page) -> tuple[list, list]:
    try:
        hits = page.eval_on_selector_all(
            "li.entry, div.entry",
            "els => els.slice(0,5).map(e => e.innerText.slice(0,500))",
        )
    except Exception:
        hits = []
    try:
        links = page.eval_on_selector_all(
            "li.entry a[href*='doi.org'], li.entry a[href*='ee']",
            "els => els.slice(0,5).map(e => e.href)",
        )
    except Exception:
        links = []
    return hits, links


def _wait_past_challenge(page) -> None:
    for _ in range(15):
        page.wait_for_timeout(5000)
        if not _challenge_present(page):
            break
        print("    [dblp] Anubis challenge solving, waiting...")
    page.wait_for_timeout(3000)


def fetch_via_playwright(paper: dict[str, Any], context) -> dict[str, Any]:
    title = paper.get("paper_name", "")
    queries = [title]
    # fallback: DBLP requires most tokens to match — retry with lead words
    short = " ".join(title.split()[:8])
    if short and short != title:
        queries.append(short)
    page = context.new_page()
    try:
        hits: list = []
        links: list = []
        used_q = queries[0]
        blocked = False
        for q in queries:
            url = f"https://dblp.org/search?q={urllib.parse.quote(q)}"
            page.goto(url, wait_until="domcontentloaded", timeout=45000)
            _wait_past_challenge(page)
            hits, links = _parse_results(page)
            used_q = q
            if hits:
                break
            blocked = _challenge_present(page)
            if blocked:
                break  # wall never cleared — a shorter query won't help
        result = {
            "found": bool(hits),
            "site": "DBLP",
            "query": title,
            "method": "playwright",
            "search_url": f"https://dblp.org/search?q={urllib.parse.quote(used_q)}",
            "top_hits": hits,
            "top_links": links,
        }
        if used_q != title:
            result["short_query_used"] = used_q
        if blocked:
            result["blocked"] = "Anubis challenge did not clear within ~75s"
        return result
    except Exception as e:
        return {"found": False, "site": "DBLP", "query": title, "method": "playwright", "error": str(e)}
    finally:
        page.close()


def fetch(paper: dict[str, Any], httpx_client=None, pw_context=None) -> dict[str, Any]:
    # NOTE: dblp.org API is behind a bot challenge ("Making sure you're not
    # a bot") for datacenter IPs, so when a browser is available we go
    # Playwright-first and use the API only as enrichment/fallback.
    if pw_context is not None:
        pw_result = fetch_via_playwright(paper, pw_context)
        if pw_result.get("found"):
            # Try to enrich with API metadata (may fail on bot-wall; ignore).
            try:
                api_result = fetch_via_api(paper, client=httpx_client)
                if api_result.get("found"):
                    pw_result["api_enrichment"] = api_result
                    for k in ("doi", "doi_url", "dblp_key", "ee", "ee_links"):
                        if not pw_result.get(k) and api_result.get(k):
                            pw_result[k] = api_result[k]
                    if not pw_result.get("pdf_url") and api_result.get("pdf_url"):
                        pw_result["pdf_url"] = api_result["pdf_url"]
            except Exception:
                pass
            return pw_result
        # Playwright missed -> still try API for completeness
        api_result = fetch_via_api(paper, client=httpx_client)
        if api_result.get("found"):
            return api_result
        api_result["playwright_fallback"] = pw_result
        return api_result
    return fetch_via_api(paper, client=httpx_client)
