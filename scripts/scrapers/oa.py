"""Extra open-access PDF sources used as last resort when a record has no
verified PDF yet.

- Semantic Scholar Graph API (no key; polite anonymous pool, backs off on 429).
- (Unpaywall intentionally omitted: it rejects placeholder emails with 422.
  Pass a real contact email to enable it — see README.)

Every candidate is guarded by title-similarity + year before use.
"""

from __future__ import annotations

from typing import Any

import httpx

from .base import API_HEADERS, api_get, match_confidence, title_similarity

S2_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
ARXIV_URL = "https://export.arxiv.org/api/query"

# ISSN -> mdpi-res.com asset slug (www.mdpi.com is Akamai-walled; the
# mdpi-res.com CDN serves the same CC-BY PDFs without the wall).
MDPI_ISSN_SLUG = {
    "2078-2489": "information",
    "2227-9032": "healthcare",
    "2076-3425": "brainsci",
    "2227-7102": "educsci",
    "2673-7426": "biomedinformatics",
    "1661-7827": "ijerph",
    "1424-8220": "sensors",
    "2076-3417": "applsci",
    "2077-0383": "jcm",
    "2072-6643": "nutrients",
    "1660-4601": "ijerph",
    "2073-4409": "cancers",
    "2227-7390": "mathematics",
    "2075-4418": "diagnostics",
    "1661-6596": "ijms",
    "1999-4923": "pharmaceutics",
    "2079-9292": "electronics",
    "2071-1050": "sustainability",
    "2306-5361": "diseases",
    "2036-7422": "clinpract",
    "2673-2688": "healthcare",
}


def mdpi_res_url(www_url: str, doi: str | None = None) -> str | None:
    """Translate a blocked www.mdpi.com PDF URL to its mdpi-res.com mirror.

    www:  https://www.mdpi.com/2078-2489/15/12/768/pdf?version=...
    mirror: https://mdpi-res.com/d_attachment/information/information-15-00768/article_deploy/information-15-00768.pdf
    """
    import re

    m = re.search(r"mdpi\.com/(\d{4}-\d{3}[\dX])/(\d+)/(\d+)/(\d+)", www_url)
    if not m:
        return None
    issn, vol, _issue, art = m.groups()
    slug = MDPI_ISSN_SLUG.get(issn)
    if not slug and doi:
        code = re.search(r"10\.3390/([a-z0-9]+)", str(doi).lower())
        if code:
            slug = code.group(1)
    if not slug:
        return None
    stem = f"{slug}-{vol}-{art.zfill(5)}"
    return f"https://mdpi-res.com/d_attachment/{slug}/{stem}/article_deploy/{stem}.pdf"


def arxiv_pdf(title: str, year: int | str | None = None) -> dict[str, Any]:
    """Look up an arXiv preprint by title (free API, no key)."""
    import re
    import urllib.parse
    import xml.etree.ElementTree as ET

    try:
        q = urllib.parse.quote(f'ti:"{title}"')
        url = f"{ARXIV_URL}?search_query={q}&max_results=5"
        r = httpx.get(url, headers={"User-Agent": API_HEADERS["User-Agent"]}, timeout=30.0)
        r.raise_for_status()
        ns = {"a": "http://www.w3.org/2005/Atom"}
        cands = []
        for entry in ET.fromstring(r.text).findall("a:entry", ns):
            t = (entry.findtext("a:title", default="") or "").replace("\n", " ").strip()
            t = re.sub(r"\s+", " ", t)
            sim = title_similarity(title, t)
            pub = entry.findtext("a:published", default="")[:4]
            arxiv_id = (entry.findtext("a:id", default="") or "").strip().rstrip("/")
            cands.append((sim, t, pub, arxiv_id))
        if not cands:
            return {"pdf_url": None, "method": "arxiv"}
        cands.sort(reverse=True)
        sim, t, pub, aid = cands[0]
        conf = match_confidence(sim)
        try:
            exp = int(year or 0)
            if exp and pub.isdigit() and abs(exp - int(pub)) > 2:
                conf = "low"
        except (TypeError, ValueError):
            pass
        pdf = aid.replace("/abs/", "/pdf/") + ".pdf" if "/abs/" in aid else None
        return {
            "pdf_url": pdf if conf != "low" else None,
            "method": "arxiv",
            "title_matched": t,
            "title_similarity": round(sim, 3),
            "match_confidence": conf,
            "year": pub,
        }
    except Exception as e:
        return {"pdf_url": None, "method": "arxiv", "error": str(e)[:200]}


def semanticscholar_pdf(
    title: str, year: int | str | None = None, client: httpx.Client | None = None
) -> dict[str, Any]:
    close = False
    if client is None:
        client = httpx.Client(headers=API_HEADERS, timeout=30.0, follow_redirects=True)
        close = True
    try:
        try:
            r = api_get(
                client,
                S2_URL,
                params={
                    "query": title,
                    "limit": 5,
                    "fields": "title,openAccessPdf,externalIds,authors,year,url",
                },
                retries=2,
                backoff=3.0,
            )
        except RuntimeError as e:
            return {"pdf_url": None, "method": "semanticscholar", "note": str(e)[:120]}
        r.raise_for_status()
        papers = r.json().get("data", [])
        if not papers:
            return {"pdf_url": None, "method": "semanticscholar"}
        ranked = sorted(papers, key=lambda w: title_similarity(title, w.get("title")), reverse=True)
        w = ranked[0]
        sim = title_similarity(title, w.get("title"))
        conf = match_confidence(sim)
        try:
            exp = int(year or 0)
            got = int(w.get("year") or 0)
            if exp and got and abs(exp - got) > 2:
                conf = "low"
        except (TypeError, ValueError):
            pass
        oa = w.get("openAccessPdf") or {}
        ext = w.get("externalIds") or {}
        return {
            "pdf_url": oa.get("url") if conf != "low" else None,
            "method": "semanticscholar",
            "title_matched": w.get("title"),
            "title_similarity": round(sim, 3),
            "match_confidence": conf,
            "year": w.get("year"),
            "doi": f"https://doi.org/{ext['DOI']}" if ext.get("DOI") else None,
            "s2_url": w.get("url"),
        }
    except Exception as e:
        return {"pdf_url": None, "method": "semanticscholar", "error": str(e)[:200]}
    finally:
        if close:
            client.close()
