# The Polite Scraper — Assignment A9

A small, polite scraper for the public [Books to Scrape](https://books.toscrape.com)
sandbox. Built for the backend internship track's Assignment A9.

## Target classification

- **Site:** https://books.toscrape.com — "Books to Scrape", a public demo catalogue of ~1000 books.
- **Why:** The site describes itself as a sandbox for practising scrapers. Its homepage carries a
  "Books to Scrape — We love being scraped!" banner and a warning that it is a "demo website for
  web scraping purposes. Prices and ratings here were randomly assigned and have no real meaning."
- **Scope:** First 3 catalogue pages only (60 books). The crawler discovers pagination from the
  site's own "next" links — page count is never hardcoded.
- **Data collected:** title, product URL, price text + numeric price, availability text, star
  rating text, description, source page URL, and fetch timestamp.
- **Why appropriate:** The operator explicitly built this site for scraping practice and invites it,
  so collecting a small public subset at a polite rate matches the site's own intended use.

**Robots result:** `GET /robots.txt` returns `404 Not Found` — no robots file found. A missing
robots file is not blanket permission; we rely on the site's explicit self-description as a
scraping sandbox and keep to a small, slow, public scope.

I will not reuse this code on another site without checking its rules and terms first.
