import csv
import json
import os
import sqlite3
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv()

DB_PATH = "data/scraper.db"


def _connect():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS items (
            site_key TEXT NOT NULL,
            source_url TEXT NOT NULL,
            data_json TEXT NOT NULL,
            first_seen TEXT NOT NULL,
            PRIMARY KEY (site_key, source_url)
        )
        """
    )
    conn.commit()


def sync_from_csv(site_key, csv_path):
    if not os.path.exists(csv_path):
        print(f"Hittar inte {csv_path}, hoppar över databassynk.")
        return []

    with open(csv_path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    conn = _connect()
    init_db(conn)

    existing = {
        row["source_url"]
        for row in conn.execute(
            "SELECT source_url FROM items WHERE site_key = ?", (site_key,)
        )
    }

    new_rows = []
    now = datetime.now(timezone.utc).isoformat()
    for row in rows:
        source_url = row.get("Source URL", "")
        if not source_url:
            continue
        is_new = source_url not in existing
        conn.execute(
            """
            INSERT INTO items (site_key, source_url, data_json, first_seen)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(site_key, source_url) DO UPDATE SET
                data_json = excluded.data_json
            """,
            (site_key, source_url, json.dumps(row, ensure_ascii=False), now),
        )
        if is_new:
            new_rows.append(row)

    conn.commit()
    conn.close()

    print(f"SQLite ({DB_PATH}): {len(rows)} rader synkade för '{site_key}', {len(new_rows)} nya.")
    return new_rows


def sync_supabase(site_key, rows):
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        print("SUPABASE_URL/SUPABASE_KEY saknas i .env - hoppar över Supabase-synk.")
        return

    if not rows:
        print("Inga rader att synka till Supabase.")
        return

    try:
        from supabase import create_client
    except ImportError:
        print("Paketet 'supabase' är inte installerat (pip install supabase).")
        return

    now = datetime.now(timezone.utc).isoformat()
    payload = [
        {
            "site_key": site_key,
            "source_url": row.get("Source URL", ""),
            "data": {k: v for k, v in row.items() if k != "Source URL"},
            "first_seen": now,
        }
        for row in rows
        if row.get("Source URL")
    ]

    try:
        client = create_client(url, key)
        client.table("scraped_items").upsert(payload, on_conflict="site_key,source_url").execute()
        print(f"Supabase: {len(payload)} rader synkade till tabellen 'scraped_items'.")
    except Exception as e:
        print(f"Supabase-synk misslyckades: {e}")
