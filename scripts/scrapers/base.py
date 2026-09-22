"""Shared helpers for all site scrapers: filenames, PDF download, Playwright browser."""

from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Any

import httpx

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36 "
    "MentalHealthAgent/1.0 (mailto:research@example.com)"
)

CONTACT_EMAIL = "research@example.com"

API_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "application/json",
}


def api_get(
    client: httpx.Client,
    url: str,
    params: dict | None = None,
    retries: int = 4,
    backoff: float = 5.0,
) -> httpx.Response:
    """GET with retry on 429/5xx. Honors Retry-After when present.

    OpenAlex/Crossref ask for a `mailto` param for the polite pool --
    callers should include it, but we add it defensively too.
    """
    params = dict(params or {})
    if "api.openalex.org" in url or "api.crossref.org" in url:
        params.setdefault("mailto", CONTACT_EMAIL)
    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            r = client.get(url, params=params)
            if r.status_code == 429 or 500 <= r.status_code < 600:
                try:
                    ra = float(r.headers.get("retry-after") or 0)
                except (TypeError, ValueError):
                    ra = 0
                if ra > 120:
                    # server imposed a long ban (e.g. OpenAlex 14h throttle):
                    # fail immediately — retrying a 14h ban is pointless.
                    raise RuntimeError(
                        f"GET {url} rate-limited (retry-after {ra:.0f}s) — "
                        "back off and resume later with --skip-existing"
                    ) from None
                wait = min(backoff * (attempt + 1), 30.0)
                if ra:
                    wait = min(max(wait, ra), 60.0)
                print(f"    [api] {r.status_code} from {url[:60]}... retry in {wait:.0f}s (attempt {attempt + 1}/{retries})")
                time.sleep(wait)
                continue
            r.raise_for_status()
            return r
        except httpx.HTTPStatusError:
            raise
        except RuntimeError:
            # deliberate fail-fast (e.g. long ban) — never retry these
            raise
        except Exception as e:
            last_exc = e
            wait = backoff * (attempt + 1)
            print(f"    [api] error {e} -- retry in {wait:.0f}s (attempt {attempt + 1}/{retries})")
            time.sleep(wait)
    if last_exc is not None:
        raise last_exc
    raise RuntimeError(f"GET {url} failed after {retries} retries")


def slugify(text: str, max_len: int = 60) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text[:max_len].strip("-") or "paper"


def paper_stem(paper: dict[str, Any]) -> str:
    pid = paper.get("id", "noid")
    title = paper.get("paper_name", f"paper-{pid}")
    return f"{pid:03d}_{slugify(title)}" if isinstance(pid, int) else f"{pid}_{slugify(title)}"


def reconstruct_abstract(inverted_index: dict[str, list[int]] | None) -> str:
    """OpenAlex returns abstract as word -> positions. Rebuild plain text."""
    if not inverted_index:
        return ""
    try:
        positions: dict[int, str] = {}
        for word, idxs in inverted_index.items():
            for i in idxs:
                positions[i] = word
        return " ".join(positions[i] for i in sorted(positions))
    except Exception:
        return ""


def normalize_title(t: str | None) -> str:
    t = (t or "").lower()
    t = re.sub(r"[^a-z0-9 ]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def title_similarity(a: str | None, b: str | None) -> float:
    """0..1 similarity between two titles (difflib on normalized text)."""
    from difflib import SequenceMatcher

    na, nb = normalize_title(a), normalize_title(b)
    if not na or not nb:
        return 0.0
    return SequenceMatcher(None, na, nb).ratio()


def match_confidence(score: float) -> str:
    if score >= 0.85:
        return "high"
    if score >= 0.6:
        return "medium"
    return "low"


def safe_unlink(path: Path, retries: int = 3, delay: float = 0.5) -> None:
    """Unlink with retries — Windows AV/file locks can hold a fresh file briefly."""
    for i in range(retries):
        try:
            path.unlink(missing_ok=True)
            return
        except OSError:
            if i == retries - 1:
                return
            time.sleep(delay)


BROWSER_DL_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "application/pdf,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
}


