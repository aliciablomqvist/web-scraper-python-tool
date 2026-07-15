import re

from bs4 import BeautifulSoup


def extract_label_value_pairs(soup):
    fields = {}

    for div in soup.find_all("div"):
        spans = div.find_all("span", recursive=False)
        if len(spans) == 2:
            label = spans[0].get_text(strip=True).rstrip(":").strip()
            value = " ".join(spans[1].get_text(separator=" ").split()).strip(", ").strip()
            if label and value and label not in fields:
                fields[label] = value

    for dt in soup.find_all("dt"):
        dd = dt.find_next_sibling("dd")
        if dd:
            label = dt.get_text(strip=True).rstrip(":").strip()
            value = " ".join(dd.get_text(separator=" ").split()).strip()
            if label and value and label not in fields:
                fields[label] = value

    for row in soup.find_all("tr"):
        cells = row.find_all(["th", "td"])
        if len(cells) == 2:
            label = cells[0].get_text(strip=True).rstrip(":").strip()
            value = " ".join(cells[1].get_text(separator=" ").split()).strip()
            if label and value and label not in fields:
                fields[label] = value

    return fields


def generic_extract(url, html):
    soup = BeautifulSoup(html, "html.parser")

    title = ""
    for tag_name in ("h1", "h2", "title"):
        el = soup.find(tag_name)
        if el and el.get_text(strip=True):
            title = el.get_text(strip=True)
            break

    description = ""
    meta = soup.find("meta", attrs={"name": "description"}) or soup.find(
        "meta", attrs={"property": "og:description"}
    )
    if meta and meta.get("content"):
        description = " ".join(meta["content"].split())

    fields = extract_label_value_pairs(soup)

    text_excerpt = " ".join(soup.get_text(separator=" ").split())[:1000]

    return {
        "Title": title,
        "Description": description,
        "Text excerpt": text_excerpt,
        "Extra fields (JSON)": fields,
        "Source URL": url,
    }


def nomads_extract(url, html):
    soup = BeautifulSoup(html, "html.parser")

    h2 = soup.find("h2")
    title = h2.get_text(strip=True) if h2 else ""

    fields = {}
    for div in soup.find_all("div"):
        spans = div.find_all("span", recursive=False)
        if len(spans) == 2:
            classes = spans[0].get("class") or []
            if "text-white" in classes:
                label = spans[0].get_text(strip=True).rstrip(":").strip()
                value = " ".join(spans[1].get_text(separator=" ").split())
                value = value.strip(", ").strip()
                if label:
                    fields[label] = value

    director = fields.get("Director", "")
    lang = fields.get("Languages", fields.get("Language", ""))
    subs = fields.get("Subtitles", "")
    topics = fields.get("Topics", "")

    year = ""
    year_wrap = soup.find("div", class_=lambda c: c and "flex-wrap" in c)
    if year_wrap:
        y = re.search(r"(19|20)\d{2}", year_wrap.get_text())
        if y:
            year = y.group(0)

    full_film_link = ""
    trailer_link = ""

    for a in soup.find_all("a"):
        click_attr = a.get("@click.prevent") or a.get("@click") or ""
        if not click_attr:
            continue
        if "youtubeUrl" not in click_attr and "vimeoUrl" not in click_attr:
            continue

        btn_text = a.get_text(strip=True).lower()

        vim = re.search(r"vimeoUrl\s*=\s*'([^']*)'", click_attr)
        yt = re.search(r"youtubeUrl\s*=\s*'([^']*)'", click_attr)

        link = ""
        if vim and vim.group(1) and "undefined" not in vim.group(1):
            link = vim.group(1)
        elif yt and yt.group(1) and "undefined" not in yt.group(1):
            link = yt.group(1)

        if not link:
            continue

        if "trailer" in btn_text or "teaser" in btn_text:
            trailer_link = trailer_link or link
        else:
            full_film_link = full_film_link or link

    watch_online_link = ""
    header = soup.find(string=re.compile(r"Watch online", re.I))
    if header:
        container = header.find_parent()
        if container:
            nxt = container.find_next("a", href=True)
            if nxt and nxt.get("href", "").startswith("http"):
                watch_online_link = nxt["href"]

    if watch_online_link and not full_film_link:
        full_film_link = watch_online_link

    if full_film_link:
        status = "Fullständig film (Watch Film)"
        link_out = full_film_link
    elif trailer_link:
        status = "Bara trailer"
        link_out = trailer_link
    else:
        status = "Ingen länk tillgänglig"
        link_out = ""

    return {
        "Name of Documentary": title,
        "Director": director,
        "Language": lang,
        "Subtitles": subs,
        "Published year": year,
        "Type": status,
        "Link to Documentary": link_out,
        "Topic": topics,
        "Source URL": url,
    }


EXTRACTORS = {
    "generic": generic_extract,
    "nomads": nomads_extract,
}
