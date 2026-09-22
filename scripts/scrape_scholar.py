"""
Scrape mental-health papers from Google Scholar (Playwright) into data/papers_raw/.

Usage:
    python scripts/scrape_scholar.py                                      # default MH queries, 10 each
    python scripts/scrape_scholar.py --query "mental health chatbot" --per-query 5
    python scripts/scrape_scholar.py --query "stress detection" --query "depression NLP" --per-query 10
    python scripts/scrape_scholar.py --skip-pdf                            # metadata JSON only
    python scripts/scrape_scholar.py --no-headless                         # watch the browser

Output (data/papers_raw/):
    sch_001_<slug>.json   enriched record {query, title, authors, venue, year, cited_by, pdf info}
    sch_001_<slug>.pdf    downloaded side-link PDF (when reachable + verified)
    _scholar_manifest.json  run summary

Notes:
  - Scholar rate-limits bots hard. The runner uses polite delays (default 8s),
    stops gracefully on a block page, and records what it got.
  - If you get blocked immediately, wait a few hours or run from a
    residential network / with --no-headless and solve the CAPTCHA once.

Requires: pip install -r backend/requirements.txt ; playwright install chromium
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.scrapers import scholar as s_scholar
from scripts.scrapers.base import (
    download_pdf,
    get_browser,
    new_context,
    pdf_matches_title,
    safe_unlink,
    slugify,
)

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "data" / "papers_raw"

DEFAULT_QUERIES = [
    "mental health chatbot",
    "stress detection machine learning",
    "depression detection natural language processing",
    "large language models mental health",
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Scrape Google Scholar -> data/papers_raw/")
    p.add_argument("--query", action="append", default=None,
                   help="Search query (repeatable). Defaults to built-in MH queries.")
    p.add_argument("--per-query", type=int, default=10, help="Max results per query")
    p.add_argument("--delay", type=float, default=8.0, help="Delay between queries/pages (s)")
    p.add_argument("--skip-pdf", action="store_true", help="Don't download PDFs")
    p.add_argument("--headless", dest="headless", action="store_true", default=True)
    p.add_argument("--no-headless", dest="headless", action="store_false")
    p.add_argument("--timeout", type=float, default=30.0, help="HTTP timeout (s)")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    queries = args.query or DEFAULT_QUERIES
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # continue numbering past existing sch_ files
    existing = sorted(OUT_DIR.glob("sch_*.json"))
    counter = 0
    for f in existing:
        try:
            counter = max(counter, int(f.name.split("_")[1]))
        except (ValueError, IndexError):
            pass

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("ERROR: playwright not installed. Run: pip install playwright && playwright install chromium")
        return 1

    manifest: list[dict] = []
    stats = {"queries": 0, "results": 0, "pdfs": 0, "blocked": False}

    with sync_playwright() as pw:
        browser = get_browser(pw, headless=args.headless)
        ctx = new_context(browser)
        try:
            for qi, q in enumerate(queries, 1):
                print(f"\n[{qi}/{len(queries)}] query={q!r} ...")
                res = s_scholar.search(q, ctx, max_results=args.per_query)
                stats["queries"] += 1
                if res.get("blocked"):
                    print("    !! Scholar block page (unusual-traffic/CAPTCHA). Stopping.")
                    stats["blocked"] = True
                    break
                if res.get("error"):
                    print(f"    !! {res['error']}")
                    continue
                print(f"    -> {len(res['results'])} results")
                for r in res["results"]:
                    counter += 1
                    stem = f"sch_{counter:03d}_{slugify(r.get('title') or 'untitled')}"
                    record = {
                        "id": f"sch-{counter:03d}",
                        "original": {"paper_name": r.get("title"), "site": "GoogleScholar"},
                        "site": "GoogleScholar",
                        "query": q,
                        "scraped_at": datetime.now(timezone.utc).isoformat(),
                        "fetched": {
                            "found": bool(r.get("title")),
                            "site": "GoogleScholar",
                            "method": "playwright-search",
                            "query": q,
                            "title_matched": r.get("title"),
                            "authors": r.get("authors"),
                            "year": r.get("year"),
                            "venue": r.get("venue"),
                            "cited_by": r.get("cited_by"),
                            "landing_page_url": r.get("url"),
                            "snippet": r.get("snippet"),
                            "pdf_url": r.get("pdf_url"),
                        },
                        "pdf_file": None,
                        "pdf_url": r.get("pdf_url"),
                    }
                    if r.get("pdf_url") and not args.skip_pdf:
                        pdf_path = OUT_DIR / f"{stem}.pdf"
                        print(f"    [pdf] trying {r['pdf_url'][:80]}...")
                        if download_pdf(r["pdf_url"], pdf_path, timeout=int(args.timeout)) and pdf_matches_title(
                            pdf_path, r.get("title") or "",
                            year=r.get("year"),
                        ):
                            print(f"    [pdf] saved {pdf_path.name} ({pdf_path.stat().st_size // 1024} KB)")
                            record["pdf_file"] = pdf_path.name
                            record["pdf_verified"] = True
                            stats["pdfs"] += 1
                        else:
                            if pdf_path.exists():
                                safe_unlink(pdf_path)
                            print("    [pdf] unavailable / unverified")
                    (OUT_DIR / f"{stem}.json").write_text(
                        json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
                    manifest.append({
                        "id": record["id"], "site": "GoogleScholar", "query": q,
                        "title": r.get("title"), "year": r.get("year"),
                        "cited_by": r.get("cited_by"), "pdf_file": record["pdf_file"],
                    })
                    stats["results"] += 1
                time.sleep(args.delay)
        finally:
            ctx.close()
            browser.close()

    (OUT_DIR / "_scholar_manifest.json").write_text(json.dumps({
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "queries": queries,
        **stats,
        "papers": manifest,
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nDone. queries={stats['queries']} results={stats['results']} pdfs={stats['pdfs']} "
          f"blocked={stats['blocked']} -> {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
