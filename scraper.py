USAGE = """python scraper.py list
python scraper.py step1 sites/nomads.json
python scraper.py step2 sites/nomads.json
python scraper.py step3 sites/nomads.json"""

import csv
import glob
import json
import os
import random
import sys
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from extractors import EXTRACTORS
from sites import load_site

FALLBACK_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0 Safari/537.36",
]

try:
    from fake_useragent import UserAgent
    _ua_generator = UserAgent()
except Exception:
    _ua_generator = None


def get_user_agent():
    if _ua_generator is not None:
        try:
            return _ua_generator.random
        except Exception:
            pass
    return random.choice(FALLBACK_USER_AGENTS)


def get_headers():
    return {"User-Agent": get_user_agent()}


def fetch_html(url, render_js):
    if render_js:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(user_agent=get_user_agent())
            page = context.new_page()
            page.goto(url, wait_until="networkidle", timeout=60000)
            html = page.content()
            context.close()
            browser.close()
            return html

    r = requests.get(url, headers=get_headers(), timeout=20)
    r.raise_for_status()
    return r.text


def _collect_urls_next_button(site, pagination):
    from playwright.sync_api import sync_playwright

    button_texts = pagination.get("button_texts", ["Next"])
    max_pages = pagination.get("max_pages", 40)
    click_wait = pagination.get("click_wait_seconds", 1.5)

    urls, seen = [], set()
    button_selector = ", ".join(f"button:has-text('{t}'), a:has-text('{t}')" for t in button_texts)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=get_user_agent())
        page = context.new_page()
        print(f"Öppnar {site.base_url} ...")
        page.goto(site.base_url, wait_until="networkidle", timeout=60000)
        time.sleep(1.5)

        page_num = 1
        while page_num <= max_pages:
            links = page.eval_on_selector_all(
                site.link_selector, "els => els.map(e => e.href)"
            )
            new_count = 0
            for link in links:
                if link not in seen:
                    seen.add(link)
                    urls.append(link)
                    new_count += 1

            print(f"Sida {page_num}: hittade {len(links)} länkar ({new_count} nya). "
                  f"Totalt hittills: {len(urls)}")

            if page_num > 1 and new_count == 0:
                print("Inga nya länkar hittades, antar att vi nått slutet.")
                break

            candidates = page.locator(button_selector)
            count = candidates.count()
            clicked = False
            for idx in range(count):
                candidate = candidates.nth(idx)
                try:
                    if candidate.is_visible():
                        candidate.scroll_into_view_if_needed()
                        candidate.click(timeout=5000)
                        clicked = True
                        break
                except Exception:
                    continue

            if not clicked:
                print("Hittar ingen synlig 'nästa'-knapp längre, avslutar.")
                break

            time.sleep(click_wait)
            page_num += 1

        context.close()
        browser.close()

    return urls


def _collect_urls_url_pattern(site, pagination):
    url_template = pagination["url_template"]
    start = pagination.get("start", 1)
    max_pages = pagination.get("max_pages", 50)

    urls, seen = [], set()
    for page_num in range(start, start + max_pages):
        page_url = url_template.format(page=page_num)
        try:
            html = fetch_html(page_url, site.render_js)
        except Exception as e:
            print(f"Sida {page_num}: FEL ({e}), antar att vi nått slutet.")
            break

        soup = BeautifulSoup(html, "html.parser")
        links = [
            urljoin(page_url, a["href"])
            for a in soup.select(site.link_selector)
            if a.get("href")
        ]
        new_links = [l for l in links if l not in seen]

        print(f"Sida {page_num}: hittade {len(links)} länkar ({len(new_links)} nya).")
        if not new_links:
            print("Inga nya länkar hittades, antar att vi nått slutet.")
            break

        for l in new_links:
            seen.add(l)
            urls.append(l)

        time.sleep(random.uniform(*site.request_delay_range))

    return urls


