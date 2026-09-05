"""Import a Needle export or any normalized JSON array of Reddit threads.

Expected minimum per item: {"thread_url":"...", "title":"..."}
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
from reddit_growth.db import init_db
from reddit_growth.service import ingest

p = argparse.ArgumentParser()
p.add_argument("file")
args = p.parse_args()
items = json.loads(Path(args.file).read_text(encoding="utf-8"))
if isinstance(items, dict):
    items = items.get("items") or items.get("results") or []
init_db()
print(json.dumps(ingest(items, source="needle"), indent=2))
