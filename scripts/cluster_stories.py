#!/usr/bin/env python3
"""
Cluster paranormal stories using UMAP + HDBSCAN to discover natural groupings.

This implements the hypothesis that paranormal experiences represent consistent
"failure modes" of perception/cognition. If true, unsupervised clustering should
reveal natural phenomenological categories that may differ from folk labels.

Pipeline:
1. Load 1024D Voyage AI embeddings from database
2. UMAP reduce to 5D (cosine metric) for clustering
3. HDBSCAN finds natural density-based clusters
4. Compare discovered clusters to story_type labels (ARI/NMI scores)
5. UMAP reduce to 2D for visualization
6. Store results back in database

Usage:
    python scripts/cluster_stories.py
    python scripts/cluster_stories.py --min-cluster-size 3
    python scripts/cluster_stories.py --n-neighbors 20
    python scripts/cluster_stories.py --dry-run  # analyze without updating DB
"""

import argparse
import os
import sys
import numpy as np
import psycopg2
from collections import Counter

try:
    import umap
except ImportError:
    print("ERROR: umap-learn not installed. Run: pip install umap-learn")
    sys.exit(1)

try:
    import hdbscan
except ImportError:
    print("ERROR: hdbscan not installed. Run: pip install hdbscan")
    sys.exit(1)

from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score
from sklearn.preprocessing import LabelEncoder

# Database connection
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://paranormal:paranormal@localhost:5433/paranormal_tracker"
)


def get_embeddings():
    """Fetch all story embeddings from the database."""
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    cur.execute("""
        SELECT id, title, story_type, content, embedding::text
        FROM stories
        WHERE embedding IS NOT NULL
        ORDER BY id
    """)

    rows = cur.fetchall()
    cur.close()
    conn.close()

    ids = []
    titles = []
    types = []
    contents = []
    embeddings = []

    for row in rows:
        ids.append(row[0])
        titles.append(row[1])
        types.append(row[2] or 'unknown')
        contents.append(row[3])
        # Parse the vector string: [0.1,0.2,...] -> numpy array
        vec_str = row[4].strip('[]')
        vec = np.array([float(x) for x in vec_str.split(',')])
        embeddings.append(vec)

    return ids, titles, types, contents, np.array(embeddings)


def run_umap_clustering(embeddings, n_neighbors=15, min_dist=0.0, n_components=5):
    """
    Reduce dimensionality with UMAP using cosine similarity.

    For clustering, we reduce to 5D (not 2D) to preserve more structure.
    Cosine similarity is better for text embeddings than Euclidean distance.
    """
    print(f"\nRunning UMAP for clustering (n_neighbors={n_neighbors}, dims={n_components})...")

    reducer = umap.UMAP(
        n_neighbors=n_neighbors,
        n_components=n_components,
        min_dist=min_dist,  # 0.0 allows tighter clusters
        metric='cosine',    # Critical for text embeddings
        random_state=42,
        verbose=True
    )

    coords = reducer.fit_transform(embeddings)
    print(f"  Reduced {embeddings.shape[1]}D → {n_components}D")
    return coords, reducer


def run_umap_viz(embeddings, n_neighbors=15, min_dist=0.1):
    """
    Reduce to 2D for visualization.

    Slightly higher min_dist (0.1) spreads points for better visual clarity.
    """
    print(f"\nRunning UMAP for visualization (2D)...")

    reducer = umap.UMAP(
        n_neighbors=n_neighbors,
        n_components=2,
        min_dist=min_dist,
        metric='cosine',
        random_state=42,
        verbose=True
    )

    coords = reducer.fit_transform(embeddings)
    return coords


def run_hdbscan(coords, min_cluster_size=5, min_samples=2):
    """
    Find natural clusters using HDBSCAN.

    HDBSCAN advantages over k-means/agglomerative:
    - Finds natural cluster count (no need to specify k)
    - Allows outliers (label=-1) rather than forcing all points into clusters
    - Handles clusters of varying density and shape
    """
    print(f"\nRunning HDBSCAN (min_cluster_size={min_cluster_size}, min_samples={min_samples})...")

    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=min_samples,
        metric='euclidean',  # UMAP output is already in a good metric space
        cluster_selection_method='eom',  # Excess of Mass (more conservative)
        prediction_data=True
    )

    labels = clusterer.fit_predict(coords)

    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    n_noise = sum(1 for l in labels if l == -1)

    print(f"  Found {n_clusters} clusters")
    print(f"  Noise points (outliers): {n_noise}")

    return labels, clusterer


