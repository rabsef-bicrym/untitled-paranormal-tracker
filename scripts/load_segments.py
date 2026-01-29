#!/usr/bin/env python3
"""
Load segment markdown files into the database with embeddings and framework analysis.

Reads .md files from segments/, parses frontmatter, runs parapsychology framework
analysis via Anthropic, generates embeddings via Voyage AI, and inserts into PostgreSQL.

For stories under the token limit: embed the full story.
For longer stories: chunk, embed each chunk, mean-pool for story embedding.

Usage:
  python scripts/load_segments.py
  python scripts/load_segments.py --root segments --dry-run
  python scripts/load_segments.py --file segments/show/2024-01-15_story.md

Environment:
  VOYAGE_API_KEY - Voyage AI API key
  DATABASE_URL   - PostgreSQL connection string
                   (default: postgresql://paranormal:paranormal@localhost:5433/paranormal_tracker)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import date, datetime
from pathlib import Path
from typing import Iterable

import yaml

from framework_analysis import analyze_story_frameworks, FRAMEWORK_SCHEMA_VERSION
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent

DEFAULT_SEGMENTS_DIR = REPO_ROOT / "segments"
DEFAULT_DATABASE_URL = "postgresql://paranormal:paranormal@localhost:5433/paranormal_tracker"

# Voyage AI embedding config
VOYAGE_MODEL = "voyage-4-large"  # 1024-dim default, best quality
EMBEDDING_DIM = 1024
MAX_TOKENS_FOR_FULL_EMBED = 4000  # Below this, embed full story
CHUNK_SIZE_TOKENS = 500  # Approximate tokens per chunk
CHUNK_OVERLAP_TOKENS = 50
VOYAGE_API_URL = "https://api.voyageai.com/v1/embeddings"


def ensure_framework_columns(conn) -> None:
    with conn.cursor() as cur:
        cur.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                              WHERE table_name='stories' AND column_name='frameworks_json') THEN
                    ALTER TABLE stories ADD COLUMN frameworks_json JSONB;
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                              WHERE table_name='stories' AND column_name='frameworks_version') THEN
                    ALTER TABLE stories ADD COLUMN frameworks_version TEXT;
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                              WHERE table_name='stories' AND column_name='frameworks_model') THEN
                    ALTER TABLE stories ADD COLUMN frameworks_model TEXT;
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                              WHERE table_name='stories' AND column_name='frameworks_computed_at') THEN
                    ALTER TABLE stories ADD COLUMN frameworks_computed_at TIMESTAMPTZ;
                END IF;
            END $$;
        """)
    conn.commit()


