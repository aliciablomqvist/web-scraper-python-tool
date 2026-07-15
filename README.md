# Web Scraper & Alerting Pipeline

**Python / AI Automation / Cloud Systems — 2026**

A configuration-driven web scraping pipeline: point it at a new site with a JSON config (no code required for most sites), and it collects listing pages, extracts structured records, exports them to CSV/XLSX/PDF, syncs to a shared database, and sends Discord alerts when new rows show up — all on a schedule via GitHub Actions.

## How it works

The pipeline runs in three explicit steps, so each stage can be inspected or re-run independently:

```
python scraper.py step1 sites/<name>.json   # collect detail-page URLs from the listing pages
python scraper.py step2 sites/<name>.json   # scrape each URL into structured fields
python scraper.py step3 sites/<name>.json   # export (CSV/XLSX/PDF) + sync to DB + Discord alert
```

- **`sites/*.json`** defines a target: base URL, link selector, pagination strategy (`single_page`, `url_pattern`, or `next_button` for JS-driven pagination via Playwright), and request delay range for polite scraping.
- **`extractors.py`** ships a `generic` extractor (title, meta description, auto-detected "Label: value" fields, and a text excerpt) that works out of the box for most sites — a site only needs a custom extractor function if it needs high-precision field mapping.
- **`storage.py`** optionally syncs every row to a shared Supabase table (keyed on site + source URL) so multiple runs/collaborators see the same de-duplicated dataset.
- **`notify.py`** posts a Discord webhook message when new rows appear, optionally filtered by keyword.
- **`docs_data.py`** + **`docs/`** generate a static dashboard (published via GitHub Pages) so non-technical reviewers can browse the latest scraped data without touching the code.
- **`.github/workflows/scrape.yml`** runs the pipeline on a schedule so data stays fresh without manual intervention.

## Reference site

`sites/nomads.json` is the real, in-use configuration: it catalogues public documentary listings from Nomads HRC's film catalogue (title, director, language, topic, year). It's the config this pipeline was originally built to maintain.

`sites/example_books.json` is a safe sandbox example against [books.toscrape.com](https://books.toscrape.com) (a site built specifically for scraping practice) — the fastest way to see the pipeline run end to end without touching a real target.

## Setup

```bash
pip install -r requirements.txt
playwright install chromium   # only needed for sites with render_js: true or next_button pagination
cp .env.example .env
```

Supabase sync and Discord alerts are both optional — leave their `.env` values blank to run purely local (SQLite export only).

## Run it

```bash
python scraper.py list                      # show all configured sites
python scraper.py step1 sites/example_books.json
python scraper.py step2 sites/example_books.json
python scraper.py step3 sites/example_books.json
```

See [`sites/README.md`](sites/README.md) for the full config schema and how to point the pipeline at a new site.

## Known limitations

- The `generic` extractor is heuristic — sites with unusual markup need a purpose-built extractor function (see `nomads_extract` in `extractors.py` for a template).
- `next_button` pagination drives a real Chromium instance via Playwright, so JS-heavy sites are slower and more resource-intensive to scrape than static ones.
- No LLM-based summarization yet — the pipeline currently does structured field extraction and alerting, not free-text summarization of scraped content.
