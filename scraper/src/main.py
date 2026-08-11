#!/usr/bin/env python3
"""Assignment A9 - The Polite Scraper.

Single entry point. Target: https://books.toscrape.com (public scraping sandbox).
"""

import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

BASE_URL = "https://books.toscrape.com"
ROBOTS_URL = f"{BASE_URL}/robots.txt"
CATALOGUE_URL = f"{BASE_URL}/catalogue/page-1.html"
SCOPE_PAGE_LIMIT = 3
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


def cache_name_for_page(url: str) -> str:
    """Map a catalogue page URL to its cache file stem, e.g. 'catalogue-page-1'."""
    name = Path(url).name
    return f"catalogue-{name[:-len('.html')]}"


def discover_catalogue() -> tuple[int, int, list[str]]:
    """Follow 'next' links within the declared 3-page scope to find book URLs.

    Returns (page_count, discovered_links, unique_book_urls). Every page is still
    discovered from the site's own 'next' link — the scope limit only bounds the
    crawl to the first three catalogue pages declared in the target classification.
    """
    page_urls = [CATALOGUE_URL]
    book_urls: set[str] = set()
    discovered = 0
    while True:
        page_url = page_urls[-1]
        cache_name = cache_name_for_page(page_url)
        content, from_cache = fetch_page(page_url, cache_name)
        size = len(content.encode("utf-8"))
        verb = "CACHE HIT" if from_cache else "FETCH"
        print(f"{verb} {cache_name} (size={size})")
        soup = BeautifulSoup(content, "html.parser")
        links = soup.select("article.product_pod h3 a[href]")
        discovered += len(links)
        for link in links:
            book_urls.add(urljoin(page_url, link["href"]))
        next_link = soup.select_one("li.next a[href]")
        if next_link is None or len(page_urls) >= SCOPE_PAGE_LIMIT:
            break
        page_urls.append(urljoin(page_url, next_link["href"]))
    return len(page_urls), discovered, sorted(book_urls)


def main() -> None:
    print("Stage 0: check before you collect")
    fetch_robots()
    print("Stage 2: find all three pages")
    page_count, discovered, book_urls = discover_catalogue()
    print(f"catalogue_pages={page_count} discovered={discovered} unique_urls={len(book_urls)}")


if __name__ == "__main__":
    main()