def compare_to_labels(discovered_labels, original_types):
    """
    Compare discovered clusters to existing story_type labels.

    If the hypothesis is correct (paranormal experiences = brain failure modes),
    discovered clusters should differ from folk categories.

    Metrics:
    - ARI (Adjusted Rand Index): 1.0 = perfect match, 0 = random, <0 = worse than random
    - NMI (Normalized Mutual Information): 1.0 = perfect match, 0 = independent
    """
    print("\n" + "="*60)
    print("CLUSTER VS LABEL COMPARISON")
    print("="*60)

    # Filter out noise points for comparison
    mask = discovered_labels >= 0
    discovered_filtered = discovered_labels[mask]
    original_filtered = np.array(original_types)[mask]

    # Encode string labels to integers
    le = LabelEncoder()
    original_encoded = le.fit_transform(original_filtered)

    ari = adjusted_rand_score(original_encoded, discovered_filtered)
    nmi = normalized_mutual_info_score(original_encoded, discovered_filtered)

    print(f"\nAdjusted Rand Index: {ari:.3f}")
    print(f"  (1.0 = discovered clusters match story_type perfectly)")
    print(f"  (0.0 = no better than random)")
    print(f"  (<0  = worse than random)")

    print(f"\nNormalized Mutual Info: {nmi:.3f}")
    print(f"  (1.0 = perfect correlation)")
    print(f"  (0.0 = independent)")

    if ari < 0.3:
        print("\n→ Low agreement suggests discovered clusters reveal")
        print("  different structure than folk categories - supports hypothesis!")
    elif ari > 0.7:
        print("\n→ High agreement suggests folk categories align with")
        print("  natural semantic groupings.")
    else:
        print("\n→ Moderate agreement - some overlap but also new structure.")

    return ari, nmi


def analyze_clusters(titles, types, contents, discovered_labels):
    """Print detailed analysis of each discovered cluster."""
    print("\n" + "="*60)
    print("CLUSTER ANALYSIS")
    print("="*60)

    unique_clusters = sorted(set(discovered_labels))

    for cluster_id in unique_clusters:
        indices = [i for i, c in enumerate(discovered_labels) if c == cluster_id]

        if cluster_id == -1:
            print(f"\n--- Noise/Outliers ({len(indices)} stories) ---")
        else:
            print(f"\n--- Cluster {cluster_id} ({len(indices)} stories) ---")

        # Count original story types in this cluster
        cluster_types = [types[i] for i in indices]
        type_counts = Counter(cluster_types)

        print(f"Story types present: {dict(type_counts.most_common())}")

        # Calculate type purity
        if len(indices) > 1:
            most_common_type, most_common_count = type_counts.most_common(1)[0]
            purity = most_common_count / len(indices)
            print(f"Type purity: {purity:.1%} ({most_common_type})")

        # Show sample stories
        print("Sample stories:")
        for idx in indices[:3]:
            title = titles[idx][:50] + "..." if len(titles[idx]) > 50 else titles[idx]
            print(f"  [{types[idx]}] {title}")

        if len(indices) > 3:
            print(f"  ... and {len(indices) - 3} more")


def extract_cluster_themes(contents, discovered_labels):
    """
    Extract common words/themes for each cluster.

    This helps interpret what each cluster represents phenomenologically.
    """
    print("\n" + "="*60)
    print("CLUSTER THEMES (common words)")
    print("="*60)

    # Simple word frequency analysis (could be enhanced with TF-IDF)
    import re
    from collections import Counter

    # Words to ignore
    stopwords = set([
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'as', 'is', 'was', 'were', 'been', 'be',
        'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
        'should', 'may', 'might', 'must', 'shall', 'can', 'need', 'dare',
        'it', 'its', 'this', 'that', 'these', 'those', 'i', 'me', 'my',
        'myself', 'we', 'our', 'ours', 'you', 'your', 'yours', 'he', 'him',
        'his', 'she', 'her', 'hers', 'they', 'them', 'their', 'what', 'which',
        'who', 'whom', 'when', 'where', 'why', 'how', 'all', 'each', 'every',
        'both', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor',
        'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very', 'just',
        'about', 'into', 'through', 'during', 'before', 'after', 'above',
        'below', 'between', 'under', 'again', 'further', 'then', 'once',
        'here', 'there', 'up', 'down', 'out', 'off', 'over', 'any', 'if',
        'because', 'until', 'while', 'although', 'though', 'since', 'unless',
        'like', 'just', 'also', 'back', 'even', 'still', 'well', 'around',
        'really', 'something', 'thing', 'things', 'going', 'went', 'got',
        'get', 'know', 'knew', 'think', 'thought', 'see', 'saw', 'seen',
        'said', 'say', 'says', 'told', 'tell', 'one', 'two', 'first', 'time',
        'make', 'made', 'way', 'come', 'came', 'being', 'now', 'never'
    ])

    unique_clusters = sorted(set(discovered_labels))

    for cluster_id in unique_clusters:
        if cluster_id == -1:
            continue

        indices = [i for i, c in enumerate(discovered_labels) if c == cluster_id]

        # Combine all content in cluster
        cluster_text = ' '.join(contents[i] for i in indices)

        # Tokenize and count
        words = re.findall(r'\b[a-z]{3,}\b', cluster_text.lower())
        word_counts = Counter(w for w in words if w not in stopwords)

        top_words = word_counts.most_common(15)

        print(f"\nCluster {cluster_id}: {', '.join(w for w, c in top_words)}")


