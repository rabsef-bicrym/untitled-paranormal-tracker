# Paranormal Tracker Web Application

A web application for visualizing and exploring first-person paranormal stories with interactive maps, 3D vector space visualization, and psychological framework categorization.

## Architecture

- **Backend**: FastAPI (Python)
- **Frontend**: SvelteKit + TypeScript
- **Database**: PostgreSQL with pgvector
- **Visualization**: deck.gl (maps) + Three.js (3D vector space)

## Features

### Views

1. **US Map View** - Stories plotted on an interactive map, geo-tagged by location
2. **Vector Space View** - 3D visualization of story embeddings using UMAP coordinates
3. **List View** - Traditional list with search results

### Filtering

Stories can be filtered by:

- **Framework** - Psychological categorization frameworks:
  - **CAPS (Cardiff Anomalous Perceptions Scale)** - Categories include temporal lobe, clinical perceptual, chemosensory, sleep-related, and external agent experiences
  - **Sleep Paralysis Framework** - Categories include intruder, incubus, and vestibular-motor experiences
  - **Hypnagogic/Hypnopompic Framework** - Categories include visual, auditory, tactile, and proprioceptive experiences

- **Story Type** - ghost, shadow_person, cryptid, ufo, alien_encounter, haunting, poltergeist, precognition, nde, obe, time_slip, doppelganger, sleep_paralysis, possession, other

### Search

- **Hybrid search** - Combines text and vector similarity
- **Text search** - PostgreSQL full-text search
- **Vector search** - Voyage AI embeddings with cosine similarity

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker (for PostgreSQL)

### 1. Start Database

```bash
cd /path/to/untitled-paranormal-tracker
docker-compose up -d
```

### 2. Start Backend

```bash
cd web/backend

# Create virtual environment (optional, or use main venv)
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL="postgresql://paranormal:paranormal@localhost:5433/paranormal_tracker"
export VOYAGE_API_KEY="your-key-here"  # Optional, for vector search

# Run server
uvicorn main:app --reload --port 8000
```

### 3. Start Frontend

```bash
cd web/frontend

# Install dependencies
npm install

# Run dev server
npm run dev
```

Open http://localhost:5173 in your browser.

## API Endpoints

### Stories

- `GET /api/stories` - List stories with pagination and filtering
- `GET /api/stories/{id}` - Get single story details
- `POST /api/search` - Search stories (hybrid/text/vector)

### Visualization

- `GET /api/map/stories` - Stories with geo-coordinates for map
- `GET /api/vector-space/points` - Stories with UMAP coordinates for 3D viz

### Metadata

- `GET /api/stats` - Database statistics
- `GET /api/frameworks` - Framework definitions
- `GET /api/story-types` - Story type counts

## Environment Variables

### Backend

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | No | PostgreSQL connection URL (has default) |
| `VOYAGE_API_KEY` | No | Voyage AI API key for vector search |

### Frontend

| Variable | Required | Description |
|----------|----------|-------------|
| `VITE_API_URL` | No | Backend API URL (default: http://localhost:8000) |

## Framework Categories Mapping

### CAPS (Cardiff Anomalous Perceptions Scale)

| Category | Story Types |
|----------|-------------|
| temporal_lobe | precognition, time_slip, deja_vu |
| clinical_perceptual | shadow_person, ghost, doppelganger |
| chemosensory | phantom_smell, other |
| sleep_related | sleep_paralysis, obe, nde |
| external_agent | alien_encounter, possession, haunting |

### Sleep Paralysis Framework

| Category | Story Types |
|----------|-------------|
| intruder | shadow_person, ghost, alien_encounter |
| incubus | sleep_paralysis, possession |
| vestibular_motor | obe, nde, time_slip |

### Hypnagogic/Hypnopompic Framework

| Category | Story Types |
|----------|-------------|
| visual | ghost, shadow_person, doppelganger, ufo |
| auditory | ghost, haunting |
| tactile | sleep_paralysis, possession |
| proprioceptive | obe, time_slip |
