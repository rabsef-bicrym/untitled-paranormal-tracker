# Spike: UMAP Strategy for Paranormal Tracker

**Issue:** upt-3f8
**Date:** January 2026
**Status:** Complete

## Executive Summary

For a paranormal story tracking web application, **server-side batch UMAP computation with cached 2D projections is the recommended approach**. Browser-based UMAP (umap-js) is viable for small datasets (<1k points) but becomes problematic at scale. The hybrid approach outlined below provides the best balance of user experience, scalability, and maintainability.

---

## Research Findings

### 1. In-Browser vs Server-Side Computation

#### umap-js (Browser)

**Pros:**
- Zero server infrastructure for computation
- Immediate feedback for small datasets
- Can run in Web Worker to avoid blocking main thread
- Good for interactive parameter exploration on small samples

**Cons:**
- No spectral embedding initialization (uses random instead) - comparable results only on smaller datasets
- No sparse data support or advanced distance functions
- Browser memory constraints (~2-4GB depending on device)
- Performance degrades significantly beyond ~5k points
- Cannot leverage GPU acceleration
- Blocking UI without Web Worker wrapper

**Observed Performance (from community benchmarks):**
- 1,000 points: "Results quickly enough"
- 10,000 points: "Be patient!" - multiple seconds to minutes
- Beyond 10k: Not recommended

#### Python umap-learn (Server)

**Pros:**
- Numba JIT compilation for high performance
- Optional TBB optimization for x86 processors
- Spectral embedding initialization for better quality
- `low_memory=True` option for constrained environments
- GPU acceleration via RAPIDS cuML (311x speedup on large datasets)
- Mature, well-tested implementation
- Handles 100k+ points efficiently on CPU, millions with GPU

**Cons:**
- Requires server infrastructure
- Network latency for results
- Compute costs for serverless/edge deployment

**Performance Benchmarks (Python umap-learn):**
| Dataset Size | CPU Time | GPU Time (cuML) |
|--------------|----------|-----------------|
| 10k points   | ~2-5s    | <1s             |
| 100k points  | ~30-60s  | ~2-5s           |
| 1M points    | ~10+ min | ~30s            |
| 10M points   | Hours    | <1 min          |

### 2. Incremental Updates vs Full Recomputation

#### Transform Method (for new points, same distribution)
- umap-learn provides `transform()` to project new data into existing embedding
- "Works efficiently - taking less than half a second" for typical use
- **Caveat:** Only works if new data is from same distribution as training data

