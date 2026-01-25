#!/usr/bin/env python3
"""
Parse the PostgreSQL dump and run UMAP + HDBSCAN clustering.
Works without needing a running database.
"""

import re
import numpy as np
import sys

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


def parse_dump(filepath):
    """Parse the PostgreSQL dump file and extract story data."""
    stories = []

    with open(filepath, 'r') as f:
        content = f.read()

    # Find the COPY block for stories
    match = re.search(
        r'COPY public\.stories \([^)]+\) FROM stdin;\n(.*?)\n\\.',
        content,
        re.DOTALL
    )

    if not match:
        print("ERROR: Could not find stories data in dump")
        sys.exit(1)

    lines = match.group(1).strip().split('\n')

    # Columns: id, episode_id, transcript_id, title, summary, content,
    #          start_time_seconds, end_time_seconds, story_type, location,
    #          time_period, is_first_person, token_count, embedding_method,
    #          embedding, umap_x, umap_y, umap_computed_at, created_at,
    #          updated_at, cluster_id

    for line in lines:
        fields = line.split('\t')
        if len(fields) < 15:
            continue

        story_id = fields[0]
        title = fields[3]
        content = fields[5]
        story_type = fields[8] if fields[8] != '\\N' else 'unknown'
        location = fields[9] if fields[9] != '\\N' else None
        embedding_str = fields[14]

        # Parse embedding: [0.1,0.2,...] format
        if embedding_str and embedding_str != '\\N':
            try:
                vec_str = embedding_str.strip('[]')
                embedding = np.array([float(x) for x in vec_str.split(',')])

                stories.append({
                    'id': story_id,
                    'title': title,
                    'content': content,
                    'story_type': story_type,
                    'location': location,
                    'embedding': embedding
                })
            except Exception as e:
                print(f"Warning: Could not parse embedding for {title}: {e}")

    return stories


def run_clustering(stories, n_neighbors=15, min_cluster_size=5):
    """Run UMAP + HDBSCAN clustering."""

    embeddings = np.array([s['embedding'] for s in stories])
    types = [s['story_type'] for s in stories]

    print(f"\n=== Clustering {len(stories)} stories ===")
    print(f"Embedding dimensions: {embeddings.shape[1]}")

    # UMAP for clustering (5D)
    print("\nRunning UMAP (5D for clustering)...")
    reducer_5d = umap.UMAP(
        n_neighbors=n_neighbors,
        n_components=5,
        metric='cosine',
        min_dist=0.0,
        random_state=42
    )
    embedding_5d = reducer_5d.fit_transform(embeddings)

    # HDBSCAN clustering
    print(f"Running HDBSCAN (min_cluster_size={min_cluster_size})...")
    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=2,
        metric='euclidean',
        cluster_selection_method='eom'
    )
    cluster_labels = clusterer.fit_predict(embedding_5d)

    # UMAP for visualization (2D)
    print("Running UMAP (2D for visualization)...")
    reducer_2d = umap.UMAP(
        n_neighbors=n_neighbors,
        n_components=2,
        metric='cosine',
        min_dist=0.1,
        random_state=42
    )
    embedding_2d = reducer_2d.fit_transform(embeddings)

    # Store results
    for i, story in enumerate(stories):
        story['cluster_id'] = int(cluster_labels[i])
        story['umap_x'] = float(embedding_2d[i, 0])
        story['umap_y'] = float(embedding_2d[i, 1])

    return stories, cluster_labels


def analyze_clusters(stories, cluster_labels):
    """Analyze clustering results."""

    types = [s['story_type'] for s in stories]

    # Basic stats
    n_clusters = len(set(cluster_labels)) - (1 if -1 in cluster_labels else 0)
    n_noise = list(cluster_labels).count(-1)

    print(f"\n=== Clustering Results ===")
    print(f"Clusters found: {n_clusters}")
    print(f"Noise points: {n_noise} ({100*n_noise/len(stories):.1f}%)")

    # Compare to folk labels
    le = LabelEncoder()
    type_encoded = le.fit_transform(types)

    # Filter out noise for comparison
    mask = cluster_labels != -1
    if mask.sum() > 0:
        ari = adjusted_rand_score(type_encoded[mask], cluster_labels[mask])
        nmi = normalized_mutual_info_score(type_encoded[mask], cluster_labels[mask])
        print(f"\nComparison to story_type labels:")
        print(f"  Adjusted Rand Index: {ari:.3f}")
        print(f"  Normalized Mutual Info: {nmi:.3f}")
        print(f"  (1.0 = perfect match, 0.0 = random)")

    # Cluster breakdown
    print(f"\n=== Cluster Composition ===")
    from collections import Counter

    for cluster_id in sorted(set(cluster_labels)):
        if cluster_id == -1:
            label = "NOISE"
        else:
            label = f"Cluster {cluster_id}"

        cluster_stories = [s for s in stories if s['cluster_id'] == cluster_id]
        type_counts = Counter(s['story_type'] for s in cluster_stories)

        print(f"\n{label} ({len(cluster_stories)} stories):")
        for t, count in type_counts.most_common(5):
            print(f"  {t}: {count}")

        # Show some titles
        print(f"  Examples:")
        for s in cluster_stories[:3]:
            print(f"    - {s['title'][:60]}")

    return n_clusters


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--dump', default='data/paranormal_tracker.sql')
    parser.add_argument('--n-neighbors', type=int, default=15)
    parser.add_argument('--min-cluster-size', type=int, default=5)
    args = parser.parse_args()

    print(f"Parsing {args.dump}...")
    stories = parse_dump(args.dump)
    print(f"Found {len(stories)} stories with embeddings")

    # Show type distribution
    from collections import Counter
    type_counts = Counter(s['story_type'] for s in stories)
    print(f"\nStory types:")
    for t, c in type_counts.most_common():
        print(f"  {t}: {c}")

    stories, cluster_labels = run_clustering(
        stories,
        n_neighbors=args.n_neighbors,
        min_cluster_size=args.min_cluster_size
    )

    analyze_clusters(stories, cluster_labels)


if __name__ == '__main__':
    main()
