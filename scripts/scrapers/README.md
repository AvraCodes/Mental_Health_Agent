# Paper scrapers — relevant_papers.json → data/papers_raw/

Playwright + API hybrid scrapers, one per `site` value in `relevant_papers.json`
(60 papers: 44 OpenAlex, 6 DBLP, 6 IEEE, 4 Crossref).

## Install

```bash
pip install -r backend/requirements.txt
playwright install chromium
```

## Run

```bash
# Full run: metadata JSON + OA PDFs for all 60 papers
python scripts/scrape_papers.py

# Common filters
python scripts/scrape_papers.py --site OpenAlex --limit 5
python scripts/scrape_papers.py --site IEEE --limit 2        # browser path
python scripts/scrape_papers.py --site DBLP --limit 2        # browser path
python scripts/scrape_papers.py --id 8
python scripts/scrape_papers.py --no-browser                 # API-only, fastest
python scripts/scrape_papers.py --skip-pdf                   # metadata JSON only
python scripts/scrape_papers.py --no-headless                # watch the browser
```

## How each site is scraped

| site | primary | fallback | notes |
|---|---|---|---|
| OpenAlex | REST API (`api.openalex.org/works?search=`) | Playwright on `openalex.org/works?search=` | saves `best_oa_location.pdf_url` + tries alternate OA copies |
| Crossref | REST API (`api.crossref.org/works?query.title=`) | Playwright on `search.crossref.org` | `mailto` param + 429 retry; saves publisher PDF link when open |
| DBLP | **Playwright** on `dblp.org/search?q=` | REST API enrich | API is bot-walled over httpx, so browser goes first |
| IEEE | **Playwright** on IEEE Xplore search + doc page | OA PDF via OpenAlex | IEEE PDFs are paywalled — only legal OA copies are downloaded |

## Output — data/papers_raw/

- `003_<slug>.json` — `{original, site, scraped_at, fetched, pdf_file, pdf_url}`
- `003_<slug>.pdf` — downloaded OA PDF (when reachable; 403/paywalled hosts are skipped honestly)
- `_manifest.json` — run summary `{total, ok, miss, pdf, papers[]}`

Feed PDFs into the existing RAG pipeline:

```bash
# ingest_papers.py currently globs *.pdf in repo root —
# either copy data/papers_raw/*.pdf there or point it at the folder.
python scripts/ingest_papers.py
```

## Honest limitations

- Several `DBLP` / `Crossref` / `IEEE` titles in `relevant_papers.json` look
  synthetic (no exact match on the live site) — those correctly record
  `found: false` or a nearest-match with `title_matched` for audit.
- Publisher hosts (SAGE, IEEE, PMC render pages) often 403 direct PDF fetch —
  metadata JSON is still saved with `doi` + `landing_page_url`.
- Keep `--delay >= 2` (default 2.0s) and don't hammer the APIs or you'll get 429s.