def get_database_url() -> str:
    return os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Parse YAML frontmatter and body from markdown file."""
    if not content.startswith("---"):
        return {}, content

    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content

    try:
        frontmatter = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        frontmatter = {}

    body = parts[2].strip()
    return frontmatter, body


def estimate_tokens(text: str) -> int:
    """Rough token estimate (words * 1.3)."""
    return int(len(text.split()) * 1.3)


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE_TOKENS, overlap: int = CHUNK_OVERLAP_TOKENS) -> list[str]:
    """
    Split text into overlapping chunks.

    Uses paragraph boundaries when possible.
    """
    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = []
    current_tokens = 0

    for para in paragraphs:
        para_tokens = estimate_tokens(para)

        if current_tokens + para_tokens > chunk_size and current_chunk:
            chunks.append("\n\n".join(current_chunk))
            # Keep overlap
            overlap_text = current_chunk[-1] if current_chunk else ""
            current_chunk = [overlap_text] if estimate_tokens(overlap_text) < overlap else []
            current_tokens = estimate_tokens("\n\n".join(current_chunk))

        current_chunk.append(para)
        current_tokens += para_tokens

    if current_chunk:
        chunks.append("\n\n".join(current_chunk))

    return chunks


def get_embedding_with_retry(text: str, api_key: str, max_retries: int = 5) -> list[float]:
    """Get embedding from Voyage AI with retry on rate limit."""
    import requests
    import time

    for attempt in range(max_retries):
        response = requests.post(
            VOYAGE_API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": VOYAGE_MODEL,
                "input": [text[:32000]],
            },
        )

        if response.status_code == 429:
            # Rate limited - exponential backoff
            wait_time = 2 ** attempt
            print(f"    Rate limited, waiting {wait_time}s...")
            time.sleep(wait_time)
            continue

        response.raise_for_status()
        result = response.json()
        return result["data"][0]["embedding"]

    raise Exception("Max retries exceeded for embedding request")


def get_embeddings_batch_with_retry(texts: list[str], api_key: str, max_retries: int = 5) -> list[list[float]]:
    """Get embeddings for multiple texts with retry on rate limit."""
    import requests
    import time

    if not texts:
        return []

    for attempt in range(max_retries):
        response = requests.post(
            VOYAGE_API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": VOYAGE_MODEL,
                "input": [t[:32000] for t in texts],
            },
        )

        if response.status_code == 429:
            wait_time = 2 ** attempt
            print(f"    Rate limited, waiting {wait_time}s...")
            time.sleep(wait_time)
            continue

        response.raise_for_status()
        result = response.json()
        return [item["embedding"] for item in result["data"]]

    raise Exception("Max retries exceeded for batch embedding request")


def mean_pool_embeddings(embeddings: list[list[float]]) -> list[float]:
    """Average multiple embeddings into one."""
    if not embeddings:
        return [0.0] * EMBEDDING_DIM
    if len(embeddings) == 1:
        return embeddings[0]

    result = [0.0] * len(embeddings[0])
    for emb in embeddings:
        for i, val in enumerate(emb):
            result[i] += val
    return [v / len(embeddings) for v in result]


def iter_segment_files(root: Path, match_patterns: list[str]) -> Iterable[Path]:
    """Yield .md segment files."""
    for path in sorted(root.rglob("*.md")):
        if path.name == "CLAUDE.md":
            continue
        if match_patterns:
            hay = path.as_posix()
            if not any(pat in hay for pat in match_patterns):
                continue
        yield path


def load_segment_to_db(
    file_path: Path,
    conn,
    voyage_api_key: str,
    anthropic_api_key: str | None,
    anthropic_model: str | None,
    frameworks_enabled: bool,
    dry_run: bool = False,
) -> dict:
    """
    Load a single segment file into the database.

    Returns dict with status info.
    """
    content = file_path.read_text()
    frontmatter, body = parse_frontmatter(content)

    if not body.strip():
        return {"status": "skip", "reason": "empty body"}

    # Extract frontmatter fields
    title = frontmatter.get("title", file_path.stem)
    show = frontmatter.get("show", "Unknown")
    episode_date = frontmatter.get("date")
    if isinstance(episode_date, str):
        episode_date = date.fromisoformat(episode_date)
    elif isinstance(episode_date, datetime):
        episode_date = episode_date.date()

    start_time = frontmatter.get("timestamp_start", 0)
    end_time = frontmatter.get("timestamp_end", 0)
    caller = frontmatter.get("caller")
    story_type = frontmatter.get("type")
    location = frontmatter.get("location")
    is_first_person = frontmatter.get("first_person", True)

    if not is_first_person:
        return {"status": "skip", "reason": "not first-person"}

    # Estimate tokens
    token_count = estimate_tokens(body)

    if dry_run:
        return {
            "status": "would_load",
            "title": title,
            "tokens": token_count,
            "method": "full" if token_count < MAX_TOKENS_FOR_FULL_EMBED else "chunked",
        }

    # Framework analysis (parapsychology)
    frameworks_payload = None
    frameworks_model = None
    if frameworks_enabled:
        result = analyze_story_frameworks(
            body,
            api_key=anthropic_api_key or "",
            model=anthropic_model,
        )
        frameworks_payload = result.to_json()
        frameworks_model = result.model

    # Generate embeddings
    if token_count < MAX_TOKENS_FOR_FULL_EMBED:
        # Embed full story
        embedding = get_embedding_with_retry(body, voyage_api_key)
        embedding_method = "full"
        chunk_embeddings = []
    else:
        # Chunk and embed (batch for efficiency)
        chunks = chunk_text(body)
        chunk_embeddings = get_embeddings_batch_with_retry(chunks, voyage_api_key)
        embedding = mean_pool_embeddings(chunk_embeddings)
        embedding_method = "mean_pooled"

    # Get or create episode
    with conn.cursor() as cur:
        # Check if episode exists
        cur.execute(
            "SELECT id FROM episodes WHERE podcast_name = %s AND air_date = %s",
            (show, episode_date),
        )
        row = cur.fetchone()
        if row:
            episode_id = row[0]
        else:
            cur.execute(
                """
                INSERT INTO episodes (title, podcast_name, air_date)
                VALUES (%s, %s, %s)
                RETURNING id
                """,
                (f"{show} - {episode_date}", show, episode_date),
            )
            episode_id = cur.fetchone()[0]

        # Check if story already exists
        cur.execute(
            """
            SELECT id FROM stories
            WHERE episode_id = %s AND title = %s AND start_time_seconds = %s
            """,
            (episode_id, title, start_time),
        )
        existing = cur.fetchone()
        if existing:
            story_id = existing[0]
            # Update existing
            cur.execute(
                """
                UPDATE stories SET
                    content = %s,
                    summary = NULL,
                    end_time_seconds = %s,
                    story_type = %s,
                    location = %s,
                    is_first_person = %s,
                    token_count = %s,
                    embedding_method = %s,
                    embedding = %s,
                    frameworks_json = COALESCE(%s::jsonb, frameworks_json),
                    frameworks_version = COALESCE(%s, frameworks_version),
                    frameworks_model = COALESCE(%s, frameworks_model),
                    frameworks_computed_at = CASE WHEN %s THEN now() ELSE frameworks_computed_at END,
                    updated_at = now()
                WHERE id = %s
                """,
                (
                    body,
                    end_time,
                    story_type,
                    location,
                    is_first_person,
                    token_count,
                    embedding_method,
                    embedding,
                    json.dumps(frameworks_payload, ensure_ascii=True) if frameworks_payload else None,
                    FRAMEWORK_SCHEMA_VERSION if frameworks_payload else None,
                    frameworks_model,
                    frameworks_payload is not None,
                    story_id,
                ),
            )
            action = "updated"
        else:
            # Insert new
            cur.execute(
                """
                INSERT INTO stories (
                    episode_id, title, content, start_time_seconds, end_time_seconds,
                    story_type, location, is_first_person, token_count, embedding_method, embedding,
                    frameworks_json, frameworks_version, frameworks_model, frameworks_computed_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s)
                RETURNING id
                """,
                (
                    episode_id,
                    title,
                    body,
                    start_time,
                    end_time,
                    story_type,
                    location,
                    is_first_person,
                    token_count,
                    embedding_method,
                    embedding,
                    json.dumps(frameworks_payload, ensure_ascii=True) if frameworks_payload else None,
                    FRAMEWORK_SCHEMA_VERSION if frameworks_payload else None,
                    frameworks_model,
                    datetime.utcnow() if frameworks_payload else None,
                ),
            )
            story_id = cur.fetchone()[0]
            action = "inserted"

        # If chunked, store chunk embeddings
        if embedding_method == "mean_pooled" and chunk_embeddings:
            # Delete existing chunks
            cur.execute("DELETE FROM story_chunks WHERE story_id = %s", (story_id,))

            chunks = chunk_text(body)
            for i, (chunk, chunk_emb) in enumerate(zip(chunks, chunk_embeddings)):
                cur.execute(
                    """
                    INSERT INTO story_chunks (story_id, chunk_index, content, token_count, embedding)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (story_id, i, chunk, estimate_tokens(chunk), chunk_emb),
                )

        conn.commit()

    return {
        "status": action,
        "title": title,
        "tokens": token_count,
        "method": embedding_method,
        "chunks": len(chunk_embeddings) if chunk_embeddings else 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Load segment markdown files into database with embeddings.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Environment:
  VOYAGE_API_KEY  - Voyage AI API key (required)
  ANTHROPIC_API_KEY - Anthropic API key (required for framework analysis)
  ANTHROPIC_MODEL   - Anthropic model override (default: claude-3-haiku-20240307)
  DATABASE_URL    - PostgreSQL URL
                    (default: postgresql://paranormal:paranormal@localhost:5433/paranormal_tracker)

Examples:
  %(prog)s                           # Load all segments
  %(prog)s --dry-run                 # Preview what would be loaded
  %(prog)s --file segments/show/x.md # Load single file
  %(prog)s --match "coast-to-coast"  # Filter by path
""",
    )

    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument(
        "--root",
        type=Path,
        default=DEFAULT_SEGMENTS_DIR,
        help=f"Root directory for segment files (default: {DEFAULT_SEGMENTS_DIR.relative_to(REPO_ROOT)})",
    )
    input_group.add_argument(
        "--file",
        type=Path,
        help="Single segment file to load",
    )

    parser.add_argument(
        "--match",
        action="append",
        default=[],
        help="Only process files containing this substring (repeatable)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of files to process",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be loaded without loading",
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress progress output",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Delay between files in seconds (default: 1.0, helps with rate limits)",
    )
    parser.add_argument(
        "--no-frameworks",
        action="store_true",
        help="Skip parapsychology framework analysis",
    )
    parser.add_argument(
        "--framework-model",
        type=str,
        default=None,
        help="Anthropic model override (defaults to ANTHROPIC_MODEL env)",
    )

    args = parser.parse_args()

    # Set up database connection
    try:
        import psycopg2
    except ImportError:
        raise SystemExit("Install psycopg2: pip install psycopg2-binary")

    database_url = get_database_url()

    # Get Voyage API key
    voyage_api_key = os.environ.get("VOYAGE_API_KEY")
    if not args.dry_run and not voyage_api_key:
        print("VOYAGE_API_KEY environment variable required", file=sys.stderr)
        return 1

    anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY")
    frameworks_enabled = not args.no_frameworks
    if not args.dry_run and frameworks_enabled and not anthropic_api_key:
        print("ANTHROPIC_API_KEY environment variable required for framework analysis", file=sys.stderr)
        return 1

    if not args.dry_run:
        try:
            conn = psycopg2.connect(database_url)
        except Exception as e:
            print(f"Database connection failed: {e}", file=sys.stderr)
            return 1
    else:
        conn = None

    if conn and frameworks_enabled:
        ensure_framework_columns(conn)

    # Collect files
    if args.file:
        if not args.file.exists():
            print(f"File not found: {args.file}", file=sys.stderr)
            return 1
        files = [args.file]
    else:
        if not args.root.exists():
            print(f"Root directory not found: {args.root}", file=sys.stderr)
            return 1
        files = list(iter_segment_files(args.root, args.match))

    if args.limit:
        files = files[:args.limit]

    if not files:
        print("No segment files found.")
        return 0

    # Process files
    total = len(files)
    loaded = 0
    skipped = 0
    errors = 0

    print(f"{'[DRY RUN] ' if args.dry_run else ''}Processing {total} segment(s)...")
    print()

    for i, file_path in enumerate(files):
        try:
            result = load_segment_to_db(
                file_path,
                conn,
                voyage_api_key,
                anthropic_api_key,
                args.framework_model,
                frameworks_enabled,
                dry_run=args.dry_run,
            )

            if result["status"] in ("inserted", "updated", "would_load"):
                loaded += 1
                if not args.quiet:
                    method_info = f" ({result['method']}, {result.get('chunks', 0)} chunks)" if result.get('chunks') else f" ({result['method']})"
                    print(f"  {result['status'].upper()}: {result['title']}{method_info}")
            else:
                skipped += 1
                if not args.quiet:
                    print(f"  SKIP: {file_path.name} - {result.get('reason', 'unknown')}")

        except Exception as e:
            errors += 1
            print(f"  ERROR: {file_path.name} - {e}", file=sys.stderr)

        # Rate limit delay between files (skip on last file)
        if not args.dry_run and i < len(files) - 1 and args.delay > 0:
            time.sleep(args.delay)

    if conn:
        conn.close()

    # Summary
    print()
    print("=" * 40)
    print(f"{'[DRY RUN] ' if args.dry_run else ''}Summary:")
    print(f"  Loaded: {loaded}")
    print(f"  Skipped: {skipped}")
    print(f"  Errors: {errors}")

    return 1 if errors > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
