from __future__ import annotations
import argparse
import json
from reddit_growth.db import init_db
from reddit_growth.service import run_daily

parser = argparse.ArgumentParser()
parser.add_argument("--source", choices=["reddit_api", "queue_only"], default="queue_only")
parser.add_argument("--max-drafts", type=int, default=None)
args = parser.parse_args()
init_db()
print(json.dumps(run_daily(source=args.source, max_drafts=args.max_drafts), indent=2))
