# Embedding Strategy Guide (2026 Best Practices)

> Research compiled January 2026 for the Paranormal Tracker project.

## The Core Problem

When you have a story that's too long for an embedding model's context window, or when you want both precise retrieval AND full context, you need a chunking + aggregation strategy.

**The key insight from 2025-2026 research**: "Chunking strategy determines roughly 60% of your RAG system's accuracy. Not the embedding model. Not the reranker. Not even the language model."

---

## Strategy Options

### 1. Late Chunking (Recommended for Our Use Case)

**What it is**: Embed the entire document first with a long-context model, THEN chunk the token embeddings and mean-pool each chunk.

**How it works**:
1. Pass full text through transformer (up to model's context limit)
2. Get token-level embeddings that capture full document context
3. Apply mean pooling to segments of the token sequence
4. Each chunk embedding "knows" about the rest of the document

**Why it's better**: Traditional chunking embeds "the city" without knowing it refers to "Berlin" mentioned earlier. Late chunking preserves that context.

**Available in**: jina-embeddings-v3 API (no extra training needed)

**Best for**: Medium-length documents where context matters across chunks.

### 2. Parent Document Retrieval

**What it is**: Store small chunks for precise retrieval, but return the larger "parent" document.

**How it works**:
1. Split document into small chunks (e.g., 200 tokens)
2. Embed and index the small chunks
3. When a chunk matches a query, return the full parent document
4. LLM sees complete context, not just the matched snippet

**Best for**: When you need surgical retrieval precision but can't lose context.

### 3. Hierarchical Indexing / Multi-Level Retrieval

**What it is**: Create embeddings at multiple granularities and search coarse-to-fine.

**How it works**:
1. Generate summaries at multiple levels:
   - Document level: "Episode about shadow people and precognitive dreams"
   - Section level: "Caller describes childhood haunting in Ohio"
   - Chunk level: Actual transcript segments
2. Embed at each level
3. Search: Document summaries → Section summaries → Chunks
4. Use coarse matches to narrow down, fine matches for precision

**Best for**: Very large document collections with complex nested structure.

### 4. Multi-Vector Indexing

**What it is**: Store multiple embeddings per document.

**Approaches**:
- **Summary + Chunks**: One embedding for the summary, separate embeddings for chunks
- **Questions + Content**: Generate hypothetical questions the content answers, embed those
- **Propositions**: Break into atomic factual statements, embed each

**Best for**: When different query types need different representations.

### 5. Simple Mean Pooling (Baseline)

**What it is**: Average all chunk embeddings to get a document embedding.

```python
document_embedding = np.mean(chunk_embeddings, axis=0)
```

**Pros**: Simple, no extra API calls
**Cons**: Loses nuance, "averages out" distinct topics

**Best for**: Quick baseline, or when chunks are semantically similar.

---

## Recommendation for Paranormal Tracker

### Design Philosophy: Preserve Raw Signal

**Critical insight**: We're treating this as signal analysis. The raw language people use to describe experiences may contain patterns that reveal something about the underlying phenomenon (brain states, cultural transmission, or something else entirely).

**Therefore**:
- ❌ NO Claude-generated summaries in the vector space
- ❌ NO paraphrasing or cleaning of transcript text
- ❌ NO secondhand accounts ("my grandmother told me...")
- ✅ ONLY first-person experiencer accounts
- ✅ ONLY verbatim transcript text (ums, stutters, and all)

This keeps the signal chain clean: **experiencer → microphone → transcript → embedding**

### Data Inclusion Criteria

1. **First-person only**: Speaker must be describing their OWN direct experience
2. **Verbatim extraction**: Exact transcript text, no cleanup
3. **Secondhand rejected**: "My grandmother saw..." gets logged but excluded from analysis

### Embedding Strategy

```
┌─────────────────────────────────────────────┐
│ STORY LEVEL (clustering/similarity)         │
│ - Full verbatim story embedding (if short)  │
│ - OR: late-chunked mean-pool (if longer)    │
│ - Raw experiencer language preserved        │
├─────────────────────────────────────────────┤
│ CHUNK LEVEL (search/retrieval)              │
│ - Contextual chunk embeddings               │
│ - Timestamps for audio navigation           │
│ - Precise passage finding                   │
└─────────────────────────────────────────────┘
```

**Implementation**:

1. **For short stories (< 4k tokens)**:
   - Embed the entire verbatim story directly
   - This becomes the story-level embedding for clustering

2. **For longer stories (4k-32k tokens)**:
   - Use late chunking with jina-embeddings-v3 or similar long-context model
   - Store chunk embeddings for search
   - Mean-pool chunk embeddings for story-level comparison

3. **Summaries are for humans only**:
   - Claude generates title/summary for UI display
   - These are NEVER embedded or used in similarity calculations

### Database Schema

```sql
-- Story-level embedding (for "find similar stories")
-- This is either:
--   a) Full story embedding (if story < 4k tokens)
--   b) Mean-pooled chunk embeddings (if story is longer)
ALTER TABLE stories ADD COLUMN embedding vector(1024);
ALTER TABLE stories ADD COLUMN embedding_method TEXT; -- 'full' or 'mean_pooled'
ALTER TABLE stories ADD COLUMN token_count INTEGER;

-- Chunk-level embeddings (for precise retrieval)
CREATE TABLE story_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    story_id UUID REFERENCES stories(id) ON DELETE CASCADE,
    chunk_index INTEGER,
    content TEXT NOT NULL,  -- VERBATIM transcript text
    start_time_seconds FLOAT,
    end_time_seconds FLOAT,
    embedding vector(1024),
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_story_chunks_story ON story_chunks(story_id);
CREATE INDEX idx_story_chunks_embedding
ON story_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

### Search Strategy

```python
def hybrid_search(query: str, mode: str = "balanced"):
    query_embedding = embed(query)

    if mode == "exploration":
        # Find similar stories (coarse)
        return search_story_summaries(query_embedding)

    elif mode == "precise":
        # Find specific passages (fine)
        chunks = search_chunks(query_embedding)
        return expand_to_stories(chunks)

    else:  # balanced
        # Two-stage retrieval
        candidate_stories = search_story_embeddings(query_embedding, limit=50)
        chunks = search_chunks_within_stories(query_embedding, candidate_stories)
        return rerank(chunks, query)
```

---

## Model Recommendations (2026)

| Model | Dimensions | Context | Best For |
|-------|------------|---------|----------|
| voyage-4-large | 1024 | 32000 | Best quality, very long docs |
| jina-embeddings-v3 | 1024 | 8192 | Late chunking, multilingual |
| text-embedding-3-large | 3072 | 8191 | Highest quality, adjustable dims |
| Cohere embed-v4 | 1024 | 512 | Reranking integration |
| Amazon Titan Embeddings v2 | 1024 | 8192 | AWS integration, cost |

**Our choice**: Voyage AI voyage-4-large
- Best quality general-purpose embeddings
- 32k context (plenty for full stories)
- Free tier available
- 1024 dimensions is plenty for our scale

---

## Sources

- [Late Chunking: Contextual Chunk Embeddings (arXiv, July 2025)](https://arxiv.org/abs/2409.04701)
- [Jina AI: Late Chunking Explanation](https://jina.ai/news/late-chunking-in-long-context-embedding-models/)
- [Weaviate: Late Chunking - Balancing Precision and Cost](https://weaviate.io/blog/late-chunking)
- [Parent Document Retrieval (DEV Community)](https://dev.to/jamesli/optimizing-rag-indexing-strategy-multi-vector-indexing-and-parent-document-retrieval-49hf)
- [Hierarchical RAG: Multi-level Retrieval (EmergentMind)](https://www.emergentmind.com/topics/hierarchical-retrieval-augmented-generation-hierarchical-rag)
- [Chunking Strategies Guide (Medium, Nov 2025)](https://medium.com/@adnanmasood/chunking-strategies-for-retrieval-augmented-generation-rag-a-comprehensive-guide-5522c4ea2a90)
- [Best Chunking Strategies for RAG 2025 (Firecrawl)](https://www.firecrawl.dev/blog/best-chunking-strategies-rag-2025)
- [ColBERT and Late Interaction (Jina)](https://jina.ai/news/what-is-colbert-and-late-interaction-and-why-they-matter-in-search/)