def _fetch_pdf_bytes(pdf_url: str, dest: Path, timeout: int, referer: str | None) -> None:
    headers = dict(BROWSER_DL_HEADERS)
    if referer:
        headers["Referer"] = referer
        headers["Sec-Fetch-Site"] = "same-origin"
    with httpx.stream("GET", pdf_url, headers=headers, timeout=timeout, follow_redirects=True) as r:
        r.raise_for_status()
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "wb") as f:
            for chunk in r.iter_bytes(chunk_size=65536):
                f.write(chunk)


def download_pdf(pdf_url: str, dest: Path, timeout: int = 60) -> bool:
    """Stream a PDF to dest. Retries 403s with a Referer header. Returns True on success."""
    try:
        try:
            _fetch_pdf_bytes(pdf_url, dest, timeout, referer=None)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                print(f"    [pdf] 403, retrying with Referer...")
                _fetch_pdf_bytes(pdf_url, dest, timeout, referer="https://scholar.google.com/")
            else:
                raise
        # sanity: must look like a PDF and be > 5KB
        if dest.stat().st_size < 5_000:
            safe_unlink(dest)
            return False
        with open(dest, "rb") as f:
            if not f.read(5).startswith(b"%PDF"):
                # some OA hosts serve PDF without %PDF magic (e.g. arxiv html?) - keep if large
                if dest.stat().st_size < 50_000:
                    safe_unlink(dest)
                    return False
        return True
    except Exception as e:
        print(f"    [pdf] failed {pdf_url[:80]}: {e}")
        safe_unlink(dest)
        return False


def get_browser(playwright, headless: bool = True):
    """Launch a Chromium browser tuned to avoid bot detection."""
    browser = playwright.chromium.launch(
        headless=headless,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-dev-shm-usage",
        ],
    )
    return browser


def new_context(browser, **kwargs):
    ctx = browser.new_context(
        user_agent=USER_AGENT,
        viewport={"width": 1366, "height": 900},
        locale="en-US",
        **kwargs,
    )
    # hide webdriver flag
    ctx.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return ctx


def pdf_matches_title(
    pdf_path: Path,
    title: str,
    doi: str | None = None,
    authors: list[str] | None = None,
    year: int | str | None = None,
) -> bool:
    """Content check: does the downloaded PDF look like the queried paper?

    Guards against OpenAlex location pollution (an OA slot pointing at a
    different paper — even a topically adjacent one sharing keywords).
    PASS if any strong signal matches: expected DOI, a query author surname,
    or strict keywords + expected year. Returns True when unsure
    (no extractable text — e.g. scanned PDF) to avoid false discards.
    """
    try:
        from pypdf import PdfReader
    except ImportError:
        return True
    try:
        reader = PdfReader(str(pdf_path))
        text = ""
        for page in reader.pages[:4]:
            try:
                text += (page.extract_text() or "") + "\n"
            except Exception:
                continue
            if len(text) > 8000:
                break
        text = text.lower()
        if len(text.strip()) < 500:
            return True  # can't judge scanned/image PDFs — keep
        first_page = text[:2000]

        # 1) DOI printed on page 1 by most publishers
        if doi:
            d = str(doi).lower().replace("https://doi.org/", "").replace("http://dx.doi.org/", "").strip()
            if d and (d in text or ("/" in d and d.split("/", 1)[1] in text)):
                return True
        # 2) a query author surname on the title page
        for a in authors or []:
            parts = re.sub(r"[^a-z ]+", " ", str(a).lower()).split()
            if parts and len(parts[-1]) >= 4 and parts[-1] in first_page:
                return True
        # 3) fallback: most distinctive word + >=3 top keywords + year
        words = [w for w in normalize_title(title).split() if len(w) >= 5]
        keywords = sorted(set(words), key=len, reverse=True)[:6]
        if keywords and keywords[0] in text:
            hits = sum(1 for kw in keywords if kw in text)
            year_ok = not year or str(year) in text
            if hits >= 3 and year_ok:
                return True
        return False
    except Exception:
        return True


def polite_delay(seconds: float = 1.0):
    time.sleep(seconds)
