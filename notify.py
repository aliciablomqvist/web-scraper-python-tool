import os

import requests
from dotenv import load_dotenv

load_dotenv()


def _matches_keywords(row, keywords):
    if not keywords:
        return True
    haystack = " ".join(str(v) for v in row.values()).lower()
    return any(kw.lower() in haystack for kw in keywords)


def _row_label(site, row):
    if site.title_field and row.get(site.title_field):
        return row[site.title_field]
    return next(iter(row.values()), "Okänd rad")


def notify_new_rows(site, rows):
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        print("DISCORD_WEBHOOK_URL saknas i .env - hoppar över notiser.")
        return

    if not rows:
        print("Inga nya rader - ingen notis skickas.")
        return

    keywords_raw = os.environ.get("NOTIFY_KEYWORDS", "")
    keywords = [k.strip() for k in keywords_raw.split(",") if k.strip()]

    matched = [row for row in rows if _matches_keywords(row, keywords)]
    if not matched:
        print(f"{len(rows)} nya rader, men inga matchade NOTIFY_KEYWORDS.")
        return

    lines = [f"🚨 **{len(matched)} nya rader hittade ({site.name})**"]
    for row in matched[:10]:
        lines.append(f"- {_row_label(site, row)}")
    if len(matched) > 10:
        lines.append(f"...och {len(matched) - 10} till.")

    send_discord_message("\n".join(lines))


def send_discord_message(content):
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        print("DISCORD_WEBHOOK_URL saknas i .env - hoppar över notis.")
        return

    try:
        resp = requests.post(webhook_url, json={"content": content}, timeout=10)
        resp.raise_for_status()
        print("Discord-notis skickad.")
    except Exception as e:
        print(f"Kunde inte skicka Discord-notis: {e}")