#### Update Method (for retraining)
- umap-learn 0.5.x added `update()` method for incremental retraining
- Some reported bugs in practice (GitHub issue #790)
- AlignedUMAP supports batched updates for large datasets

#### Parametric UMAP (neural network approach)
- Learns embedding via neural network instead of direct optimization
- Can incorporate new data by continuing training
- Requires "landmarks" to prevent embedding drift
- More complex to deploy but better for truly streaming scenarios

#### Batch-Incremental UMAP
- For streaming/evolving data: process batches independently
- Embedding "stitching" required to combine results
- Research approach, not production-ready

#### Recommendation by Scenario
| Scenario | Approach |
|----------|----------|
| New stories (same distribution) | `transform()` - fast, reliable |
| Significant new data (100+ stories) | Full recompute - better quality |
| Data distribution shift | Full recompute - essential |
| Near real-time updates | Parametric UMAP with landmarks |

### 3. Library Comparison

| Feature | umap-js | umap-learn |
|---------|---------|------------|
| Language | TypeScript/JS | Python |
| Initialization | Random | Spectral |
| Sparse data | No | Yes |
| Custom distances | Limited | Full |
| GPU support | No | Via cuML |
| Web Worker | Manual wrapper | N/A |
| Transform | Yes | Yes |
| Update/Incremental | No | Yes (with caveats) |
| Memory efficiency | Browser limited | `low_memory` option |
| Production maturity | Good for small data | Production-grade |

### 4. Performance at Scale

#### 1,000 points
- **umap-js:** 1-3 seconds, acceptable UX
- **umap-learn:** <1 second
- **Recommendation:** Either viable; browser-side acceptable

#### 10,000 points
- **umap-js:** 10-60+ seconds, poor UX without progress indicator
- **umap-learn:** 2-5 seconds
- **Recommendation:** Server-side preferred

#### 100,000 points
- **umap-js:** Not recommended (memory issues, multi-minute compute)
- **umap-learn:** 30-60 seconds on CPU, ~2-5s with GPU
- **Recommendation:** Server-side required; consider pre-computation

### 5. Storage Strategy for 2D Projections

#### Recommended: PostgreSQL with simple columns

For UMAP 2D projections, pgvector is overkill. Simple float columns suffice:

```sql
-- Stories table with projections
ALTER TABLE stories ADD COLUMN umap_x FLOAT;
ALTER TABLE stories ADD COLUMN umap_y FLOAT;
ALTER TABLE stories ADD COLUMN umap_computed_at TIMESTAMPTZ;

-- Index for efficient range queries (optional, for viewport filtering)
CREATE INDEX idx_stories_umap ON stories (umap_x, umap_y);
```

**Why not pgvector for projections?**
- pgvector is designed for high-dimensional vectors (100s-1000s of dims)
- 2D projections don't benefit from vector similarity operations
- Simple float columns are more efficient and queryable

**When to use pgvector:**
- Store the original high-dimensional embeddings (e.g., from text embedding models)
- Enable semantic search on story content
- These are separate from UMAP projections

#### Storage Architecture
```
┌─────────────────────────────────────────────┐
│ stories table                               │
├─────────────────────────────────────────────┤
│ id, title, content, ...                     │
│ embedding VECTOR(384)  ← for semantic search│
│ umap_x FLOAT           ← for visualization  │
│ umap_y FLOAT           ← for visualization  │
│ umap_computed_at TIMESTAMPTZ               │
└─────────────────────────────────────────────┘
```

---

## Recommended Architecture

### Overview

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Browser       │────▶│  Supabase        │────▶│  Python Worker  │
│   (Viz only)    │     │  (DB + API)      │     │  (UMAP compute) │
└─────────────────┘     └──────────────────┘     └─────────────────┘
        │                        │                        │
        │  Fetch cached         │  Trigger on            │  Write back
        │  projections          │  new stories           │  projections
        ▼                        ▼                        ▼
   ┌─────────────────────────────────────────────────────────────┐
   │                    PostgreSQL                                │
   │  stories: id, content, embedding, umap_x, umap_y, ...       │
   └─────────────────────────────────────────────────────────────┘
```

### Component Details

#### 1. Frontend (Browser)
- Fetch pre-computed UMAP coordinates from database
- Render visualization using WebGL (deck.gl, regl, etc.)
- NO UMAP computation in browser
- Optional: umap-js for small sample exploration (<500 points)

#### 2. Supabase
- Store stories with embeddings and UMAP coordinates
- Real-time subscriptions for new story positions
- Edge Function to trigger recomputation (calls Python worker)

#### 3. Python Worker (External)
Since Supabase Edge Functions don't support Python:

**Option A: Scheduled Cloud Function (Recommended)**
- Use AWS Lambda, Google Cloud Functions, or Railway
- Trigger on schedule (every 15 min) or webhook
- Batch process new stories with `transform()`
- Full recompute weekly or when >10% new data

**Option B: Fly.io/Railway Persistent Worker**
- Long-running Python process
- Listen for database changes via Supabase Realtime
- More complex but lower latency

### Computation Strategy

```python
# Pseudo-code for worker
def process_umap():
    # Check for new stories without projections
    new_stories = db.query("SELECT * FROM stories WHERE umap_x IS NULL")

    if len(new_stories) == 0:
        return

    # Get all stories for context
    all_stories = db.query("SELECT * FROM stories WHERE embedding IS NOT NULL")

    if should_full_recompute(all_stories, new_stories):
        # Full recompute: >10% new or weekly
        embeddings = np.array([s.embedding for s in all_stories])
        reducer = umap.UMAP(n_neighbors=15, min_dist=0.1)
        projections = reducer.fit_transform(embeddings)
        update_all_projections(all_stories, projections)
    else:
        # Transform only: project new into existing space
        existing = all_stories.filter(lambda s: s.umap_x is not None)
        embeddings = np.array([s.embedding for s in existing])
        reducer = umap.UMAP(n_neighbors=15, min_dist=0.1)
        reducer.fit(embeddings)

        new_embeddings = np.array([s.embedding for s in new_stories])
        new_projections = reducer.transform(new_embeddings)
        update_new_projections(new_stories, new_projections)
```

### When to Recompute

| Trigger | Action |
|---------|--------|
| New story submitted | Queue for transform (batch every 15 min) |
| 10% new stories since last full compute | Full recompute |
| Weekly schedule | Full recompute |
| Manual admin trigger | Full recompute |
| Embedding model changed | Full recompute (all stories) |

---

## Implementation Phases

### Phase 1: MVP (Manual/Scheduled)
- Add `umap_x`, `umap_y` columns to stories table
- Create Python script for local UMAP computation
- Run manually or via cron when needed
- Frontend fetches coordinates directly from DB

### Phase 2: Automated Pipeline
- Deploy Python worker to cloud function
- Supabase Edge Function to trigger on new stories
- Batch processing every 15 minutes

### Phase 3: Optimization (if needed)
- GPU acceleration for 100k+ scale
- Parametric UMAP for near-real-time updates
- Caching layer for frequently-accessed viewport regions

---

## Decision Summary

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Computation location | Server-side (Python) | Scalability, quality, no browser constraints |
| Library | umap-learn | Production maturity, transform support, GPU option |
| Update strategy | Transform for new, periodic full recompute | Best balance of quality and performance |
| Storage | PostgreSQL float columns | Simple, efficient for 2D data |
| Hosting | Cloud function (Lambda/GCF/Railway) | Cost-effective, scales to zero |

---

## References

- [umap-learn Documentation](https://umap-learn.readthedocs.io/)
- [umap-js GitHub](https://github.com/PAIR-code/umap-js)
- [UMAP Benchmarking](https://umap-learn.readthedocs.io/en/latest/benchmarking.html)
- [Transform New Data with UMAP](https://umap-learn.readthedocs.io/en/latest/transform.html)
- [Batch-Incremental UMAP Research](https://link.springer.com/chapter/10.1007/978-3-030-44584-3_4)
- [pgvector for PostgreSQL](https://supabase.com/docs/guides/database/extensions/pgvector)
- [RAPIDS cuML GPU Acceleration](https://developer.nvidia.com/blog/even-faster-and-more-scalable-umap-on-the-gpu-with-rapids-cuml/)
- [Supabase Edge Functions](https://supabase.com/docs/guides/functions)
