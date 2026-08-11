#!/usr/bin/env python3
"""Assignment A9 - The Polite Scraper.

Single entry point. Target: https://books.toscrape.com (public scraping sandbox).
"""

import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel, ValidationError

BASE_URL = "https://books.toscrape.com"
ROBOTS_URL = f"{BASE_URL}/robots.txt"
CATALOGUE_URL = f"{BASE_URL}/catalogue/page-1.html"
SCOPE_PAGE_LIMIT = 3
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"


class BookRecord(BaseModel):
    title: str
    product_url: str
    price_text: str
    price_gbp: float
    availability_text: str
    rating_text: str
    description: str | None = None
    source_page: str
    fetched_at: str
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
    resp.encoding = "utf-8"
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


def discover_catalogue() -> tuple[int, int, dict[str, str]]:
    """Follow 'next' links within the declared 3-page scope to find book URLs.

    Returns (page_count, discovered_links, book_pages) where book_pages maps each
    unique book URL to the catalogue page it was found on (its source_page). Every
    page is discovered from the site's own 'next' link — the scope limit only
    bounds the crawl to the first three catalogue pages declared in the target
    classification.
    """
    page_urls = [CATALOGUE_URL]
    book_pages: dict[str, str] = {}
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
            book_urls = urljoin(page_url, link["href"])
            book_pages.setdefault(book_urls, page_url)
        next_link = soup.select_one("li.next a[href]")
        if next_link is None or len(page_urls) >= SCOPE_PAGE_LIMIT:
            break
        page_urls.append(urljoin(page_url, next_link["href"]))
    return len(page_urls), discovered, book_pages


def cache_name_for_book(url: str) -> str:
    """Map a book detail URL to its cache file stem, e.g. 'a-light-in-the-attic_1000'."""
    return urlparse(url).path.rstrip("/").split("/")[-2]


def extract_record(book_url: str, source_page: str, content: str) -> dict:
    soup = BeautifulSoup(content, "html.parser")
    product_main = soup.select_one("div.product_main")

    title = product_main.h1.get_text(strip=True) if product_main and product_main.h1 else None
    price_el = product_main.select_one("p.price_color") if product_main else None
    availability_el = product_main.select_one("p.instock.availability") if product_main else None
    rating_el = product_main.select_one("p.star-rating") if product_main else None

    rating_text = None
    if rating_el is not None:
        for cls in rating_el.get("class", []):
            if cls != "star-rating":
                rating_text = cls

    description = None
    description_header = soup.select_one("div#product_description")
    if description_header is not None:
        description_para = description_header.find_next_sibling("p")
        if description_para is not None:
            description = description_para.get_text(strip=True)

    return {
        "title": title,
        "product_url": book_url,
        "price_text": price_el.get_text(strip=True) if price_el is not None else None,
        "availability_text": availability_el.get_text(" ", strip=True) if availability_el is not None else None,
        "rating_text": rating_text,
        "description": description,
        "source_page": source_page,
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def extract_records(book_pages: dict[str, str]) -> list[dict]:
    records = []
    for book_url, source_page in book_pages.items():
        cache_name = cache_name_for_book(book_url)
        content, from_cache = fetch_page(book_url, cache_name)
        size = len(content.encode("utf-8"))
        verb = "CACHE HIT" if from_cache else "FETCH"
        print(f"{verb} {cache_name} (size={size})")
        records.append(extract_record(book_url, source_page, content))
    return records


def normalize_record(raw: dict) -> dict:
    """Add numeric price_gbp alongside the raw price_text; never discard raw values."""
    price_gbp = None
    if raw.get("price_text"):
        match = re.search(r"\d+(?:\.\d+)?", raw["price_text"])
        if match is not None:
            price_gbp = float(match.group(0))
    return {**raw, "price_gbp": price_gbp}


def validate_records(raw_records: list[dict]) -> tuple[list[dict], list[dict]]:
    books, errors = [], []
    for raw in raw_records:
        try:
            record = BookRecord.model_validate(raw)
        except ValidationError as exc:
            errors.append({"reason": exc.errors(), "record": raw})
        else:
            books.append(record.model_dump())
    return books, errors


def write_outputs(books: list[dict], errors: list[dict]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "books.json").write_text(
        json.dumps(books, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUTPUT_DIR / "errors.json").write_text(
        json.dumps(errors, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def main() -> None:
    print("Stage 0: check before you collect")
    fetch_robots()
    print("Stage 4: clean, validate, store")
    page_count, discovered, book_pages = discover_catalogue()
    print(f"catalogue_pages={page_count} discovered={discovered} unique_urls={len(book_pages)}")
    raw_records = extract_records(book_pages)
    books, errors = validate_records([normalize_record(r) for r in raw_records])
    write_outputs(books, errors)
    print(f"valid={len(books)} invalid={len(errors)} -> output/books.json")


if __name__ == "__main__":
    main()
