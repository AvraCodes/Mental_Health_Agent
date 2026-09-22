"""One-off: rebuild combined _manifest.json from all per-paper JSONs."""

import collections
import glob
import json
from datetime import datetime, timezone
from pathlib import Path

OUT = Path("data/papers_raw")

recs = []
for jf in sorted(glob.glob(str(OUT / "[0-9]*.json"))):
    r = json.load(open(jf, encoding="utf-8"))
    f = r.get("fetched") or {}
    recs.append(
        {
            "id": r.get("id"),
            "site": r.get("site"),
            "title": (r.get("original") or {}).get("paper_name"),
            "found": bool(f.get("found")),
            "method": f.get("method"),
            "doi": f.get("doi"),
            "confidence": f.get("match_confidence"),
            "pdf_file": r.get("pdf_file"),
            "json_file": Path(jf).name,
        }
    )

by_site = collections.Counter()
found_site = collections.Counter()
pdf_site = collections.Counter()
for x in recs:
    by_site[x["site"]] += 1
    if x["found"]:
        found_site[x["site"]] += 1
    if x["pdf_file"]:
        pdf_site[x["site"]] += 1

print("=== PER-SITE ===")
for s in sorted(by_site):
    print(f"{s}: {found_site[s]}/{by_site[s]} found, {pdf_site[s]} pdfs")
print("TOTAL:", len(recs), "found:", sum(found_site.values()), "pdfs:", sum(pdf_site.values()))
print("=== MISSES ===")
for x in recs:
    if not x["found"]:
        print(f"MISS id={x['id']} [{x['site']}] {(x['title'] or '')[:65]}")

man = {
    "scraped_at": datetime.now(timezone.utc).isoformat(),
    "total": len(recs),
    "found": sum(found_site.values()),
    "pdfs": sum(pdf_site.values()),
    "by_site": {
        s: {"total": by_site[s], "found": found_site[s], "pdfs": pdf_site[s]} for s in by_site
    },
    "papers": recs,
}
(OUT / "_manifest.json").write_text(json.dumps(man, indent=2, ensure_ascii=False), encoding="utf-8")
print("manifest written")