def _collect_urls_single_page(site):
    html = fetch_html(site.base_url, site.render_js)
    soup = BeautifulSoup(html, "html.parser")
    urls, seen = [], set()
    for a in soup.select(site.link_selector):
        href = a.get("href")
        if not href:
            continue
        link = urljoin(site.base_url, href)
        if link not in seen:
            seen.add(link)
            urls.append(link)
    return urls


def step1_collect_urls(site):
    os.makedirs(site.data_dir, exist_ok=True)
    ptype = site.pagination.get("type", "single_page")

    if ptype == "next_button":
        urls = _collect_urls_next_button(site, site.pagination)
    elif ptype == "url_pattern":
        urls = _collect_urls_url_pattern(site, site.pagination)
    elif ptype == "single_page":
        urls = _collect_urls_single_page(site)
    else:
        raise ValueError(f"Okänd pagination.type: {ptype!r}")

    with open(site.urls_file, "w", encoding="utf-8") as f:
        for u in urls:
            f.write(u.strip() + "\n")

    print(f"\nKLART! Sparade {len(urls)} URL:er till {site.urls_file}")


def _jsonify_complex_values(row):
    return {
        k: (json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v)
        for k, v in row.items()
    }


def step2_scrape_details(site):
    if not os.path.exists(site.urls_file):
        print(f"Hittar inte {site.urls_file}. Kör 'python scraper.py step1 <config>' först.")
        return

    with open(site.urls_file, encoding="utf-8") as f:
        urls = [line.strip() for line in f if line.strip()]

    done_urls = set()
    file_exists = os.path.exists(site.csv_file)
    if file_exists:
        with open(site.csv_file, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                done_urls.add(row.get("Source URL", ""))

    extractor = EXTRACTORS[site.extractor]
    os.makedirs(site.data_dir, exist_ok=True)

    mode = "a" if file_exists else "w"
    with open(site.csv_file, mode, newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=site.fieldnames, extrasaction="ignore", restval="")
        if not file_exists:
            writer.writeheader()

        session = requests.Session() if not site.render_js else None

        for i, url in enumerate(urls, 1):
            if url in done_urls:
                continue
            try:
                if site.render_js:
                    html = fetch_html(url, render_js=True)
                else:
                    r = session.get(url, headers=get_headers(), timeout=20)
                    r.raise_for_status()
                    html = r.text

                row = _jsonify_complex_values(extractor(url, html))
                writer.writerow(row)
                f.flush()
                label = row.get(site.title_field) if site.title_field else next(iter(row.values()), "")
                print(f"[{i}/{len(urls)}] {label!r}")
            except Exception as e:
                print(f"[{i}/{len(urls)}] FEL vid {url}: {e}")
            time.sleep(random.uniform(*site.request_delay_range))

    print(f"\nKLART! Data sparad i {site.csv_file}")


def step3_export_and_sync(site):
    import docs_data
    import exporters
    import notify
    import storage

    if not os.path.exists(site.csv_file):
        print(f"Hittar inte {site.csv_file}. Kör 'python scraper.py step2 <config>' först.")
        return

    exporters.export_excel(site.csv_file, site.xlsx_file, title=site.name)
    exporters.export_pdf(site.csv_file, site.pdf_file, title=site.name)

    new_rows = storage.sync_from_csv(site.key, site.csv_file)

    with open(site.csv_file, encoding="utf-8") as f:
        all_rows = list(csv.DictReader(f))
    storage.sync_supabase(site.key, all_rows)
    docs_data.write_site_data(site, all_rows)

    notify.notify_new_rows(site, new_rows)

    print("\nKLART! step3 (export + databassynk + notiser) färdig.")


def list_sites():
    for path in sorted(glob.glob("sites/*.json")):
        site = load_site(path)
        print(f"{site.key:20s} {site.name:35s} {path}")


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "list":
        list_sites()
        sys.exit(0)

    if len(sys.argv) != 3 or sys.argv[1] not in ("step1", "step2", "step3"):
        print(USAGE)
        sys.exit(1)

    site_config = load_site(sys.argv[2])
    {
        "step1": step1_collect_urls,
        "step2": step2_scrape_details,
        "step3": step3_export_and_sync,
    }[sys.argv[1]](site_config)
