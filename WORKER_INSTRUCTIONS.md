# Worker Instructions: Extract Paranormal Stories from Transcripts

## Your Assignment

You will be assigned **ONE transcript file** to process. Your job is to extract all first-person paranormal stories from that transcript using the provided script.

**CRITICAL: ONE WORKER = ONE TRANSCRIPT = ONE EPISODE**

Do not process multiple transcripts. Focus entirely on your assigned episode.

---

## Setup (Run Once)

```bash
cd /Users/rabsef-bicrym/Development/personal/projects/untitled-paranormal-tracker
source venv/bin/activate
export $(cat .env | xargs)
```

---

## Procedural Workflow

### Step 1: Read Your Assigned Transcript

Your coordinator will assign you a transcript file. Example:
```
transcripts/mau_s2e4_22-Sep-2016.txt
```

Read the `.txt` file from start to finish. It looks like this:

```
1: [Speaker A] Hello and welcome to Monsters Among Us...
2: [Speaker B] Hi, this is Mike from Texas. When I was 8 years old...
3: [Speaker B] I woke up and there was this shadow figure...
4: [Speaker A] That's terrifying. Thanks for calling...
5: [Speaker C] Hi Derek, this is Sarah from Ohio...
```

**Speaker A** = Host (Derek Hayes) - skip this, don't extract
**Speaker B, C, D, E, etc.** = Callers - extract their stories

### Step 2: Identify First-Person Paranormal Stories

For each caller segment, ask:

**✅ EXTRACT IF:**
- Caller says "I saw...", "I experienced...", "This happened to me..."
- Caller is recounting something they personally witnessed
- Story is paranormal/supernatural in nature

**❌ SKIP IF:**
- Secondhand: "My friend saw...", "My grandmother told me...", "There's a legend..."
- Host commentary/intros (Speaker A)
- Non-paranormal stories

### Step 3: Note Story Details

For each story you'll extract, write down:

1. **Line range** - Which lines contain this caller's story
   - Example: `5-12` (lines 5 through 12)
   - Example: `23-23` (single line 23)

2. **Title** - Create a descriptive title (3-8 words)
   - Example: "Shadow Figure in Childhood Bedroom"
   - Example: "Triangle UFO Over Highway"

3. **Caller** - Caller's name if mentioned
   - Example: "Mike from Texas"
   - Example: "Anonymous"

4. **Type** - Story category (pick one, use best judgment):
   - `ghost` - Apparitions, spirits
   - `shadow_person` - Shadow figures, hat man
   - `cryptid` - Bigfoot, unknown creatures
   - `ufo` - UFO sightings, strange lights
   - `alien_encounter` - Alien beings, abduction
   - `haunting` - Location-based paranormal activity
   - `poltergeist` - Objects moving, physical disturbances
   - `precognition` - Knowing future events
   - `nde` - Near-death experience
   - `obe` - Out-of-body experience, astral projection
   - `time_slip` - Time anomalies, missing time
   - `doppelganger` - Seeing one's double
   - `sleep_paralysis` - Sleep paralysis with entity
   - `possession` - Possession experiences
   - `other` - Doesn't fit other categories

5. **Location** - Location if mentioned
   - Example: "Texas"
   - Example: "Unknown"

### Step 4: Get Episode Date

Get the modification date of the **transcript JSON file** (NOT the .txt file):

```bash
stat -f "%Sm" -t "%Y-%m-%d" transcripts/mau_s2e4_22-Sep-2016.json
```

This gives you the episode date in YYYY-MM-DD format.

### Step 5: Extract Each Story Using the Script

**CRITICAL: DO NOT MANUALLY TRANSCRIBE**
**DO NOT COPY-PASTE TEXT MANUALLY**
**USE THE SCRIPT FOR EVERY EXTRACTION**

For each story, run this command:

