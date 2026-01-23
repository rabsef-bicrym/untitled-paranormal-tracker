#!/usr/bin/env python3
"""
Transcribe podcast MP3 using AssemblyAI with speaker diarization.

Outputs two files:
  1. {name}.json - Full AssemblyAI response with word-level timestamps
  2. {name}.txt  - Plain text transcript with speaker labels and line numbers

The .txt is designed for Claude to read efficiently. The .json is used by
extract_segment.py to look up precise timestamps.

Usage:
  python scripts/transcribe.py episodes/show_2024-01-15.mp3
  python scripts/transcribe.py episodes/show_2024-01-15.mp3 --output transcripts/
  python scripts/transcribe.py --url "https://example.com/episode.mp3"

Environment:
  ASSEMBLYAI_API_KEY - Required API key for AssemblyAI
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent

DEFAULT_OUTPUT = REPO_ROOT / "transcripts"


def get_api_key() -> str:
    """Get AssemblyAI API key from environment."""
    key = os.environ.get("ASSEMBLYAI_API_KEY")
    if not key:
        raise SystemExit(
            "Missing ASSEMBLYAI_API_KEY environment variable.\n"
            "Get your API key at: https://www.assemblyai.com/dashboard/signup"
        )
    return key


def transcribe(audio_source: str, api_key: str) -> dict:
    """Transcribe audio using AssemblyAI with speaker diarization."""
    try:
        import assemblyai as aai
    except ImportError:
        raise SystemExit("Install assemblyai: pip install assemblyai")

    aai.settings.api_key = api_key

    config = aai.TranscriptionConfig(speaker_labels=True)
    transcriber = aai.Transcriber()

    print(f"Submitting to AssemblyAI...", flush=True)
    transcript = transcriber.transcribe(audio_source, config)

    if transcript.status == aai.TranscriptStatus.error:
        raise RuntimeError(f"Transcription failed: {transcript.error}")

    # Convert to serializable dict
    result = {
        "id": transcript.id,
        "status": str(transcript.status),
        "text": transcript.text,
        "confidence": transcript.confidence,
        "audio_duration": transcript.audio_duration,
        "words": [
            {
                "text": w.text,
                "start": w.start,
                "end": w.end,
                "confidence": w.confidence,
                "speaker": getattr(w, "speaker", None),
            }
            for w in (transcript.words or [])
        ],
        "utterances": [
            {
                "text": u.text,
                "start": u.start,
                "end": u.end,
                "confidence": u.confidence,
                "speaker": u.speaker,
            }
            for u in (transcript.utterances or [])
        ],
        "audio_url": transcript.audio_url,
        "created_at": datetime.now().isoformat(),
    }

    return result


def format_transcript_txt(data: dict) -> str:
    """
    Format transcript as plain text with line numbers and speaker labels.

    Output format (one utterance per line, numbered for easy reference):

        1: [Speaker A] First thing the speaker said...
        2: [Speaker B] Response from another speaker...
        3: [Speaker A] And so on...

    Claude reads this to identify stories, then references line numbers.
    """
    lines = []
    utterances = data.get("utterances", [])

    if not utterances:
        # Fallback to plain text if no utterances
        return data.get("text", "")

    for i, u in enumerate(utterances, start=1):
        speaker = u.get("speaker", "?")
        text = u.get("text", "").strip()
        lines.append(f"{i}: [Speaker {speaker}] {text}")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Transcribe audio with AssemblyAI, output JSON + TXT.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Output Files:
  {name}.json  - Full AssemblyAI response with word-level timestamps
  {name}.txt   - Plain text with speaker labels and line numbers

Environment:
  ASSEMBLYAI_API_KEY    Required

Examples:
  %(prog)s episodes/show_2024-01-15.mp3
  %(prog)s episodes/show_2024-01-15.mp3 -o transcripts/
  %(prog)s --url "https://example.com/ep.mp3" --name my_episode
""",
    )

    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "file",
        nargs="?",
        type=Path,
        help="Path to audio file (MP3, WAV, etc.)",
    )
    input_group.add_argument(
        "--url",
        help="URL to audio file",
    )

    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output directory (default: {DEFAULT_OUTPUT.relative_to(REPO_ROOT)})",
    )
    parser.add_argument(
        "--name",
        help="Base name for output files (default: derived from input)",
    )

    args = parser.parse_args()

    api_key = get_api_key()

    # Determine source and output name
    if args.file:
        if not args.file.exists():
            print(f"File not found: {args.file}", file=sys.stderr)
            return 1
        source = str(args.file)
        name = args.name or args.file.stem
    else:
        source = args.url
        name = args.name or args.url.split("/")[-1].split("?")[0].rsplit(".", 1)[0] or "transcript"

    # Transcribe
    print(f"Transcribing: {source}")
    data = transcribe(source, api_key)

    # Write outputs
    args.output.mkdir(parents=True, exist_ok=True)

    json_path = args.output / f"{name}.json"
    txt_path = args.output / f"{name}.txt"

    json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    txt_path.write_text(format_transcript_txt(data))

    # Summary
    duration = data.get("audio_duration", 0)
    utterances = len(data.get("utterances", []))
    speakers = len(set(u.get("speaker") for u in data.get("utterances", [])))

    print()
    print(f"Done!")
    print(f"  Duration: {duration:.0f}s ({duration/60:.1f} min)")
    print(f"  Utterances: {utterances}")
    print(f"  Speakers: {speakers}")
    print()
    print(f"Output:")
    print(f"  {json_path}")
    print(f"  {txt_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
