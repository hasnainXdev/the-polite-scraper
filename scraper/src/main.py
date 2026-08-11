#!/usr/bin/env python3
"""Assignment A9 - The Polite Scraper.

Single entry point. Target: https://books.toscrape.com (public scraping sandbox).
"""

import time
from pathlib import Path

import requests

BASE_URL = "https://books.toscrape.com"
ROBOTS_URL = f"{BASE_URL}/robots.txt"
CATALOGUE_URL = f"{BASE_URL}/catalogue/page-1.html"
CACHE_DIR = Path(__file__).resolve().parent.parent / "cache"
USER_AGENT = "FlyRankInternshipA9/1.0 (+https://github.com/<my-username>/<repo>)"
REQUEST_TIMEOUT = 5
POLITE_DELAY = 0.5


_last_request_at = 0.0


def _respect_delay() -> None:
    """Sleep the remainder of the 500ms polite window before a real request."""
    global _last_request_at
    elapsed = time.monotonic() - _last_request_at
    if elapsed < POLITE_DELAY:
        time.sleep(POLITE_DELAY - elapsed)
    _last_request_at = time.monotonic()


def fetch_page(url: str, cache_name: str) -> tuple[str, bool]:
    """Fetch url honouring the politeness rules, caching to disk.

    Returns (content, from_cache). Cached reads never sleep.
    """
    cache_path = CACHE_DIR / f"{cache_name}.html"
    if cache_path.exists():
        return cache_path.read_text(encoding="utf-8"), True
    _respect_delay()
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT)
    if resp.status_code != 200:
        raise RuntimeError(f"failed fetch: GET {url} -> HTTP {resp.status_code}")
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(resp.text, encoding="utf-8")
    return resp.text, False


def fetch_robots() -> None:
    cache_path = CACHE_DIR / "robots.txt"
    if cache_path.exists():
        print(f"CACHE HIT robots.txt (size={cache_path.stat().st_size})")
        print(cache_path.read_text(encoding="utf-8"), end="")
        return
    _respect_delay()
    resp = requests.get(ROBOTS_URL, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if resp.status_code == 200:
        cache_path.write_text(resp.text, encoding="utf-8")
        print(f"FETCH robots.txt (size={len(resp.text)})")
        print(resp.text, end="")
    elif resp.status_code == 404:
        cache_path.write_text("no robots file found\n", encoding="utf-8")
        print("FETCH robots.txt (status=404)")
        print("no robots file found")
    else:
        raise RuntimeError(f"failed fetch: GET {ROBOTS_URL} -> HTTP {resp.status_code}")


def fetch_catalogue_page_1() -> None:
    content, from_cache = fetch_page(CATALOGUE_URL, "catalogue-page-1")
    size = len(content.encode("utf-8"))
    verb = "CACHE HIT" if from_cache else "FETCH"
    print(f"{verb} catalogue-page-1 (size={size})")


def main() -> None:
    print("Stage 0: check before you collect")
    fetch_robots()
    print("Stage 1: fetch once, cache once")
    fetch_catalogue_page_1()


if __name__ == "__main__":
    main()
