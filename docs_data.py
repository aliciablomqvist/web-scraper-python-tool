import json
import os
from datetime import datetime, timezone

DOCS_DATA_DIR = "docs/data"
MANIFEST_PATH = f"{DOCS_DATA_DIR}/manifest.json"


def write_site_data(site, rows):
    os.makedirs(DOCS_DATA_DIR, exist_ok=True)
    out_path = f"{DOCS_DATA_DIR}/{site.key}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False)
    print(f"Portfolio-dashboard: skrev {out_path} ({len(rows)} rader)")
    _update_manifest(site, len(rows))


def _update_manifest(site, count):
    manifest = {"sites": {}}
    if os.path.exists(MANIFEST_PATH):
        with open(MANIFEST_PATH, encoding="utf-8") as f:
            manifest = json.load(f)

    manifest.setdefault("sites", {})[site.key] = {
        "name": site.name,
        "count": count,
        "data_file": f"{site.key}.json",
        "title_field": site.title_field,
    }
    manifest["generated_at"] = datetime.now(timezone.utc).isoformat()

    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
