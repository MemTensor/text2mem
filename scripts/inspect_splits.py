#!/usr/bin/env python3
"""
Inspect split results in the Text2Mem SQLite DB.

Usage examples:
  - Auto-detect the most recent split parent and list its children:
      python scripts/inspect_splits.py

  - Specify DB path and parent id explicitly:
      python scripts/inspect_splits.py --db text2mem.db --parent-id 31010

Outputs a compact summary of the parent and its split children with previews.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
from typing import Optional, Tuple, List


def _connect(db_path: str) -> sqlite3.Connection:
    if not os.path.exists(db_path):
        raise SystemExit(f"DB not found: {db_path}")
    conn = sqlite3.connect(db_path)
    # Ensure text returns str
    conn.row_factory = sqlite3.Row
    return conn


def _detect_latest_parent_id(conn: sqlite3.Connection) -> Optional[int]:
    """Find the most recent parent id by looking at children tagged with split_from_XXX.

    We don't rely on SQLite JSON1; instead we fetch recent rows and parse tags in Python.
    """
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, tags
        FROM memory
        WHERE tags LIKE '%"split_from_%'
        ORDER BY id DESC
        LIMIT 50
        """
    )
    rows = cur.fetchall()
    split_re = re.compile(r"^split_from_(\d+)$")
    for row in rows:
        tags_text = row["tags"] or "[]"
        try:
            tags = json.loads(tags_text)
        except Exception:
            continue
        if isinstance(tags, list):
            for t in tags:
                if isinstance(t, str):
                    m = split_re.match(t)
                    if m:
                        return int(m.group(1))
    return None


def _get_parent(conn: sqlite3.Connection, parent_id: int) -> Optional[sqlite3.Row]:
    cur = conn.cursor()
    cur.execute(
        "SELECT id, text, subject, topic, time, tags FROM memory WHERE id = ?",
        (parent_id,),
    )
    return cur.fetchone()


def _get_children(conn: sqlite3.Connection, parent_id: int) -> List[sqlite3.Row]:
    cur = conn.cursor()
    pattern = f'%"split_from_{parent_id}"%'
    cur.execute(
        """
        SELECT id, text, subject, topic, time, tags
        FROM memory
        WHERE tags LIKE ?
        ORDER BY id ASC
        """,
        (pattern,),
    )
    return cur.fetchall()


def _preview(text: Optional[str], limit: int = 120) -> str:
    if not text:
        return ""
    txt = text.strip().replace("\n", " ")
    if len(txt) <= limit:
        return txt
    return txt[: limit - 1] + "…"


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect split results in the DB")
    parser.add_argument("--db", default="text2mem.db", help="Path to SQLite DB (default: text2mem.db)")
    parser.add_argument("--parent-id", type=int, help="Parent memory id; if omitted, auto-detect the latest parent")
    parser.add_argument("--show-tags", action="store_true", help="Show tags column for parent and children")
    parser.add_argument("--child-limit", type=int, default=200, help="Max children to show (default: 200)")
    args = parser.parse_args()

    conn = _connect(args.db)

    parent_id = args.parent_id
    if parent_id is None:
        parent_id = _detect_latest_parent_id(conn)
        if parent_id is None:
            raise SystemExit("No split children found; cannot auto-detect parent id. Use --parent-id.")

    parent = _get_parent(conn, parent_id)
    if not parent:
        raise SystemExit(f"Parent not found: {parent_id}")

    children = _get_children(conn, parent_id)

    print("=== Parent ===")
    print(f"id: {parent['id']}")
    if parent["subject"]:
        print(f"subject: {parent['subject']}")
    if parent["topic"]:
        print(f"topic: {parent['topic']}")
    if parent["time"]:
        print(f"time: {parent['time']}")
    if args.show_tags:
        print(f"tags: {parent['tags']}")
    print(f"preview: {_preview(parent['text'], 200)}")
    print()

    count = len(children)
    print(f"=== Children ({count}) ===")
    for i, ch in enumerate(children[: args.child_limit], start=1):
        title = (ch["text"] or "").splitlines()[0].strip()
        title = title if title else "(no title)"
        print(f"[{i}] id={ch['id']} title={_preview(title, 80)}")
        print(f"    preview: {_preview(ch['text'], 160)}")
        if args.show_tags:
            print(f"    tags: {ch['tags']}")
    if count > args.child_limit:
        print(f"… {count - args.child_limit} more not shown")


if __name__ == "__main__":
    main()
