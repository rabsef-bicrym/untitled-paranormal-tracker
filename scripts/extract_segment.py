#!/usr/bin/env python3
"""
Extract a story segment from a transcript and write it as a markdown file.

Given line numbers (from the .txt transcript), this script:
  1. Extracts the verbatim text for those lines
  2. Looks up precise timestamps from the .json
  3. Writes a .md file with frontmatter and content

Usage:
  python scripts/extract_segment.py \\
    --transcript transcripts/show_2024-01-15.json \\
    --lines 45-120 \\
    --title "Shadow Figure in Childhood Bedroom" \\
    --show "Coast to Coast AM" \\
    --date 2024-01-15

  # With optional metadata
  python scripts/extract_segment.py \\
    --transcript transcripts/show_2024-01-15.json \\
    --lines 45-120 \\
    --title "Shadow Figure in Childhood Bedroom" \\
    --show "Coast to Coast AM" \\
    --date 2024-01-15 \\
    --caller "Mike from Ohio" \\
    --type shadow_person \\
    --location "Ohio" \\
    --first-person

Output:
  segments/{show}/{date}_{title-slugified}.md
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent

DEFAULT_SEGMENTS_DIR = REPO_ROOT / "segments"


def slugify(text: str) -> str:
    """Convert text to filesystem-safe slug."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'-+', '-', text)
    return text[:60].rstrip('-')


def parse_line_range(spec: str) -> tuple[int, int]:
    """Parse a line range spec like '45-120' into (start, end)."""
    if '-' in spec:
        parts = spec.split('-', 1)
        return int(parts[0]), int(parts[1])
    else:
        n = int(spec)
        return n, n


def load_transcript(json_path: Path) -> dict:
    """Load the AssemblyAI transcript JSON."""
    return json.loads(json_path.read_text())


def extract_utterances(data: dict, start_line: int, end_line: int) -> list[dict]:
    """
    Extract utterances for the given line range.

    Lines are 1-indexed (matching the .txt output).
    """
    utterances = data.get("utterances", [])
    # Lines are 1-indexed, list is 0-indexed
    return utterances[start_line - 1 : end_line]


def get_timestamps(utterances: list[dict]) -> tuple[float, float]:
    """Get start/end timestamps (in seconds) from utterances."""
    if not utterances:
        return 0.0, 0.0

    # AssemblyAI timestamps are in milliseconds
    start_ms = utterances[0].get("start", 0)
    end_ms = utterances[-1].get("end", 0)

    return start_ms / 1000.0, end_ms / 1000.0


def format_timestamp(seconds: float) -> str:
    """Format seconds as HH:MM:SS or MM:SS."""
    total_seconds = int(seconds)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60

    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes}:{secs:02d}"


def format_content(utterances: list[dict]) -> str:
    """
    Format utterances as verbatim transcript text.

    Preserves speaker labels and exact text.
    """
    lines = []
    for u in utterances:
        speaker = u.get("speaker", "?")
        text = u.get("text", "").strip()
        lines.append(f"[Speaker {speaker}] {text}")
    return "\n\n".join(lines)


def write_segment(
    output_path: Path,
    title: str,
    show: str,
    episode_date: date,
    start_time: float,
    end_time: float,
    content: str,
    caller: str | None = None,
    story_type: str | None = None,
    location: str | None = None,
    is_first_person: bool = True,
    source_lines: str | None = None,
) -> None:
    """Write the segment markdown file with frontmatter."""

    # Build frontmatter
    fm_lines = [
        "---",
        f"title: \"{title}\"",
        f"show: \"{show}\"",
        f"date: {episode_date.isoformat()}",
        f"timestamp_start: {start_time:.1f}",
        f"timestamp_end: {end_time:.1f}",
        f"timestamp_display: \"{format_timestamp(start_time)} - {format_timestamp(end_time)}\"",
    ]

    if caller:
        fm_lines.append(f"caller: \"{caller}\"")
    if story_type:
        fm_lines.append(f"type: \"{story_type}\"")
    if location:
        fm_lines.append(f"location: \"{location}\"")
    if source_lines:
        fm_lines.append(f"source_lines: \"{source_lines}\"")

    fm_lines.append(f"first_person: {str(is_first_person).lower()}")
    fm_lines.append("---")

    frontmatter = "\n".join(fm_lines)

    # Write file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(f"{frontmatter}\n\n{content}\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract a story segment from transcript to markdown file.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s -t transcripts/show.json -l 45-120 --title "Shadow Figure" --show "C2C" --date 2024-01-15
  %(prog)s -t transcripts/show.json -l 45-120 --title "Shadow Figure" --show "C2C" --date 2024-01-15 --caller "Mike" --type shadow_person

