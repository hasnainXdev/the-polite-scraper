# The Polite Scraper - Assignment A9

A small, polite scraper for the public [Books to Scrape](https://books.toscrape.com)
sandbox. Built for the backend internship track, **Assignment A9**. The data is
already present in the server-rendered HTML, so a headless browser would only add
cost: a plain `requests` + `BeautifulSoup` pipeline is all this needs.

## Run it

Lane: **backend internship, A9**. Python 3.10+.

```bash
cd scraper
uv venv
uv pip install -r requirements.txt
uv run python src/main.py
```

Outputs land in `scraper/output/`: `books.json` (60 validated records),
`run-report.json` (honest run metrics), `errors.json` (validation failures, if any).
Run it again and you'll see every page served from `cache/` instead of the network;
no new requests, same 60 records.

## Target classification

- **Site:** https://books.toscrape.com: "Books to Scrape", a public demo catalogue of ~1000 books.
- **Why:** The site describes itself as a sandbox for practising scrapers. Its homepage carries a
  "Books to Scrape, We love being scraped!" banner and a warning that it is a "demo website for
  web scraping purposes. Prices and ratings here were randomly assigned and have no real meaning."
- **Scope:** First 3 catalogue pages only (60 books). The crawler discovers pagination from the
  site's own "next" links; page count is never hardcoded.
- **Data collected:** title, product URL, price text + numeric price, availability text, star
  rating text, description, source page URL, and fetch timestamp.
- **Why appropriate:** The operator explicitly built this site for scraping practice and invites it,
  so collecting a small public subset at a polite rate matches the site's own intended use.

**Robots result:** `GET /robots.txt` returns `404 Not Found`, so no robots file found. A missing
robots file is not blanket permission; we rely on the site's explicit self-description as a
scraping sandbox and keep to a small, slow, public scope.

I will not reuse this code on another site without checking its rules and terms first.

## Record schema

Each entry in `output/books.json`:

| Field              | Type            | Notes                                             |
|--------------------|-----------------|---------------------------------------------------|
| `title`            | string          | book title from the product area                  |
| `product_url`      | string          | absolute URL; canonical identity (no duplicates)  |
| `price_text`       | string          | raw price, e.g. `£51.77` (never discarded)        |
| `price_gbp`        | number (float)  | parsed from `price_text`, e.g. `51.77`            |
| `availability_text`| string          | e.g. `In stock (22 available)`                    |
| `rating_text`      | string          | star rating word, e.g. `Three`                    |
| `description`      | string \| null  | `null` when the page has no description           |
| `source_page`      | string          | catalogue page the book was found on (provenance) |
| `fetched_at`       | string          | UTC ISO timestamp (provenance)                    |

Validated against a `pydantic.BaseModel` before storage; anything that fails goes to
`output/errors.json` and never reaches `books.json`.

## Politeness rules

- **User-Agent:** identifies the bot: `FlyRankInternshipA9/1.0 (+https://github.com/hasnainXdev/the-polite-scraper)`.
- **Delay:** at least 500ms between real requests; cached reads never sleep.
- **Timeout:** 5s on every request; never waits forever.
- **Status check:** only `200` is treated as HTML; anything else is a failed fetch.
- **Cache:** every fetched page is saved under `scraper/cache/` (gitignored) and reused on later runs.
- **Failure survival:** each page is processed independently; a 404/403 fails fast (no retry),
  a timeout/5xx is retried once after a short wait, and one bad page never kills the run.

## Sample run report

Real output from a full run (all 60 pages served from cache):

```json
{
  "start_time": "2026-08-11T12:11:56Z",
  "duration_seconds": 0.766,
  "pages_fetched": 63,
  "cache_hits": 63,
  "valid_records": 60,
  "invalid_records": 0,
  "failed_pages": 0
}
```

## Honest limitations

Descriptions come straight from the page, and Books to Scrape's demo data includes
quirks: for example, some descriptions contain a truncated copy followed by the full
copy. This scraper stores the paragraph exactly as served rather than "fixing" it.

## Ethics note

Use an official API when one exists, never bypass logins, paywalls or blocks, and collect only
what you actually need. This scraper targets a site whose operators explicitly invite scraping, and
it stays well within that invitation: a small public subset, at a polite rate, touching nothing else.
