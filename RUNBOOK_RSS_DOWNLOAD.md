# Monsters Among Us RSS Download & Processing Runbook

## Overview

This runbook documents the automated download and processing pipeline for Monsters Among Us podcast episodes from their RSS feed.

## Prerequisites

```bash
# Activate virtual environment
source /Users/rabsef-bicrym/Development/personal/projects/untitled-paranormal-tracker/venv/bin/activate

# Load environment variables
export $(cat /Users/rabsef-bicrym/Development/personal/projects/untitled-paranormal-tracker/.env | xargs)
```

## Step 1: Download Episodes from RSS

```bash
# Download latest 5 episodes
python scripts/download_rss.py --limit 5

# Download all episodes in feed (550+ episodes available)
python scripts/download_rss.py --all

# Download with custom delay between episodes
python scripts/download_rss.py --limit 10 --delay 3.0
```

### RSS Feed Details
- **URL**: https://audioboom.com/channels/5147816.rss
- **Episodes in feed**: 550+ (as of Jan 2026)
- **File naming**: `mau_s{season}e{episode}_{date}.mp3`
- **Output directory**: `episodes/`

## Step 2: Transcribe Episodes

```bash
# Transcribe individual episode
python scripts/transcribe.py episodes/mau_s20e28_15-Jan-2026.mp3

# Transcribe multiple episodes (run sequentially)
for ep in episodes/mau_s20e*.mp3; do
    python scripts/transcribe.py "$ep"
done
```

### Transcription Output
- JSON file: `transcripts/{filename}.json` (timestamped data)
- TXT file: `transcripts/{filename}.txt` (line-numbered readable format)

## Step 3: Extract Story Segments

### Manual Process (Current Workflow)

1. Read the `.txt` transcript
2. Identify **first-person** paranormal stories (reject second-hand stories)
3. Note line numbers, titles, caller info, story type, location

4. Extract each story:

```bash
python scripts/extract_segment.py \
  -t transcripts/mau_s20e28_15-Jan-2026.json \
  -l 5-5 \
  --title "Pickle Jar Flies Off Fridge" \
  --show "Monsters Among Us" \
  --date 2026-01-15 \
  --caller "Alicia from Texas" \
  --type poltergeist \
  --location "Houston area, Texas"
```

### Story Type Reference

See `CLAUDE.md` for complete list. Common types:
- `ghost`, `shadow_person`, `haunting`
- `ufo`, `alien_encounter`
- `cryptid`, `poltergeist`
- `obe`, `nde`, `precognition`
- `sleep_paralysis`, `possession`
- `other`

## Step 4: Load Segments to Database

```bash
# Load all new segments with rate limiting
python scripts/load_segments.py --delay 1

# Increase delay if hitting Voyage AI rate limits
python scripts/load_segments.py --delay 3.0
```

## Step 5: Verify Database Load

```bash
# Check story count
PGPASSWORD=paranormal psql -h localhost -p 5433 -U paranormal -d paranormal_tracker -c "SELECT COUNT(*) FROM stories;"

# Search for newly loaded stories
python scripts/search.py "shadow figure" --limit 10
```

## File Cleanup (Optional)

After successful database load, temp files can be removed:

```bash
# Remove episode MP3s (keep segments as source of truth)
rm episodes/mau_s20e*.mp3

# Remove transcript files (segments contain the extracted stories)
rm transcripts/mau_s20e*.json
rm transcripts/mau_s20e*.txt
```

## Automation Opportunities

### Future Improvements

1. **Auto-segmentation**: Use LLM to identify first-person stories from transcripts
2. **Batch processing**: Download → Transcribe → Extract pipeline for multiple episodes
3. **Incremental updates**: Track processed episodes to avoid re-downloading
4. **Story classification**: Auto-detect story types using embeddings

## Rate Limits

### Voyage AI (Embeddings)
- **Free tier (no payment)**: 3 requests/minute
- **With payment method**: Much higher (200M free tokens still apply)
- **Handling**: Scripts use exponential backoff on 429 errors

### AssemblyAI (Transcription)
- Check account limits
- Each ~60min episode costs approximately 1 transcription credit

## Current Dataset Stats

- **Total segments**: 180+ stories
- **Latest additions**: 32 stories from 3 episodes (Jan 8-15, 2026)
- **Shows covered**: Monsters Among Us
- **Storage**: Segment markdown files in `segments/monsters-among-us/`

## New Scripts Added

### `scripts/download_rss.py`

Downloads episodes from Monsters Among Us RSS feed.

**Features**:
- Parses RSS XML for episode metadata
- Filters by season/episode/date
- Skips already-downloaded files
- Respects server with 2-second delays between downloads
- Progress indicators for large downloads

**Usage**:
```bash
python scripts/download_rss.py --limit 5
python scripts/download_rss.py --all
python scripts/download_rss.py --rss <custom-url>
```

## Troubleshooting

### AssemblyAI Errors
- Check API key in `.env`
- Verify audio file format (MP3 supported)
- Check account credit balance

### Voyage AI Rate Limits
- Increase `--delay` parameter
- Add payment method to account for higher limits
- Wait 60 seconds if hitting 429 errors

### Database Connection Issues
```bash
# Ensure PostgreSQL is running
docker-compose up -d

# Test connection
PGPASSWORD=paranormal psql -h localhost -p 5433 -U paranormal -d paranormal_tracker -c "SELECT 1;"
```
