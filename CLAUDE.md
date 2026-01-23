# Paranormal Tracker - Usage Guide

A pipeline for extracting, embedding, and searching first-person paranormal stories from podcast transcripts.

## Quick Start

```bash
# 1. Activate venv
source venv/bin/activate

# 2. Load env vars
export $(cat .env | xargs)

# 3. Start database
docker-compose up -d

# 4. Process an episode (see workflow below)
```

## Environment Variables

```bash
ASSEMBLYAI_API_KEY=xxx  # For transcription
VOYAGE_API_KEY=xxx      # For embeddings
```

---

## Exact Workflow (Command by Command)

This is the exact process for processing one episode.

### Step 1: Setup (once per session)

```bash
cd /Users/rabsef-bicrym/Development/personal/projects/untitled-paranormal-tracker
source venv/bin/activate
export $(cat .env | xargs)
docker-compose up -d
```

### Step 2: Transcribe the MP3

```bash
python scripts/transcribe.py episodes/1e297334-4568-5430-802d-b4060c48b6b7.mp3
```

This creates two files:
- `transcripts/1e297334-4568-5430-802d-b4060c48b6b7.json` - full JSON with timestamps
- `transcripts/1e297334-4568-5430-802d-b4060c48b6b7.txt` - line-numbered readable transcript

### Step 3: Read the Transcript and Identify Stories

Read the `.txt` file. It looks like this:

```
1: [Speaker A] Welcome to the show...
2: [Speaker B] Thanks for having me...
...
8: [Speaker A] Hi, this is Alicia and I'm from the Dallas area. This one is like short and sweet. I was living in a house close to Houston area...
...
24: [Speaker C] Hi, this is Edward calling from Texas. I've been listening to a lot of people talk about the Shadow man...
```

For each **first-person** paranormal story, note:
- **Line number(s)** - which line(s) contain the story (e.g., `8-8` or `24-24` for single-line, `45-52` for multi-line)
- **Title** - descriptive title you create
- **Show name** - podcast name (e.g., "Monsters Among Us")
- **Date** - episode date (YYYY-MM-DD format)
- **Caller** - caller's name if mentioned (e.g., "Alicia from Texas")
- **Type** - story type (see list below)
- **Location** - location if mentioned

**FIRST-PERSON ONLY - REJECT:**
- "My grandmother told me..."
- "My friend saw..."
- "There's a legend about..."

**FIRST-PERSON ONLY - ACCEPT:**
- "I saw..."
- "This happened to me when I was 8..."
- "I woke up and there was this figure..."

### Step 4: Extract Each Story

Run one command per story:

```bash
python scripts/extract_segment.py \
  -t transcripts/1e297334-4568-5430-802d-b4060c48b6b7.json \
  -l 8-8 \
  --title "Pickle Jar Flies Off Fridge" \
  --show "Monsters Among Us" \
  --date 2026-01-20 \
  --caller "Alicia from Texas" \
  --type poltergeist \
  --location "Houston, Texas"
```

```bash
python scripts/extract_segment.py \
  -t transcripts/1e297334-4568-5430-802d-b4060c48b6b7.json \
  -l 24-24 \
  --title "Shadow Man Visits Bedroom" \
  --show "Monsters Among Us" \
  --date 2026-01-20 \
  --caller "Edward from Texas" \
  --type shadow_person \
  --location "Texas"
```

```bash
python scripts/extract_segment.py \
  -t transcripts/1e297334-4568-5430-802d-b4060c48b6b7.json \
  -l 26-26 \
  --title "Bright Light Through Windows at 3AM" \
  --show "Monsters Among Us" \
  --date 2026-01-20 \
  --type ufo \
  --location "Unknown"
```

```bash
python scripts/extract_segment.py \
  -t transcripts/1e297334-4568-5430-802d-b4060c48b6b7.json \
  -l 28-28 \
  --title "Phantom Violin at Music Studio" \
  --show "Monsters Among Us" \
  --date 2026-01-20 \
  --caller "Bob from Detroit" \
  --type ghost \
  --location "Detroit, Michigan"
```

```bash
python scripts/extract_segment.py \
  -t transcripts/1e297334-4568-5430-802d-b4060c48b6b7.json \
  -l 32-32 \
  --title "Brothers Astral Form Floats Through House" \
  --show "Monsters Among Us" \
  --date 2026-01-20 \
  --caller "Nate from Idaho" \
  --type obe \
  --location "Southern Utah"
```

```bash
python scripts/extract_segment.py \
  -t transcripts/1e297334-4568-5430-802d-b4060c48b6b7.json \
  -l 34-34 \
  --title "Whistle Mimic at Haunted Restaurant" \
  --show "Monsters Among Us" \
  --date 2026-01-20 \
  --caller "Stacy from Vermont" \
  --type ghost \
  --location "Westover, Vermont"
```

