#!/usr/bin/env python3
"""
Batch transcribe all episodes that don't have transcripts yet.

Finds all .mp3 files in episodes/ and subdirectories, checks which ones
lack corresponding .json transcripts, and transcribes them sequentially.

Usage:
  python scripts/batch_transcribe.py
  python scripts/batch_transcribe.py --dry-run
"""

import argparse
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
EPISODES_DIR = REPO_ROOT / "episodes"
TRANSCRIPTS_DIR = REPO_ROOT / "transcripts"


def find_untranscribed_episodes():
    """Find all MP3 files without corresponding JSON transcripts."""
    # Find all MP3 files
    mp3_files = list(EPISODES_DIR.rglob("*.mp3"))

    # Check which ones lack transcripts
    untranscribed = []
    for mp3_path in mp3_files:
        # Determine what the transcript filename would be
        transcript_name = mp3_path.stem + ".json"
        transcript_path = TRANSCRIPTS_DIR / transcript_name

        if not transcript_path.exists():
            untranscribed.append(mp3_path)

    return sorted(untranscribed)


def transcribe_episode(mp3_path):
    """Transcribe a single episode using transcribe.py."""
    cmd = [
        sys.executable,
        str(SCRIPT_DIR / "transcribe.py"),
        str(mp3_path)
    ]

    print(f"\n{'='*80}")
    print(f"Transcribing: {mp3_path.relative_to(REPO_ROOT)}")
    print(f"{'='*80}\n")

    result = subprocess.run(cmd)

    if result.returncode != 0:
        print(f"\n❌ FAILED: {mp3_path.name}", file=sys.stderr)
        return False

    print(f"\n✅ SUCCESS: {mp3_path.name}\n")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Batch transcribe all episodes without transcripts"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be transcribed without doing it"
    )
    args = parser.parse_args()

    # Find episodes to transcribe
    episodes = find_untranscribed_episodes()

    if not episodes:
        print("✅ All episodes already transcribed!")
        return 0

    print(f"Found {len(episodes)} episodes to transcribe:\n")
    for i, ep in enumerate(episodes, 1):
        print(f"  {i:2d}. {ep.relative_to(REPO_ROOT)}")

    if args.dry_run:
        print(f"\n[DRY RUN] Would transcribe {len(episodes)} episodes")
        return 0

    print(f"\nStarting batch transcription...")

    # Transcribe each episode
    success_count = 0
    failed = []

    for i, ep in enumerate(episodes, 1):
        print(f"\n[{i}/{len(episodes)}]")

        if transcribe_episode(ep):
            success_count += 1
        else:
            failed.append(ep)

    # Summary
    print(f"\n{'='*80}")
    print(f"BATCH TRANSCRIPTION COMPLETE")
    print(f"{'='*80}")
    print(f"✅ Successful: {success_count}/{len(episodes)}")

    if failed:
        print(f"❌ Failed: {len(failed)}")
        for ep in failed:
            print(f"   - {ep.relative_to(REPO_ROOT)}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