def update_database(ids, umap_coords_2d, cluster_labels):
    """Store UMAP coordinates and cluster IDs in the database."""
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    # Ensure columns exist
    cur.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                          WHERE table_name='stories' AND column_name='umap_x') THEN
                ALTER TABLE stories ADD COLUMN umap_x FLOAT;
            END IF;
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                          WHERE table_name='stories' AND column_name='umap_y') THEN
                ALTER TABLE stories ADD COLUMN umap_y FLOAT;
            END IF;
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                          WHERE table_name='stories' AND column_name='cluster_id') THEN
                ALTER TABLE stories ADD COLUMN cluster_id INTEGER;
            END IF;
        END $$;
    """)

    # Update each story
    data = [
        (
            float(umap_coords_2d[i, 0]),
            float(umap_coords_2d[i, 1]),
            int(cluster_labels[i]) if cluster_labels[i] >= 0 else None,
            ids[i]
        )
        for i in range(len(ids))
    ]

    cur.executemany("""
        UPDATE stories
        SET umap_x = %s, umap_y = %s, cluster_id = %s
        WHERE id = %s
    """, data)

    conn.commit()
    cur.close()
    conn.close()

    print(f"\nUpdated {len(ids)} stories with UMAP coordinates and cluster IDs")


def main():
    parser = argparse.ArgumentParser(
        description='Cluster paranormal stories to discover natural phenomenological groupings'
    )
    parser.add_argument('--n-neighbors', type=int, default=15,
                       help='UMAP n_neighbors (default: 15, higher=more global structure)')
    parser.add_argument('--min-cluster-size', type=int, default=5,
                       help='HDBSCAN min_cluster_size (default: 5)')
    parser.add_argument('--min-samples', type=int, default=2,
                       help='HDBSCAN min_samples (default: 2)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Analyze without updating database')
    parser.add_argument('--viz-min-dist', type=float, default=0.1,
                       help='UMAP min_dist for 2D visualization (default: 0.1)')
    args = parser.parse_args()

    # Load embeddings
    print("Loading embeddings from database...")
    ids, titles, types, contents, embeddings = get_embeddings()
    print(f"Loaded {len(ids)} stories with {embeddings.shape[1]}-dimensional embeddings")

    if len(ids) < 10:
        print("Not enough stories for meaningful clustering (need at least 10)")
        return

    # Print distribution of existing labels
    type_counts = Counter(types)
    print(f"\nExisting story_type distribution:")
    for t, count in type_counts.most_common():
        print(f"  {t}: {count}")

    # Step 1: UMAP to 5D for clustering (cosine metric)
    coords_5d, _ = run_umap_clustering(
        embeddings,
        n_neighbors=args.n_neighbors,
        n_components=5
    )

    # Step 2: HDBSCAN clustering in 5D space
    cluster_labels, clusterer = run_hdbscan(
        coords_5d,
        min_cluster_size=args.min_cluster_size,
        min_samples=args.min_samples
    )

    # Step 3: Compare discovered clusters to existing labels
    ari, nmi = compare_to_labels(cluster_labels, types)

    # Step 4: Analyze what's in each cluster
    analyze_clusters(titles, types, contents, cluster_labels)

    # Step 5: Extract themes
    extract_cluster_themes(contents, cluster_labels)

    # Step 6: UMAP to 2D for visualization
    coords_2d = run_umap_viz(
        embeddings,
        n_neighbors=args.n_neighbors,
        min_dist=args.viz_min_dist
    )

    print(f"\n2D visualization coordinate ranges:")
    print(f"  X: [{coords_2d[:, 0].min():.2f}, {coords_2d[:, 0].max():.2f}]")
    print(f"  Y: [{coords_2d[:, 1].min():.2f}, {coords_2d[:, 1].max():.2f}]")

    # Step 7: Update database
    if not args.dry_run:
        update_database(ids, coords_2d, cluster_labels)
        print("\nDatabase updated! Run the TUI visualize view to see the scatter plot.")
    else:
        print("\n[DRY RUN] Database not updated.")

    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    n_clusters = len(set(cluster_labels)) - (1 if -1 in cluster_labels else 0)
    n_types = len(set(types))
    print(f"Original story_type categories: {n_types}")
    print(f"Discovered natural clusters: {n_clusters}")
    print(f"Agreement (ARI): {ari:.3f}")

    if ari < 0.3 and n_clusters != n_types:
        print("\n✓ Results suggest natural phenomenological groupings differ")
        print("  from folk categories - consistent with 'brain failure mode' hypothesis")


if __name__ == '__main__':
    main()