```bash
python scripts/extract_segment.py \
  -t transcripts/1e297334-4568-5430-802d-b4060c48b6b7.json \
  -l 36-36 \
  --title "Small Ghostly Legs From Mailbox" \
  --show "Monsters Among Us" \
  --date 2026-01-20 \
  --caller "Peter from Tennessee" \
  --type ghost \
  --location "Tennessee"
```

```bash
python scripts/extract_segment.py \
  -t transcripts/1e297334-4568-5430-802d-b4060c48b6b7.json \
  -l 51-51 \
  --title "Green Light Missing Time and Small Beings" \
  --show "Monsters Among Us" \
  --date 2026-01-20 \
  --caller "Jay from Canada" \
  --type alien_encounter \
  --location "Canada"
```

```bash
python scripts/extract_segment.py \
  -t transcripts/1e297334-4568-5430-802d-b4060c48b6b7.json \
  -l 73-73 \
  --title "Shadow Person Appears to Crying Child" \
  --show "Monsters Among Us" \
  --date 2026-01-20 \
  --caller "Nadia from Virginia" \
  --type shadow_person \
  --location "Northern Virginia"
```

Each command creates a `.md` file in `segments/monsters-among-us/`.

### Step 5: Load All Segments to Database

```bash
python scripts/load_segments.py --delay 1
```

This:
- Reads all `.md` files from `segments/`
- Generates Voyage AI embeddings for each story
- Inserts into PostgreSQL with pgvector

### Step 6: Search

```bash
# Hybrid search (text + vector blend)
python scripts/search.py "shadow figure in bedroom"

# Vector-only (pure semantic similarity)
python scripts/search.py "objects moving on their own" --vector-only

# Text-only (keyword match)
python scripts/search.py "Texas" --text-only
```

### Step 7: Cleanup (Optional)

After all segments extracted, remove temp files:

```bash
rm transcripts/1e297334-4568-5430-802d-b4060c48b6b7.json
rm transcripts/1e297334-4568-5430-802d-b4060c48b6b7.txt
rm episodes/1e297334-4568-5430-802d-b4060c48b6b7.mp3
```

The `.md` segment files in `segments/` are now the source of truth.

---

## Story Types

Use these exact values for `--type`:

| Type | Description |
|------|-------------|
| `ghost` | Apparitions, spirits, deceased persons |
| `shadow_person` | Shadow figures, hat man, dark humanoid shapes |
| `cryptid` | Bigfoot, unknown creatures |
| `ufo` | Unidentified flying objects, strange lights |
| `alien_encounter` | Alien beings, abduction experiences |
| `haunting` | Location-based paranormal activity |
| `poltergeist` | Objects moving, physical disturbances |
| `precognition` | Knowing future events before they happen |
| `nde` | Near-death experience |
| `obe` | Out-of-body experience, astral projection |
| `time_slip` | Time anomalies, missing time |
| `doppelganger` | Seeing one's double or living person's apparition |
| `sleep_paralysis` | Sleep paralysis with entity encounter |
| `possession` | Possession experiences |
| `other` | Doesn't fit other categories |

---

## Database

```bash
# Start
docker-compose up -d

# Stop
docker-compose down

# Reset (wipe all data)
docker-compose down -v && docker-compose up -d

# Direct SQL access
PGPASSWORD=paranormal psql -h localhost -p 5433 -U paranormal -d paranormal_tracker

# Check story count
PGPASSWORD=paranormal psql -h localhost -p 5433 -U paranormal -d paranormal_tracker -c "SELECT COUNT(*) FROM stories;"
```

---

## Rate Limiting

Voyage AI free tier (without payment method): **3 requests per minute**
Voyage AI with payment method: **much higher limits** (200M free tokens still apply)

The scripts handle rate limits with:
- Exponential backoff on 429 errors (auto-retry with increasing delays)
- `--delay` flag for load_segments.py (default 1s between files)

If you hit limits:
```bash
python scripts/load_segments.py --delay 3.0
```

---

## File Structure After Processing

```
untitled-paranormal-tracker/
├── episodes/                    # Source MP3s (can delete after processing)
├── transcripts/                 # Temp JSON + TXT (can delete after processing)
├── segments/
│   └── monsters-among-us/       # Extracted story .md files (SOURCE OF TRUTH)
│       ├── 2026-01-20_pickle-jar-flies-off-fridge.md
│       ├── 2026-01-20_shadow-man-visits-bedroom.md
│       └── ...
├── scripts/
│   ├── transcribe.py
│   ├── extract_segment.py
│   ├── load_segments.py
│   └── search.py
├── .env                         # API keys
├── docker-compose.yml           # Database config
└── CLAUDE.md                    # This file
```
