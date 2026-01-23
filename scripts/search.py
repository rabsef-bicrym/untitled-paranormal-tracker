#!/usr/bin/env python3
"""
Search stories using hybrid (text + vector) search.

Usage:
  python scripts/search.py "shadow figure bedroom"
  python scripts/search.py "UFO triangle" --limit 5
  python scripts/search.py "ghost" --text-only
  python scripts/search.py "strange lights" --vector-only

Environment:
  VOYAGE_API_KEY  - For vector search (embeddings)
  DATABASE_URL    - PostgreSQL URL
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent

DEFAULT_DATABASE_URL = "postgresql://paranormal:paranormal@localhost:5433/paranormal_tracker"
VOYAGE_MODEL = "voyage-4-large"
VOYAGE_API_URL = "https://api.voyageai.com/v1/embeddings"


def get_database_url() -> str:
    return os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)


def get_query_embedding(query: str, api_key: str, max_retries: int = 5) -> list[float]:
    """Get embedding for search query via Voyage AI with retry."""
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
                "input": [query],
            },
        )

        if response.status_code == 429:
            wait_time = 2 ** attempt
            print(f"Rate limited, waiting {wait_time}s...", file=sys.stderr)
            time.sleep(wait_time)
            continue

        response.raise_for_status()
        result = response.json()
        return result["data"][0]["embedding"]

    raise Exception("Max retries exceeded")


def text_search(conn, query: str, limit: int = 10) -> list[dict]:
    """Full-text search using PostgreSQL tsvector."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                s.id, s.title, s.story_type, s.location,
                e.podcast_name, e.air_date,
                ts_rank(s.search_vector, plainto_tsquery('english', %s)) as rank,
                substring(s.content, 1, 200) as snippet
            FROM stories s
            JOIN episodes e ON s.episode_id = e.id
            WHERE s.search_vector @@ plainto_tsquery('english', %s)
            ORDER BY rank DESC
            LIMIT %s
            """,
            (query, query, limit),
        )
        columns = [desc[0] for desc in cur.description]
        return [dict(zip(columns, row)) for row in cur.fetchall()]


def vector_search(conn, query_embedding: list[float], limit: int = 10) -> list[dict]:
    """Vector similarity search using pgvector."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                s.id, s.title, s.story_type, s.location,
                e.podcast_name, e.air_date,
                1 - (s.embedding <=> %s::vector) as similarity,
                substring(s.content, 1, 200) as snippet
            FROM stories s
            JOIN episodes e ON s.episode_id = e.id
            WHERE s.embedding IS NOT NULL
            ORDER BY s.embedding <=> %s::vector
            LIMIT %s
            """,
            (query_embedding, query_embedding, limit),
        )
        columns = [desc[0] for desc in cur.description]
        return [dict(zip(columns, row)) for row in cur.fetchall()]


def hybrid_search(
    conn,
    query: str,
    query_embedding: list[float],
    limit: int = 10,
    alpha: float = 0.7,
) -> list[dict]:
    """
    Hybrid search combining text and vector results.

    Alpha controls blend: 1.0 = all vector, 0.0 = all text.
    """
    # Get both result sets
    text_results = text_search(conn, query, limit * 2)
    vector_results = vector_search(conn, query_embedding, limit * 2)

    # Build score maps
    text_scores = {r["id"]: r.get("rank", 0) for r in text_results}
    vector_scores = {r["id"]: r.get("similarity", 0) for r in vector_results}

    # Normalize scores
    max_text = max(text_scores.values()) if text_scores else 1
    max_vector = max(vector_scores.values()) if vector_scores else 1

    text_scores = {k: v / max_text if max_text else 0 for k, v in text_scores.items()}
    vector_scores = {k: v / max_vector if max_vector else 0 for k, v in vector_scores.items()}

    # Combine results
    all_ids = set(text_scores.keys()) | set(vector_scores.keys())
    combined = []

    # Build lookup for full results
    result_lookup = {r["id"]: r for r in text_results + vector_results}

    for id_ in all_ids:
        text_score = text_scores.get(id_, 0)
        vector_score = vector_scores.get(id_, 0)
        hybrid_score = alpha * vector_score + (1 - alpha) * text_score

        result = result_lookup[id_].copy()
        result["hybrid_score"] = hybrid_score
        result["text_score"] = text_score
        result["vector_score"] = vector_score
        combined.append(result)

    combined.sort(key=lambda x: x["hybrid_score"], reverse=True)
    return combined[:limit]


def format_result(result: dict, index: int) -> str:
    """Format a search result for display."""
    lines = [
        f"{index}. {result['title']}",
        f"   Show: {result['podcast_name']} ({result['air_date']})",
    ]

    if result.get("story_type"):
        lines.append(f"   Type: {result['story_type']}")
    if result.get("location"):
        lines.append(f"   Location: {result['location']}")

    # Score info
    scores = []
    if "hybrid_score" in result:
        scores.append(f"hybrid={result['hybrid_score']:.3f}")
    if "similarity" in result:
        scores.append(f"vector={result['similarity']:.3f}")
    if "rank" in result:
        scores.append(f"text={result['rank']:.3f}")
    if scores:
        lines.append(f"   Score: {', '.join(scores)}")

    # Snippet
    snippet = result.get("snippet", "")
    if snippet:
        snippet = snippet.replace("\n", " ")[:150]
        lines.append(f"   \"{snippet}...\"")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Search paranormal stories using hybrid text + vector search.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "shadow figure"
  %(prog)s "UFO triangle lights" --limit 5
  %(prog)s "ghost" --text-only
  %(prog)s "strange presence" --vector-only --alpha 1.0
""",
    )

    parser.add_argument(
        "query",
        help="Search query",
    )
    parser.add_argument(
        "--limit", "-n",
        type=int,
        default=10,
        help="Maximum results to return (default: 10)",
    )
    parser.add_argument(
        "--alpha",
        type=float,
        default=0.7,
        help="Blend factor: 1.0=vector only, 0.0=text only (default: 0.7)",
    )
    parser.add_argument(
        "--text-only",
        action="store_true",
        help="Use only text search (no embeddings needed)",
    )
    parser.add_argument(
        "--vector-only",
        action="store_true",
        help="Use only vector search",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )

    args = parser.parse_args()

    # Database connection
    try:
        import psycopg2
    except ImportError:
        raise SystemExit("Install psycopg2: pip install psycopg2-binary")

    try:
        conn = psycopg2.connect(get_database_url())
    except Exception as e:
        print(f"Database connection failed: {e}", file=sys.stderr)
        return 1

    # Get query embedding if needed
    query_embedding = None
    if not args.text_only:
        voyage_api_key = os.environ.get("VOYAGE_API_KEY")
        if not voyage_api_key:
            if args.vector_only:
                raise SystemExit("VOYAGE_API_KEY environment variable required for vector search")
            print("Warning: VOYAGE_API_KEY not set, falling back to text-only search", file=sys.stderr)
            args.text_only = True
        else:
            try:
                query_embedding = get_query_embedding(args.query, voyage_api_key)
            except Exception as e:
                if args.vector_only:
                    print(f"Failed to get query embedding: {e}", file=sys.stderr)
                    return 1
                print(f"Warning: embedding failed ({e}), falling back to text-only", file=sys.stderr)
                args.text_only = True

    # Search
    if args.text_only:
        results = text_search(conn, args.query, args.limit)
    elif args.vector_only:
        results = vector_search(conn, query_embedding, args.limit)
    else:
        results = hybrid_search(conn, args.query, query_embedding, args.limit, args.alpha)

    conn.close()

    if not results:
        print("No results found.")
        return 0

    # Output
    if args.json:
        # Convert dates to strings for JSON
        for r in results:
            if r.get("air_date"):
                r["air_date"] = str(r["air_date"])
        print(json.dumps(results, indent=2))
    else:
        print(f"Found {len(results)} result(s) for: {args.query}")
        print()
        for i, result in enumerate(results, 1):
            print(format_result(result, i))
            print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
