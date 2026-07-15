# Lägga till en ny sajt

Skapa en `sites/<namn>.json` och kör `python scraper.py step1 sites/<namn>.json`
osv. Ingen kod behöver skrivas om `"extractor": "generic"` räcker (fungerar mot
de flesta sajter: hämtar titel, meta-beskrivning, "Label: värde"-fält den
hittar automatiskt, samt en textutdrag).

```jsonc
{
  "key": "exempel",                 // används i filnamn (data/exempel/...) och i databasen
  "name": "Läsbart namn",           // visas i export-titlar och Discord-notiser
  "base_url": "https://...",       // startsida (listningssida eller enda sidan)
  "link_selector": "a.some-class", // CSS-selector som pekar ut länkar till detaljsidor
  "extractor": "generic",          // "generic", "nomads", eller en ny nyckel du lägger i extractors.py
  "fieldnames": null,               // bara nödvändigt för egna extraktorer - annars auto
  "pagination": {
    "type": "single_page"           // "single_page" | "url_pattern" | "next_button"
  },
  "render_js": false,               // true om sidan kräver JavaScript (kör via Playwright)
  "request_delay_range": [2, 5],    // slumpad fördröjning (sekunder) mellan anrop
  "title_field": null               // kolumn att visa i Discord-notiser, annars första kolumnen
}
```

## Pagination-typer

- `single_page` - bara `base_url`, ingen bläddring.
- `url_pattern` - bygger URL:er från en mall med `{page}`:
  ```json
  { "type": "url_pattern", "url_template": "https://site.com/page/{page}", "start": 1, "max_pages": 50 }
  ```
- `next_button` - klickar på en "Nästa"-knapp via Playwright (för sidor där
  bläddring sker med JavaScript/AJAX, t.ex. Livewire):
  ```json
  { "type": "next_button", "button_texts": ["Next", "Nästa"], "max_pages": 40, "click_wait_seconds": 1.8 }
  ```

## Egen extraktor (för hög precision mot en specifik sajt)

Lägg en funktion `def my_extract(url, html) -> dict` i `extractors.py` och
registrera den i `EXTRACTORS`-dicten. Ange sedan `"extractor": "my_extract"`
och en explicit `"fieldnames"`-lista (kolumnordning) i sajtens JSON-fil.
Se `nomads_extract` i `extractors.py` för ett exempel.

## Supabase-schema (valfritt)

Om `SUPABASE_URL`/`SUPABASE_KEY` sätts i `.env` synkar `storage.py` alla
rader till en delad Supabase-tabell. Skapa den en gång med:

```sql
create table scraped_items (
    site_key text not null,
    source_url text not null,
    data jsonb not null,
    first_seen timestamptz not null,
    primary key (site_key, source_url)
);
```

## Testa konfigurationen

```
python scraper.py list                        # visar alla konfigurerade sajter
python scraper.py step1 sites/<namn>.json      # samlar in detaljsides-URL:er
python scraper.py step2 sites/<namn>.json      # skrapar varje URL
python scraper.py step3 sites/<namn>.json      # export + databas + notiser
```

`sites/example_books.json` är ett körbart exempel mot books.toscrape.com
(en sandlåda som är gjord specifikt för att öva skrapning på).
