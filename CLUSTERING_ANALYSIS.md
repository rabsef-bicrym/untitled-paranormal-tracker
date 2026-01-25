# Clustering Analysis Results

**Date:** 2026-01-24
**Stories Analyzed:** 231
**Algorithm:** UMAP + HDBSCAN

## Summary

The clustering analysis discovered **21 natural clusters** from the 231 paranormal stories in the database, compared to the 14 original `story_type` categories. This suggests that unsupervised clustering reveals different phenomenological groupings than traditional folk categories.

### Key Metrics

- **Clusters Found:** 21
- **Noise/Outlier Stories:** 26 (11.3%)
- **Clustered Stories:** 205 (88.7%)
- **Adjusted Rand Index (ARI):** 0.170
  - Low ARI indicates discovered clusters differ significantly from folk categories
  - Supports the hypothesis that paranormal experiences represent distinct "brain failure modes"
- **Normalized Mutual Information (NMI):** 0.466
  - Moderate correlation between discovered clusters and story types

### Cluster Characteristics

The 21 discovered clusters show distinct phenomenological patterns:

#### High-Purity Clusters (>90% single story_type)
- **Cluster 18:** 100% shadow_person (7 stories) - Pure shadow figure experiences
- **Cluster 6:** 91.7% ghost (12 stories) - Auditory phenomena (music, voices)

#### Phenomenon-Specific Clusters (70-90% purity)
- **Cluster 0:** 80.0% UFO (5 stories) - Bright light phenomena
- **Cluster 3:** 71.4% cryptid (14 stories) - Creature encounters
- **Cluster 4:** 75.8% UFO (33 stories) - UFO sightings (largest cluster)
- **Cluster 7:** 71.4% poltergeist (7 stories) - Physical object movement
- **Cluster 17:** 71.4% shadow_person (7 stories) - Shadow entities
- **Cluster 19:** 66.7% shadow_person (6 stories) - Bedroom shadow figures

#### Mixed/Cross-Category Clusters
Many clusters combine multiple story types, suggesting shared phenomenology:
- **Cluster 1:** Mixed (35.7% ghost) - 14 stories across 5 types
- **Cluster 10:** Mixed (36.4% haunting) - Auditory experiences across types
- **Cluster 20:** Mixed (36.4% other) - Diverse unusual experiences

### Phenomenological Analysis

The feature extraction revealed dominant sensory/contextual patterns:

**Auditory-Dominant Clusters:**
- Clusters 5, 6, 8, 10 - Voice/music/sound phenomena

**Visual/Light-Dominant Clusters:**
- Clusters 0, 4 - Bright light UFO experiences
- Cluster 4 specifically emphasizes road/driving context

**Tactile/Somatic Clusters:**
- Clusters 2, 13 - Physical sensations, touch, pressure

**Sleep/Paralysis Context:**
- Multiple clusters (18, 19, 20) emphasize bedroom/sleep context
- Suggests hypnagogic/hypnopompic state involvement

**Physical Effects:**
- Cluster 7 - Poltergeist/object movement
- Cluster 8 - Door-related phenomena

### Database Updates

All 231 stories updated with:
- `umap_x`, `umap_y`: 2D visualization coordinates
- `cluster_id`: Assigned cluster (NULL for noise/outliers)

### Visualization

The TUI visualize view now supports:
- Toggle between `story_type` and `cluster` coloring (press 'c')
- Color-coded cluster legend
- Both type and cluster displayed for selected stories

### Interpretation

The low ARI (0.170) combined with 21 discovered clusters vs 14 original types suggests:
1. **Natural phenomenological groupings differ from folk categories**
2. **Cross-category patterns exist** - e.g., shadow figures split into multiple clusters based on context
3. **Supports "brain failure mode" hypothesis** - Similar cognitive/perceptual states produce similar narratives regardless of labeled category

### Next Steps

Potential follow-up analyses available with optional flags:
- `--hierarchy`: Show hierarchical relationships between clusters
- `--stability`: Test cluster robustness across parameters
- `--soft`: Find ambiguous/transitional stories
- `--bertopic`: Extract interpretable topic labels
- `--all-analysis`: Run all optional analyses

## Files Modified

- `scripts/cluster_stories.py`: Clustering analysis script (new)
- `requirements.txt`: Added UMAP, HDBSCAN, scipy dependencies
- Database schema: Added `umap_x`, `umap_y`, `cluster_id` columns
- `tui/`: Updated to support cluster visualization
- `clustering_output.txt`: Full analysis output
