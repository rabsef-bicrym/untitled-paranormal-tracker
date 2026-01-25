#!/usr/bin/env python3
"""
Download episodes from Monsters Among Us RSS feed.

Usage:
    python scripts/download_rss.py --limit 5
    python scripts/download_rss.py --all
"""

import argparse
import os
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlparse
import requests


def fetch_rss(url):
    """Fetch and parse RSS feed."""
    print(f"Fetching RSS feed from {url}...")
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return ET.fromstring(response.content)


def extract_episodes(root):
    """Extract episode info from RSS XML."""
    episodes = []

    # Define namespaces
    ns = {
        'itunes': 'http://www.itunes.com/dtds/podcast-1.0.dtd',
        'content': 'http://purl.org/rss/1.0/modules/content/'
    }

    for item in root.findall('.//item'):
        title_elem = item.find('title')
        enclosure_elem = item.find('enclosure')
        pubdate_elem = item.find('pubDate')
        season_elem = item.find('itunes:season', ns)
        episode_elem = item.find('itunes:episode', ns)

        if enclosure_elem is not None and enclosure_elem.get('url'):
            mp3_url = enclosure_elem.get('url')

            # Parse publication date (e.g., "Thu, 15 Jan 2026 08:00:00 +0000")
            pubdate_str = pubdate_elem.text if pubdate_elem is not None else ""

            # Extract simple date (DD Mon YYYY)
            date_parts = pubdate_str.split()
            if len(date_parts) >= 4:
                day = date_parts[1]
                month = date_parts[2]
                year = date_parts[3]
                simple_date = f"{day}-{month}-{year}"
            else:
                simple_date = "unknown"

            episodes.append({
                'title': title_elem.text if title_elem is not None else "Untitled",
                'mp3_url': mp3_url,
                'pubdate': simple_date,
                'season': season_elem.text if season_elem is not None else "unknown",
                'episode': episode_elem.text if episode_elem is not None else "unknown"
            })

    return episodes


def download_mp3(url, output_path):
    """Download MP3 file with progress."""
    print(f"  Downloading to {output_path}...")

    response = requests.get(url, stream=True, timeout=60)
    response.raise_for_status()

    total_size = int(response.headers.get('content-length', 0))
    downloaded = 0

    with open(output_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
                downloaded += len(chunk)
                if total_size > 0:
                    pct = (downloaded / total_size) * 100
                    print(f"  Progress: {pct:.1f}%", end='\r')

    print(f"  Download complete: {downloaded / (1024*1024):.1f} MB")


def main():
    parser = argparse.ArgumentParser(description="Download Monsters Among Us episodes from RSS")
    parser.add_argument('--rss', default='https://audioboom.com/channels/5147816.rss',
                        help='RSS feed URL')
    parser.add_argument('--limit', type=int, default=None,
                        help='Maximum number of episodes to download')
    parser.add_argument('--all', action='store_true',
                        help='Download all episodes from feed')
    parser.add_argument('--episodes-dir', default='episodes',
                        help='Directory to save episodes')

    args = parser.parse_args()

    # Create episodes directory
    episodes_dir = Path(args.episodes_dir)
    episodes_dir.mkdir(exist_ok=True)

    # Fetch RSS feed
    try:
        root = fetch_rss(args.rss)
    except Exception as e:
        print(f"Error fetching RSS feed: {e}", file=sys.stderr)
        return 1

    # Extract episodes
    episodes = extract_episodes(root)
    print(f"Found {len(episodes)} episodes in feed")

    # Limit if requested
    if args.limit:
        episodes = episodes[:args.limit]
        print(f"Limited to {args.limit} episodes")

    # Download episodes
    downloaded = 0
    skipped = 0

    for i, ep in enumerate(episodes, 1):
        # Generate filename from URL (use the unique ID in the audioboom URL)
        parsed = urlparse(ep['mp3_url'])
        # Extract UUID-like identifier from the URL path
        filename = f"mau_s{ep['season']}e{ep['episode']}_{ep['pubdate']}.mp3"
        filename = filename.replace(' ', '_').replace(',', '')
        output_path = episodes_dir / filename

        print(f"\n[{i}/{len(episodes)}] {ep['title']}")
        print(f"  Season {ep['season']}, Episode {ep['episode']}")
        print(f"  Date: {ep['pubdate']}")

        if output_path.exists():
            print(f"  Skipping: already exists")
            skipped += 1
            continue

        try:
            download_mp3(ep['mp3_url'], output_path)
            downloaded += 1

            # Be respectful to the server
            if i < len(episodes):
                time.sleep(2)
        except Exception as e:
            print(f"  Error downloading: {e}", file=sys.stderr)
            continue

    print(f"\n{'='*60}")
    print(f"Summary:")
    print(f"  Downloaded: {downloaded}")
    print(f"  Skipped (already exist): {skipped}")
    print(f"  Total processed: {len(episodes)}")
    print(f"  Files in {episodes_dir}: {len(list(episodes_dir.glob('*.mp3')))}")

    return 0


if __name__ == '__main__':
    sys.exit(main())
