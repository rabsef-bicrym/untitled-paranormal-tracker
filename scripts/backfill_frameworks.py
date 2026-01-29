#!/usr/bin/env python3
"""
Backfill parapsychology framework analysis for stories already in the database.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime

import psycopg2

from framework_analysis import analyze_story_frameworks, FRAMEWORK_SCHEMA_VERSION
from load_segments import ensure_framework_columns


DEFAULT_DATABASE_URL = "postgresql://paranormal:paranormal@localhost:5433/paranormal_tracker"


def get_database_url() -> str:
    return os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)


def fetch_stories(conn, ids: list[str] | None, include_all: bool, limit: int | None):
    with conn.cursor() as cur:
        if ids:
            cur.execute(
                """
                SELECT id, title, content
                FROM stories
                WHERE id = ANY(%s)
                ORDER BY id
                """,
                (ids,),
            )
        elif include_all:
            cur.execute(
                """
                SELECT id, title, content
                FROM stories
                WHERE is_first_person IS TRUE AND content IS NOT NULL
                ORDER BY id
                """
            )
        else:
            cur.execute(
                """
                SELECT id, title, content
                FROM stories
                WHERE is_first_person IS TRUE
                  AND content IS NOT NULL
                  AND (frameworks_json IS NULL OR frameworks_version IS DISTINCT FROM %s)
                ORDER BY id
                """,
                (FRAMEWORK_SCHEMA_VERSION,),
            )

        rows = cur.fetchall()

    if limit is not None:
        rows = rows[:limit]
    return rows


def update_story_frameworks(conn, story_id: str, payload: dict, model: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE stories
            SET frameworks_json = %s::jsonb,
                frameworks_version = %s,
                frameworks_model = %s,
                frameworks_computed_at = %s,
                updated_at = now()
            WHERE id = %s
            """,
            (
                json.dumps(payload, ensure_ascii=True),
                FRAMEWORK_SCHEMA_VERSION,
                model,
                datetime.utcnow(),
                story_id,
            ),
        )
    conn.commit()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Backfill parapsychology framework analysis for stories in the database."
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Recompute frameworks for all stories (ignores version checks)",
    )
    parser.add_argument(
        "--id",
        action="append",
        default=[],
        help="Story UUID to process (repeatable)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of stories processed",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="Delay between stories in seconds (default: 0.5)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show which stories would be processed without updating",
    )
    parser.add_argument(
        "--framework-model",
        type=str,
        default=None,
        help="Anthropic model override (defaults to ANTHROPIC_MODEL env)",
    )

    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not args.dry_run and not api_key:
        print("ANTHROPIC_API_KEY environment variable required", file=sys.stderr)
        return 1

    database_url = get_database_url()
    try:
        conn = psycopg2.connect(database_url)
    except Exception as e:
        print(f"Database connection failed: {e}", file=sys.stderr)
        return 1

    ensure_framework_columns(conn)

    rows = fetch_stories(conn, args.id or None, args.all, args.limit)
    total = len(rows)
    if total == 0:
        print("No stories found to process.")
        conn.close()
        return 0

    print(f"{'[DRY RUN] ' if args.dry_run else ''}Processing {total} story(ies)...")
    print()

    processed = 0
    errors = 0
    for idx, (story_id, title, content) in enumerate(rows):
        try:
            if args.dry_run:
                print(f"  WOULD_UPDATE: {title} ({story_id})")
            else:
                result = analyze_story_frameworks(
                    content,
                    api_key=api_key or "",
                    model=args.framework_model,
                )
                update_story_frameworks(conn, story_id, result.to_json(), result.model)
                print(f"  UPDATED: {title}")
            processed += 1
        except Exception as e:
            errors += 1
            print(f"  ERROR: {title} - {e}", file=sys.stderr)

        if not args.dry_run and idx < total - 1 and args.delay > 0:
            time.sleep(args.delay)

    conn.close()

    print()
    print("=" * 40)
    print(f"{'[DRY RUN] ' if args.dry_run else ''}Summary:")
    print(f"  Processed: {processed}")
    print(f"  Errors: {errors}")

    return 1 if errors > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
