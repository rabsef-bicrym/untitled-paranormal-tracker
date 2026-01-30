-- Paranormal Tracker Database Schema
-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- For fuzzy text search

-- Episodes table (podcast episodes)
CREATE TABLE episodes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    podcast_name TEXT,
    episode_number TEXT,
    air_date DATE,
    source_url TEXT,
    audio_filename TEXT,
    duration_seconds INTEGER,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Transcripts table (raw AssemblyAI output)
CREATE TABLE transcripts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    episode_id UUID REFERENCES episodes(id) ON DELETE CASCADE,
    assemblyai_id TEXT UNIQUE,
    raw_json JSONB,
    speaker_count INTEGER,
    word_count INTEGER,
    confidence FLOAT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Stories table (segmented paranormal stories - FIRST-PERSON ONLY)
CREATE TABLE stories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    episode_id UUID REFERENCES episodes(id) ON DELETE CASCADE,
    transcript_id UUID REFERENCES transcripts(id) ON DELETE CASCADE,

    -- Story content (VERBATIM - never cleaned or paraphrased)
    title TEXT NOT NULL,           -- For human display only
    summary TEXT,                  -- For human display only (NOT embedded)
    content TEXT NOT NULL,         -- VERBATIM transcript text

    -- Timestamps within episode
    start_time_seconds FLOAT,
    end_time_seconds FLOAT,

    -- Metadata from segmentation
    story_type TEXT,  -- e.g., 'ghost', 'cryptid', 'ufo', 'precognition', etc.
    location TEXT,
    time_period TEXT,
    is_first_person BOOLEAN DEFAULT TRUE,  -- Should always be true (validation)

    -- Embedding metadata
    token_count INTEGER,
    embedding_method TEXT,  -- 'full' (< 4k tokens) or 'mean_pooled' (chunked)

    -- Story-level embedding (1024-dim for Titan)
    -- Either full story embedding OR mean-pooled chunk embeddings
    embedding vector(1024),

    -- UMAP projections for visualization
    umap_x FLOAT,
    umap_y FLOAT,
    umap_computed_at TIMESTAMPTZ,

    -- Parapsychology framework analysis (LLM-generated, story-only)
    frameworks_json JSONB,
    frameworks_version TEXT,
    frameworks_model TEXT,
    frameworks_computed_at TIMESTAMPTZ,

    -- Full-text search (includes summary for text search, not semantic)
    search_vector tsvector GENERATED ALWAYS AS (
        setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(summary, '')), 'B') ||
        setweight(to_tsvector('english', coalesce(content, '')), 'C')
    ) STORED,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Story chunks (for late chunking / precise retrieval)
CREATE TABLE story_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    story_id UUID REFERENCES stories(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,         -- VERBATIM chunk text
    start_time_seconds FLOAT,
    end_time_seconds FLOAT,
    token_count INTEGER,
    embedding vector(1024),
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Rejected stories (secondhand accounts - kept for audit trail)
CREATE TABLE rejected_stories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    episode_id UUID REFERENCES episodes(id) ON DELETE CASCADE,
    transcript_id UUID REFERENCES transcripts(id) ON DELETE CASCADE,
    title TEXT,
    start_time_seconds FLOAT,
    end_time_seconds FLOAT,
    rejection_reason TEXT NOT NULL,  -- e.g., 'secondhand', 'folklore', etc.
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Speaker mappings (from LeMUR identification)
CREATE TABLE speakers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    episode_id UUID REFERENCES episodes(id) ON DELETE CASCADE,
    speaker_label TEXT NOT NULL,  -- e.g., 'A', 'B'
    speaker_name TEXT,
    role TEXT,  -- e.g., 'host', 'guest', 'caller'
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(episode_id, speaker_label)
);

-- Clusters (for visualization)
CREATE TABLE clusters (
    id SERIAL PRIMARY KEY,
    label TEXT,
    description TEXT,
    centroid vector(1024),
    story_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE story_clusters (
    story_id UUID REFERENCES stories(id) ON DELETE CASCADE,
    cluster_id INTEGER REFERENCES clusters(id) ON DELETE CASCADE,
    similarity_score FLOAT,
    PRIMARY KEY (story_id, cluster_id)
);

-- Indexes
CREATE INDEX idx_stories_episode ON stories(episode_id);
CREATE INDEX idx_stories_embedding ON stories USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_stories_search ON stories USING GIN (search_vector);
CREATE INDEX idx_stories_umap ON stories(umap_x, umap_y);
CREATE INDEX idx_stories_type ON stories(story_type);
CREATE INDEX idx_transcripts_episode ON transcripts(episode_id);

-- Trigger for updated_at
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER episodes_updated_at
    BEFORE UPDATE ON episodes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER stories_updated_at
    BEFORE UPDATE ON stories
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER clusters_updated_at
    BEFORE UPDATE ON clusters
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
