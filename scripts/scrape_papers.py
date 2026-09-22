"""
Scrape paper metadata (+ OA PDFs where available) for every entry in
relevant_papers.json and save to data/papers_raw/.

Strategy per `site` field:
  - OpenAlex / Crossref / DBLP -> fast REST API first, Playwright fallback
    scrapes the site's search page when the API misses.
  - IEEE Xplore -> Playwright-first (no open API key needed); OA PDF is
    resolved legally via OpenAlex. IEEE paywalled PDFs are NOT bypassed.

Usage:
    python scripts/scrape_papers.py                       # scrape all 60
    python scripts/scrape_papers.py --site OpenAlex --limit 5
    python scripts/scrape_papers.py --id 4                 # single paper
    python scripts/scrape_papers.py --no-browser           # API-only, fastest
    python scripts/scrape_papers.py --headless             # default headless
    python scripts/scrape_papers.py --no-headless          # watch browser
    python scripts/scrape_papers.py --skip-pdf             # metadata JSON only

Output (data/papers_raw/):
    003_<slug>.json   enriched record {original + fetched + pdf info}
    003_<slug>.pdf    downloaded OA PDF (when found)
    _manifest.json    run summary

Requires: pip install -r backend/requirements.txt ; playwright install chromium
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.scrapers import openalex as s_openalex
from scripts.scrapers import crossref as s_crossref
from scripts.scrapers import dblp as s_dblp
from scripts.scrapers import ieee as s_ieee
from scripts.scrapers.base import (
    API_HEADERS,
    download_pdf,
    get_browser,
    new_context,
    paper_stem,
    polite_delay,
)

BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_JSON = BASE_DIR / "relevant_papers.json"
OUT_DIR = BASE_DIR / "data" / "papers_raw"

SITE_MODULES = {
    "OpenAlex": s_openalex,
    "Crossref": s_crossref,
    "DBLP": s_dblp,
    "IEEE": s_ieee,
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Scrape relevant_papers.json sites -> data/papers_raw/")
    p.add_argument("--site", default=None, help="Only this site (OpenAlex|Crossref|DBLP|IEEE)")
    p.add_argument("--id", type=int, default=None, help="Only this paper id")
    p.add_argument("--limit", type=int, default=None, help="Max papers to process")
    p.add_argument("--no-browser", action="store_true", help="Skip Playwright; API-only")
    p.add_argument("--headless", dest="headless", action="store_true", default=True)
    p.add_argument("--no-headless", dest="headless", action="store_false")
    p.add_argument("--skip-pdf", action="store_true", help="Don't download PDFs")
    p.add_argument("--delay", type=float, default=2.0, help="Polite delay between papers (s)")
    p.add_argument("--skip-existing", action="store_true",
                   help="Skip papers whose JSON already exists (resume interrupted runs)")
    p.add_argument("--no-fallback", action="store_true",
                   help="Disable Crossref fallback enrichment for site misses")
    p.add_argument("--timeout", type=float, default=30.0, help="HTTP timeout (s)")
    p.add_argument("--retry-pdfs", action="store_true",
                   help="Only retry missing PDFs using stored metadata (no re-scrape)")
    return p.parse_args()


def scrape_one(paper: dict, httpx_client: httpx.Client, pw_context) -> dict:
    site = paper.get("site", "OpenAlex")
    mod = SITE_MODULES.get(site)
    if mod is None:
        return {"found": False, "site": site, "query": paper.get("paper_name"), "error": f"Unknown site {site!r}"}
    try:
        return mod.fetch(paper, httpx_client=httpx_client, pw_context=pw_context)
    except Exception as e:
        return {"found": False, "site": site, "query": paper.get("paper_name"), "error": str(e)}


def download_pdfs(args, http_client, paper, fetched, found, record, stem, json_path, stats) -> None:
    """Try every PDF source for one record (mutates record/stats in place).

    Order: stored candidates -> Semantic Scholar last resort. Every file is
    content-verified before it counts.
    """
    from scripts.scrapers.base import pdf_matches_title, safe_unlink

    def _matches(path, doi=None) -> bool:
        return pdf_matches_title(
            path,
            paper.get("paper_name", ""),
            doi=doi or fetched.get("doi"),
            authors=fetched.get("authors"),
            year=paper.get("year"),
        )

    # PDF download (OA only — try every candidate in order).
    # Skip PDFs on low-confidence title matches to avoid filing
    # the wrong paper's PDF under this id.
    candidates = fetched.get("pdf_candidates") or (
        [fetched["pdf_url"]] if fetched.get("pdf_url") else []
    )
    if fetched.get("match_confidence") == "low":
        print(f"    [pdf] skipped: low title-match confidence "
              f"(sim={fetched.get('title_similarity')}, matched={str(fetched.get('title_matched'))[:60]!r})")
        candidates = []
    # MDPI mirror expansion: www.mdpi.com 403s bots, mdpi-res.com serves
    # the same CC-BY PDFs without the wall.
    if candidates:
        from scripts.scrapers.oa import mdpi_res_url

        expanded: list[str] = []
        for u in candidates:
            expanded.append(u)
            if "mdpi.com/" in u and "mdpi-res.com" not in u:
                m = mdpi_res_url(u, fetched.get("doi"))
                if m and m not in expanded:
                    expanded.append(m)
                    print(f"    [pdf] + MDPI mirror candidate")
        candidates = expanded
    if found and not args.skip_pdf and candidates:
        pdf_path = OUT_DIR / f"{stem}.pdf"
        if pdf_path.exists() and pdf_path.stat().st_size > 5_000:
            # trust a previous verified run; otherwise (re)verify once
            prev_verified = False
            if json_path.exists():
                try:
                    prev = json.loads(json_path.read_text(encoding="utf-8"))
                    prev_verified = bool(prev.get("pdf_verified")) and prev.get("pdf_file") == pdf_path.name
                except Exception:
                    pass
            if prev_verified:
                print(f"    [pdf] already exists, verified earlier")
                record["pdf_file"] = pdf_path.name
                record["pdf_verified"] = True
                stats["pdf"] += 1
                candidates = []
            elif _matches(pdf_path):
                print(f"    [pdf] already exists, verified")
                record["pdf_file"] = pdf_path.name
                record["pdf_verified"] = True
                stats["pdf"] += 1
                candidates = []
            else:
                print(f"    [pdf] existing file FAILED content check (wrong paper?) — redownloading")
                safe_unlink(pdf_path)
        if candidates and record.get("pdf_file") is None:
            saved = False
            for url in candidates:
                print(f"    [pdf] trying {url[:90]}...")
                if download_pdf(url, pdf_path) and _matches(pdf_path):
                    print(f"    [pdf] saved {pdf_path.name} ({pdf_path.stat().st_size // 1024} KB, verified)")
                    record["pdf_file"] = pdf_path.name
                    record["pdf_url"] = url
                    record["pdf_verified"] = True
                    stats["pdf"] += 1
                    saved = True
                    break
                elif pdf_path.exists():
                    print(f"    [pdf] content mismatch (wrong paper?) — trying next source")
                    safe_unlink(pdf_path)
            if not saved:
                print("    [pdf] unavailable (paywalled, blocked, or no verified copy)")
                record["pdf_url"] = candidates[0]

    # Last resort: Semantic Scholar OA lookup (independent index —
    # runs even when the site match was low-confidence or paywalled).
    if found and not args.skip_pdf and record.get("pdf_file") is None:
        from scripts.scrapers.oa import semanticscholar_pdf

        s2 = semanticscholar_pdf(
            paper.get("paper_name", ""), paper.get("year"), client=http_client
        )
        if s2.get("pdf_url"):
            print(f"    [pdf] trying Semantic Scholar copy...")
            _pdf_path = OUT_DIR / f"{stem}.pdf"
            if download_pdf(s2["pdf_url"], _pdf_path) and pdf_matches_title(
                _pdf_path,
                paper.get("paper_name", ""),
                doi=s2.get("doi") or fetched.get("doi"),
                year=paper.get("year"),
            ):
                print(f"    [pdf] saved {_pdf_path.name} via Semantic Scholar "
                      f"({_pdf_path.stat().st_size // 1024} KB, verified)")
                record["pdf_file"] = _pdf_path.name
                record["pdf_url"] = s2["pdf_url"]
                record["pdf_source"] = "semanticscholar"
                record["pdf_verified"] = True
                stats["pdf"] += 1
            else:
                if _pdf_path.exists():
                    safe_unlink(_pdf_path)
                print("    [pdf] Semantic Scholar copy unusable "
                      f"(matched={str(s2.get('title_matched'))[:60]!r})")
                record.setdefault("s2_attempt", s2)
        elif s2.get("error") or s2.get("note"):
            record.setdefault("s2_attempt", s2)

    # Final resort: arXiv preprint (free API, usually same work).
    if found and not args.skip_pdf and record.get("pdf_file") is None:
        from scripts.scrapers.oa import arxiv_pdf

        ax = arxiv_pdf(paper.get("paper_name", ""), paper.get("year"))
        if ax.get("pdf_url"):
            print(f"    [pdf] trying arXiv copy...")
            _ax_path = OUT_DIR / f"{stem}.pdf"
            if download_pdf(ax["pdf_url"], _ax_path) and _matches(_ax_path, doi=None):
                print(f"    [pdf] saved {_ax_path.name} via arXiv "
                      f"({_ax_path.stat().st_size // 1024} KB, verified)")
                record["pdf_file"] = _ax_path.name
                record["pdf_url"] = ax["pdf_url"]
                record["pdf_source"] = "arxiv"
                record["pdf_verified"] = True
                stats["pdf"] += 1
            else:
                if _ax_path.exists():
                    safe_unlink(_ax_path)
                print("    [pdf] arXiv copy unusable "
                      f"(matched={str(ax.get('title_matched'))[:60]!r})")
                record.setdefault("arxiv_attempt", ax)
        elif ax.get("error"):
            record.setdefault("arxiv_attempt", ax)


def main() -> int:
    args = parse_args()

    if not INPUT_JSON.exists():
        print(f"ERROR: {INPUT_JSON} not found")
        return 1
    papers = json.loads(INPUT_JSON.read_text(encoding="utf-8"))
    print(f"Loaded {len(papers)} papers from {INPUT_JSON.name}")

    if args.site:
        papers = [p for p in papers if p.get("site") == args.site]
    if args.id is not None:
        papers = [p for p in papers if p.get("id") == args.id]
    if args.limit is not None:
        papers = papers[: args.limit]
    if not papers:
        print("Nothing to do (filter matched 0 papers).")
        return 0

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Output dir: {OUT_DIR}")
    print(f"Browser: {'disabled (--no-browser)' if args.no_browser else ('headless' if args.headless else 'headed')}")

    manifest: list[dict] = []
    stats = {"ok": 0, "miss": 0, "pdf": 0}

    # Single shared HTTP client + single shared browser (efficient)
    with httpx.Client(headers=API_HEADERS, timeout=args.timeout, follow_redirects=True) as http_client:
        pw = browser = pw_context = None
        if not args.no_browser:
            try:
                from playwright.sync_api import sync_playwright
            except ImportError:
                print("ERROR: playwright not installed. Run: pip install playwright && playwright install chromium")
                print("...continuing in API-only mode.")
                args.no_browser = True
            else:
                pw = sync_playwright().start()
                browser = get_browser(pw, headless=args.headless)
                pw_context = new_context(browser)

        try:
            for i, paper in enumerate(papers, 1):
                pid = paper.get("id")
                site = paper.get("site")
                title = paper.get("paper_name", "")[:80]
                stem = paper_stem(paper)
                json_path = OUT_DIR / f"{stem}.json"

                if args.skip_existing and json_path.exists():
                    try:
                        rec = json.loads(json_path.read_text(encoding="utf-8"))
                        print(f"[{i}/{len(papers)}] id={pid} [{site}] {title}... [skip] already scraped")
                        manifest.append({
                            "id": pid, "site": site,
                            "title": paper.get("paper_name"),
                            "found": bool((rec.get("fetched") or {}).get("found")),
                            "method": (rec.get("fetched") or {}).get("method"),
                            "doi": (rec.get("fetched") or {}).get("doi"),
                            "pdf_file": rec.get("pdf_file"),
                            "json_file": json_path.name,
                        })
                        stats["ok" if manifest[-1]["found"] else "miss"] += 1
                        if rec.get("pdf_file"):
                            stats["pdf"] += 1
                        continue
                    except Exception:
                        pass  # corrupt file — rescrape below

                if args.retry_pdfs and json_path.exists():
                    # PDF-only pass: reuse stored metadata, no re-scrape.
                    try:
                        _rec = json.loads(json_path.read_text(encoding="utf-8"))
                        _pdf = _rec.get("pdf_file")
                        if _pdf and (OUT_DIR / _pdf).exists():
                            print(f"[{i}/{len(papers)}] id={pid} [{site}] {title}... [pdf already saved]")
                            manifest.append({
                                "id": pid, "site": site,
                                "title": paper.get("paper_name"),
                                "found": True,
                                "method": (_rec.get("fetched") or {}).get("method"),
                                "doi": (_rec.get("fetched") or {}).get("doi"),
                                "pdf_file": _pdf,
                                "json_file": json_path.name,
                            })
                            stats["ok"] += 1
                            stats["pdf"] += 1
                            continue
                        _fetched = _rec.get("fetched") or {}
                        if not _fetched.get("found"):
                            print(f"[{i}/{len(papers)}] id={pid} [{site}] {title}... [no metadata, nothing to retry]")
                            manifest.append({
                                "id": pid, "site": site,
                                "title": paper.get("paper_name"),
                                "found": False,
                                "method": _fetched.get("method"),
                                "doi": _fetched.get("doi"),
                                "pdf_file": None,
                                "json_file": json_path.name,
                            })
                            stats["miss"] += 1
                            continue
                        print(f"\n[{i}/{len(papers)}] id={pid} [{site}] {title}... [retry pdfs]")
                        _rec["scraped_at"] = datetime.now(timezone.utc).isoformat()
                        _rec["pdf_file"] = None
                        download_pdfs(args, http_client, paper, _fetched, True,
                                      _rec, stem, json_path, stats)
                        json_path.write_text(json.dumps(_rec, indent=2, ensure_ascii=False), encoding="utf-8")
                        manifest.append({
                            "id": pid, "site": site,
                            "title": paper.get("paper_name"),
                            "found": True,
                            "method": _fetched.get("method"),
                            "doi": _fetched.get("doi"),
                            "pdf_file": _rec.get("pdf_file"),
                            "json_file": json_path.name,
                        })
                        stats["ok"] += 1
                        polite_delay(args.delay)
                        continue
                    except Exception as e:
                        print(f"    [retry-pdfs] {_rec if '_rec' in dir() else ''} failed ({e}), rescraping below")

                print(f"\n[{i}/{len(papers)}] id={pid} [{site}] {title}...")

                fetched = scrape_one(paper, http_client, pw_context)
                found = bool(fetched.get("found"))
                if not found and not args.no_fallback and site != "Crossref":
                    from scripts.scrapers.fallback import crossref_lookup

                    print("    [fallback] site miss — trying Crossref enrichment...")
                    fb = crossref_lookup(paper, client=http_client)
                    if fb.get("found"):
                        print(f"    [fallback] FOUND via crossref-fallback "
                              f"| doi={fb.get('doi')} | sim={fb.get('title_similarity')}")
                        fetched = {**fb, "site": site, "site_miss": fetched}
                        found = True
                    else:
                        print(f"    [fallback] still miss "
                              f"(matched={str(fb.get('title_matched'))[:60]!r}, sim={fb.get('title_similarity')})")
                        fetched["fallback_attempt"] = fb
                print(f"    -> {'FOUND' if found else 'MISS'} via {fetched.get('method')} "
                      f"| doi={fetched.get('doi')} | pdf={'yes' if fetched.get('pdf_url') else 'no'}")
                if fetched.get("error"):
                    print(f"       error: {fetched['error']}")

                stem = paper_stem(paper)  # (recomputed; same stem as above)
                record = {
                    "id": pid,
                    "original": paper,
                    "site": site,
                    "scraped_at": datetime.now(timezone.utc).isoformat(),
                    "fetched": fetched,
                    "pdf_file": None,
                    "pdf_url": fetched.get("pdf_url"),
                }

                download_pdfs(args, http_client, paper, fetched, found, record, stem, json_path, stats)

                json_path = OUT_DIR / f"{stem}.json"
                json_path.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")

                manifest.append({
                    "id": pid, "site": site,
                    "title": paper.get("paper_name"),
                    "found": found,
                    "method": fetched.get("method"),
                    "doi": fetched.get("doi"),
                    "pdf_file": record["pdf_file"],
                    "json_file": json_path.name,
                })
                stats["ok" if found else "miss"] += 1
                polite_delay(args.delay)
        finally:
            if pw_context is not None:
                pw_context.close()
            if browser is not None:
                browser.close()
            if pw is not None:
                pw.stop()

    (OUT_DIR / "_manifest.json").write_text(json.dumps({
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "total": len(papers),
        **stats,
        "papers": manifest,
    }, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\nDone. found={stats['ok']} miss={stats['miss']} pdfs={stats['pdf']} -> {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
