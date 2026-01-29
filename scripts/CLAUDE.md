# Scripts Usage Guide

This folder contains scripts for processing paranormal podcast episodes into structured, searchable data.

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set environment variables (see .env.example)
export ASSEMBLYAI_API_KEY=your_key
export VOYAGE_API_KEY=your_key
export ANTHROPIC_API_KEY=your_key

# 3. Start database
docker-compose up -d

# 4. Process an episode (see workflow below)
```

---

## Complete Workflow

```
MP3 → transcribe.py → .json + .txt
                           ↓
              [Claude reads .txt, identifies stories]
                           ↓
         extract_segment.py (for each story) → .md files
                           ↓
                    load_segments.py → Database
                           ↓
                      search.py → Query results
```

---

## Step 1: Transcribe

Convert MP3 to JSON (timestamps) + TXT (readable).

```bash
python scripts/transcribe.py episodes/show_2024-01-15.mp3
```

**Output:**
- `transcripts/show_2024-01-15.json` - Word-level timestamps for extraction
- `transcripts/show_2024-01-15.txt` - Line-numbered transcript for reading

**TXT format:**
```
1: [Speaker A] Welcome to the show...
2: [Speaker B] Thanks for having me. This happened when I was eight...
3: [Speaker B] I woke up and there was this figure...
```

---

## Step 2: Identify Stories

Read the `.txt` file. For each first-person paranormal story, note:
- Line range (e.g., "45-120")
- Title (you create this)
- Caller name (if mentioned)
- Story type
- Location (if mentioned)

**FIRST-PERSON ONLY:**
- ✅ "I saw..." "When I was 8..." "This happened to me..."
- ❌ "My grandmother told me..." "My friend saw..." "There's a legend..."

---

## Step 3: Extract Segments

For each story, create a `.md` file:

```bash
python scripts/extract_segment.py \
  --transcript transcripts/show_2024-01-15.json \
  --lines 45-120 \
  --title "Shadow Figure in Childhood Bedroom" \
  --show "Coast to Coast AM" \
  --date 2024-01-15 \
  --caller "Mike from Ohio" \
  --type shadow_person \
  --location "Ohio"
```

**Creates:** `segments/coast-to-coast-am/2024-01-15_shadow-figure-in-childhood-bedroom.md`

**Arguments:**
| Arg | Required | Description |
|-----|----------|-------------|
| `-t, --transcript` | Yes | Path to .json file |
| `-l, --lines` | Yes | Line range (e.g., "45-120") |
| `--title` | Yes | Title for this story |
| `--show` | Yes | Podcast/show name |
| `--date` | Yes | Episode date (YYYY-MM-DD) |
| `--caller` | No | Caller's name |
| `--type` | No | Story type (see list below) |
| `--location` | No | Location mentioned |
| `--secondhand` | No | Flag if NOT first-person (usually skip these) |
| `--dry-run` | No | Preview without writing |

---

## Step 4: Cleanup Temp Files

After extracting all segments:

```bash
rm transcripts/show_2024-01-15.{json,txt}
rm episodes/show_2024-01-15.mp3
```

The `.md` segment files are now the source of truth.

---

## Step 5: Load into Database

Load segment files with embeddings:

```bash
# Load all segments
python scripts/load_segments.py

# Preview what would be loaded
python scripts/load_segments.py --dry-run

# Load specific file
python scripts/load_segments.py --file segments/show/story.md
```

Stories < 4k tokens get embedded whole. Longer stories are chunked, embedded per-chunk, then mean-pooled for the story-level embedding.

---

## Step 6: Search

Query the database:

```bash
# Hybrid search (text + vector)
python scripts/search.py "shadow figure bedroom"

# Text-only (no API key needed)
python scripts/search.py "ghost" --text-only

# Vector-only (semantic similarity)
python scripts/search.py "strange presence at night" --vector-only

# Adjust blend (0=text, 1=vector)
python scripts/search.py "UFO" --alpha 0.5
```

---

## Story Types

Use these standardized values:
- `ghost` - Apparitions, spirits
- `shadow_person` - Shadow figures, hat man
- `cryptid` - Bigfoot, creatures
- `ufo` - UFO sightings
- `alien_encounter` - Alien beings, abduction
- `haunting` - Location-based activity
- `poltergeist` - Object movement
- `precognition` - Knowing future events
- `nde` - Near-death experience
- `obe` - Out-of-body experience
- `time_slip` - Time anomalies
- `doppelganger` - Seeing one's double
- `sleep_paralysis` - Sleep paralysis entities
- `possession` - Possession experiences
- `other` - Doesn't fit categories

---

## Segment File Format

```markdown
---
title: "Shadow Figure in Childhood Bedroom"
show: "Coast to Coast AM"
date: 2024-01-15
timestamp_start: 1245.5
timestamp_end: 1892.3
timestamp_display: "20:45 - 31:32"
caller: "Mike from Ohio"
type: "shadow_person"
location: "Ohio"
source_lines: "45-120"
first_person: true
---

[Speaker B] So this happened when I was about eight years old...

[Speaker B] I woke up in the middle of the night, and there was this figure...

[Speaker A] What did it look like?

[Speaker B] It was like a shadow, but darker than the darkness...
```

---

## Environment Variables

| Variable | Required For | Description |
|----------|--------------|-------------|
| `ASSEMBLYAI_API_KEY` | transcribe.py | AssemblyAI API key |
| `VOYAGE_API_KEY` | load_segments.py, search.py | Voyage AI API key |
| `ANTHROPIC_API_KEY` | load_segments.py | Anthropic API key for framework analysis |
| `ANTHROPIC_MODEL` | load_segments.py | Optional Anthropic model override |

### Framework Backfill

```bash
# Backfill only missing/outdated framework analysis
python scripts/backfill_frameworks.py

# Recompute frameworks for all stories
python scripts/backfill_frameworks.py --all

# Process specific story ID(s)
python scripts/backfill_frameworks.py --id <uuid> --id <uuid>
```
| `DATABASE_URL` | load_segments.py, search.py | PostgreSQL URL (has default) |

---

## Example Full Run

```bash
# 1. Transcribe
python scripts/transcribe.py episodes/c2c_2024-01-15.mp3

# 2. Read transcript, identify stories
cat transcripts/c2c_2024-01-15.txt
# Found: lines 23-87 = shadow figure, lines 150-210 = UFO

# 3. Extract each segment
python scripts/extract_segment.py \
  -t transcripts/c2c_2024-01-15.json \
  -l 23-87 \
  --title "Shadow Figure in Childhood Bedroom" \
  --show "Coast to Coast AM" \
  --date 2024-01-15 \
  --caller "Mike" \
  --type shadow_person

python scripts/extract_segment.py \
  -t transcripts/c2c_2024-01-15.json \
  -l 150-210 \
  --title "Triangle UFO Over Highway" \
  --show "Coast to Coast AM" \
  --date 2024-01-15 \
  --caller "Linda" \
  --type ufo \
  --location "Arizona"

# 4. Cleanup
rm transcripts/c2c_2024-01-15.{json,txt}
rm episodes/c2c_2024-01-15.mp3

# 5. Load into database
python scripts/load_segments.py

# 6. Search
python scripts/search.py "shadow figure"
```

---

## Database

**Start:** `docker-compose up -d`
**Stop:** `docker-compose down`
**Reset:** `docker-compose down -v && docker-compose up -d`

**Connection:** `postgresql://paranormal:paranormal@localhost:5433/paranormal_tracker`

**Direct access:**
```bash
PGPASSWORD=paranormal psql -h localhost -p 5433 -U paranormal -d paranormal_tracker
```
