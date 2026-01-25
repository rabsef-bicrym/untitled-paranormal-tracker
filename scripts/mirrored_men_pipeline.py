#!/usr/bin/env python3
"""Mirrored Men pipeline: fetch RSS, filter mirrored episodes, download audio, transcribe with Whisper.

Creates:
  episodes/mirrored-men/...
  transcripts/mirrored-men/...
  transcripts/mirrored-men/INDEX.md

Usage:
  source venv/bin/activate
  python scripts/mirrored_men_pipeline.py --download --transcribe

Notes:
  - Filters RSS items whose title contains 'mirrored' (case-insensitive).
  - Uses itunes:season and itunes:episode when available.
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

import requests

RSS_DEFAULT = "https://audioboom.com/channels/5147816.rss"

NS = {
    "itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd",
}


@dataclass
class Episode:
    title: str
    season: str
    episode: str
    pubdate_rfc2822: str
    pubdate_iso: str
    pubdate_slug: str
    link: str
    mp3_url: str

    def code(self) -> str:
        # handle 19.5 etc; keep verbatim
        s = self.season or "unknown"
        e = self.episode or "unknown"
        return f"s{s}e{e}"


def fetch_rss(url: str) -> ET.Element:
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return ET.fromstring(r.content)


def parse_pubdate(pub: str) -> tuple[str, str, str]:
    """Return (iso_date, slug_date, original)."""
    pub = (pub or "").strip()
    # Example: Thu, 15 Jan 2026 08:00:00 +0000
    try:
        dt = datetime.strptime(pub, "%a, %d %b %Y %H:%M:%S %z")
        iso = dt.date().isoformat()
        slug = dt.strftime("%d-%b-%Y")
        return iso, slug, pub
    except Exception:
        return "", "unknown", pub


def extract_episodes(root: ET.Element) -> list[Episode]:
    out: list[Episode] = []
    for item in root.findall(".//item"):
        title = item.findtext("title", default="Untitled")
        if "mirrored" not in title.lower():
            continue

        enc = item.find("enclosure")
        mp3_url = enc.get("url") if enc is not None else ""
        if not mp3_url:
            continue

        season = item.findtext("itunes:season", default="", namespaces=NS)
        ep = item.findtext("itunes:episode", default="", namespaces=NS)
        link = item.findtext("link", default="")
        pub = item.findtext("pubDate", default="")
        iso, slug, pub_orig = parse_pubdate(pub)

        out.append(
            Episode(
                title=title,
                season=season,
                episode=ep,
                pubdate_rfc2822=pub_orig,
                pubdate_iso=iso,
                pubdate_slug=slug,
                link=link,
                mp3_url=mp3_url,
            )
        )

    def sort_key(e: Episode):
        # season and episode can be non-int (e.g., 19.5). Sort numerically where possible.
        def num(x: str):
            try:
                return float(x)
            except Exception:
                return 0.0

        return (num(e.season), num(e.episode), e.pubdate_iso or "")

    out.sort(key=sort_key)
    return out


def safe_filename(s: str) -> str:
    s = s.strip().replace(" ", "_")
    s = re.sub(r"[^A-Za-z0-9._-]+", "", s)
    return s


def download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0) or 0)
        got = 0
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 256):
                if not chunk:
                    continue
                f.write(chunk)
                got += len(chunk)
                if total:
                    pct = got * 100 / total
                    print(f"    {pct:5.1f}%", end="\r", flush=True)
    if total:
        print(" " * 20, end="\r")


def run_whisper(audio_path: Path, out_dir: Path, model: str, language: str = "en") -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        "whisper",
        str(audio_path),
        "--model",
        model,
        "--language",
        language,
        "--output_dir",
        str(out_dir),
        "--output_format",
        "txt",
        "--output_format",
        "json",
        "--verbose",
        "False",
    ]
    # whisper supports multiple --output_format values; if not, it will error; fall back to txt only.
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError:
        cmd2 = [
            "whisper",
            str(audio_path),
            "--model",
            model,
            "--language",
            language,
            "--output_dir",
            str(out_dir),
            "--output_format",
            "txt",
            "--verbose",
            "False",
        ]
        subprocess.run(cmd2, check=True)


def write_index(episodes: Iterable[Episode], episodes_dir: Path, transcripts_dir: Path, index_path: Path) -> None:
    lines = []
    lines.append("# Mirrored Men episodes — Monsters Among Us")
    lines.append("")
    lines.append(f"Generated: {datetime.now().isoformat(timespec='seconds')}")
    lines.append("")
    lines.append("Columns: Season/Episode, Date, Title, Audioboom link, Audio file, Transcript")
    lines.append("")

    for ep in episodes:
        base = f"mau_{ep.code()}_{ep.pubdate_slug}"
        mp3 = episodes_dir / f"{base}.mp3"
        txt = transcripts_dir / f"{base}.txt"
        js = transcripts_dir / f"{base}.json"

        audio_rel = mp3.as_posix()
        txt_rel = txt.as_posix()
        json_rel = js.as_posix()

        lines.append(f"- **S{ep.season} Ep{ep.episode}** — {ep.pubdate_iso or ep.pubdate_slug}")
        lines.append(f"  - Title: {ep.title}")
        if ep.link:
            lines.append(f"  - Audioboom: {ep.link}")
        lines.append(f"  - MP3: `{audio_rel}`")
        if txt.exists():
            lines.append(f"  - Transcript (txt): `{txt_rel}`")
        if js.exists():
            lines.append(f"  - Transcript (json): `{json_rel}`")
        lines.append("")

    index_path.write_text("\n".join(lines), encoding="utf-8")

    # Also emit machine-readable CSV
    csv_path = index_path.with_suffix(".csv")
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["season", "episode", "date", "title", "audioboom_link", "mp3_url", "mp3_path", "transcript_txt", "transcript_json"])
        for ep in episodes:
            base = f"mau_{ep.code()}_{ep.pubdate_slug}"
            mp3 = episodes_dir / f"{base}.mp3"
            txt = transcripts_dir / f"{base}.txt"
            js = transcripts_dir / f"{base}.json"
            w.writerow([
                ep.season,
                ep.episode,
                ep.pubdate_iso,
                ep.title,
                ep.link,
                ep.mp3_url,
                str(mp3),
                str(txt),
                str(js),
            ])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rss", default=RSS_DEFAULT)
    ap.add_argument("--download", action="store_true")
    ap.add_argument("--transcribe", action="store_true")
    ap.add_argument("--model", default=os.environ.get("WHISPER_MODEL", "base"), help="Whisper model (default: base; override with WHISPER_MODEL)")
    ap.add_argument("--delay", type=float, default=2.0, help="Delay between downloads (seconds)")
    args = ap.parse_args()

    repo = Path(__file__).resolve().parents[1]
    episodes_dir = repo / "episodes" / "mirrored-men"
    transcripts_dir = repo / "transcripts" / "mirrored-men"
    index_path = transcripts_dir / "INDEX.md"

    print(f"Fetching RSS: {args.rss}")
    root = fetch_rss(args.rss)
    eps = extract_episodes(root)
    print(f"Matched {len(eps)} episodes with 'mirrored' in title")

    if not args.download and not args.transcribe:
        print("Nothing to do (pass --download and/or --transcribe)")

    if args.download:
        episodes_dir.mkdir(parents=True, exist_ok=True)
        for i, ep in enumerate(eps, 1):
            base = f"mau_{ep.code()}_{ep.pubdate_slug}"
            mp3_path = episodes_dir / f"{base}.mp3"
            print(f"[{i}/{len(eps)}] Download: {ep.title}")
            if mp3_path.exists() and mp3_path.stat().st_size > 0:
                print("  Skipping (exists)")
                continue
            print(f"  -> {mp3_path}")
            download(ep.mp3_url, mp3_path)
            time.sleep(args.delay)

    if args.transcribe:
        transcripts_dir.mkdir(parents=True, exist_ok=True)
        for i, ep in enumerate(eps, 1):
            base = f"mau_{ep.code()}_{ep.pubdate_slug}"
            mp3_path = episodes_dir / f"{base}.mp3"
            if not mp3_path.exists():
                print(f"[{i}/{len(eps)}] Missing audio, skipping: {mp3_path}")
                continue
            txt_path = transcripts_dir / f"{base}.txt"
            if txt_path.exists() and txt_path.stat().st_size > 0:
                print(f"[{i}/{len(eps)}] Transcription exists, skipping: {txt_path.name}")
                continue
            print(f"[{i}/{len(eps)}] Whisper transcribe ({args.model}): {mp3_path.name}")
            run_whisper(mp3_path, transcripts_dir, model=args.model)

    write_index(eps, episodes_dir, transcripts_dir, index_path)
    print(f"Wrote index: {index_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