```bash
python scripts/extract_segment.py \
  --transcript transcripts/mau_s2e4_22-Sep-2016.json \
  --lines 5-12 \
  --title "Shadow Figure in Childhood Bedroom" \
  --show "Monsters Among Us" \
  --date 2020-09-10 \
  --caller "Mike from Texas" \
  --type shadow_person \
  --location "Texas"
```

**Replace:**
- `transcripts/mau_s2e4_22-Sep-2016.json` - your assigned transcript (**JSON file, not TXT**)
- `--lines 5-12` - line range from your notes
- `--title "..."` - title you created
- `--date 2020-09-10` - date from Step 4
- `--caller "..."` - caller name (or "Anonymous")
- `--type ...` - story type from your notes
- `--location "..."` - location (or "Unknown")

The script will:
- Extract the exact text from the JSON
- Look up precise timestamps
- Create a properly formatted `.md` file in `segments/monsters-among-us/`

### Step 6: Verify Output

After running the script, check that the file was created:

```bash
ls -lh segments/monsters-among-us/
```

You should see a new file like:
```
2020-09-10_shadow-figure-in-childhood-bedroom.md
```

### Step 7: Repeat for All Stories

Go through your entire transcript and extract every first-person paranormal story using Steps 2-6.

---

## Example Complete Workflow

**Assigned transcript:** `transcripts/mau_s2e4_22-Sep-2016.txt`

**1. Read transcript, find stories:**
- Lines 5-12: Mike from Texas - shadow figure story
- Lines 23-23: Sarah from Ohio - UFO sighting
- Lines 45-52: Anonymous - ghost encounter

**2. Get episode date:**
```bash
stat -f "%Sm" -t "%Y-%m-%d" transcripts/mau_s2e4_22-Sep-2016.json
# Output: 2016-09-22
```

**3. Extract story 1:**
```bash
python scripts/extract_segment.py \
  --transcript transcripts/mau_s2e4_22-Sep-2016.json \
  --lines 5-12 \
  --title "Shadow Figure in Childhood Bedroom" \
  --show "Monsters Among Us" \
  --date 2016-09-22 \
  --caller "Mike from Texas" \
  --type shadow_person \
  --location "Texas"
```

**4. Extract story 2:**
```bash
python scripts/extract_segment.py \
  --transcript transcripts/mau_s2e4_22-Sep-2016.json \
  --lines 23-23 \
  --title "Triangle UFO Over Highway" \
  --show "Monsters Among Us" \
  --date 2016-09-22 \
  --caller "Sarah from Ohio" \
  --type ufo \
  --location "Ohio"
```

**5. Extract story 3:**
```bash
python scripts/extract_segment.py \
  --transcript transcripts/mau_s2e4_22-Sep-2016.json \
  --lines 45-52 \
  --title "Deceased Mother Appears in Kitchen" \
  --show "Monsters Among Us" \
  --date 2016-09-22 \
  --caller "Anonymous" \
  --type ghost \
  --location "Unknown"
```

**6. Report completion:**
When done, report:
- Transcript file processed
- Number of stories extracted
- Any issues encountered

---

## Common Mistakes to Avoid

❌ **DO NOT manually transcribe or copy-paste text**
✅ **ALWAYS use the extract_segment.py script**

❌ **DO NOT extract host commentary (Speaker A)**
✅ **ONLY extract caller stories (Speaker B, C, D, etc.)**

❌ **DO NOT extract secondhand stories ("my friend saw...")**
✅ **ONLY extract first-person accounts ("I saw...")**

❌ **DO NOT process multiple transcripts**
✅ **PROCESS ONLY YOUR ASSIGNED TRANSCRIPT**

❌ **DO NOT use the .txt file in the script**
✅ **USE the .json file in the --transcript argument**

---

## Questions?

If you encounter issues:
- Story spans unclear line ranges → Use your best judgment
- Caller name not mentioned → Use "Anonymous"
- Location not mentioned → Use "Unknown"
- Unsure about story type → Pick closest match or use "other"
- First-person vs secondhand unclear → When in doubt, skip it

Report completion when all stories from your assigned transcript are extracted.