Output:
  segments/{show}/{date}_{title-slug}.md
""",
    )

    parser.add_argument(
        "-t", "--transcript",
        type=Path,
        required=True,
        help="Path to transcript JSON file",
    )
    parser.add_argument(
        "-l", "--lines",
        required=True,
        help="Line range to extract (e.g., '45-120' or '45')",
    )
    parser.add_argument(
        "--title",
        required=True,
        help="Title for the segment (used in filename and frontmatter)",
    )
    parser.add_argument(
        "--show",
        required=True,
        help="Show/podcast name",
    )
    parser.add_argument(
        "--date",
        required=True,
        type=lambda s: date.fromisoformat(s),
        help="Episode date (YYYY-MM-DD)",
    )

    # Optional metadata
    parser.add_argument(
        "--caller",
        help="Caller name if mentioned",
    )
    parser.add_argument(
        "--type",
        dest="story_type",
        help="Story type (ghost, cryptid, ufo, shadow_person, etc.)",
    )
    parser.add_argument(
        "--location",
        help="Location mentioned in story",
    )
    parser.add_argument(
        "--first-person",
        action="store_true",
        default=True,
        help="Mark as first-person account (default: true)",
    )
    parser.add_argument(
        "--secondhand",
        action="store_true",
        help="Mark as secondhand account (sets first_person=false)",
    )

    # Output options
    parser.add_argument(
        "-o", "--output-dir",
        type=Path,
        default=DEFAULT_SEGMENTS_DIR,
        help=f"Base output directory (default: {DEFAULT_SEGMENTS_DIR.relative_to(REPO_ROOT)})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be written without writing",
    )

    args = parser.parse_args()

    # Validate inputs
    if not args.transcript.exists():
        print(f"Transcript not found: {args.transcript}", file=sys.stderr)
        return 1

    # Load transcript
    data = load_transcript(args.transcript)

    # Parse line range
    start_line, end_line = parse_line_range(args.lines)

    # Extract utterances
    utterances = extract_utterances(data, start_line, end_line)
    if not utterances:
        print(f"No utterances found for lines {start_line}-{end_line}", file=sys.stderr)
        return 1

    # Get timestamps and content
    start_time, end_time = get_timestamps(utterances)
    content = format_content(utterances)

    # Determine output path
    show_slug = slugify(args.show)
    title_slug = slugify(args.title)
    output_path = args.output_dir / show_slug / f"{args.date.isoformat()}_{title_slug}.md"

    is_first_person = not args.secondhand

    if args.dry_run:
        print(f"Would write: {output_path}")
        print(f"  Lines: {start_line}-{end_line}")
        print(f"  Timestamp: {format_timestamp(start_time)} - {format_timestamp(end_time)}")
        print(f"  Content length: {len(content)} chars")
        print(f"  First-person: {is_first_person}")
        return 0

    # Write segment
    write_segment(
        output_path=output_path,
        title=args.title,
        show=args.show,
        episode_date=args.date,
        start_time=start_time,
        end_time=end_time,
        content=content,
        caller=args.caller,
        story_type=args.story_type,
        location=args.location,
        is_first_person=is_first_person,
        source_lines=args.lines,
    )

    print(f"Created: {output_path}")
    print(f"  Timestamp: {format_timestamp(start_time)} - {format_timestamp(end_time)}")
    print(f"  Duration: {end_time - start_time:.0f}s")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
