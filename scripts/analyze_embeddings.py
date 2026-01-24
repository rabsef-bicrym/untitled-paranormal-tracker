#!/usr/bin/env python3
"""
Analyze story embeddings: t-SNE dimensionality reduction + clustering.

This script:
1. Loads all story embeddings from the database
2. Runs t-SNE to reduce 1024D → 2D for visualization
3. Runs DBSCAN/Agglomerative clustering to find natural groups
4. Stores umap_x, umap_y, and cluster_id back in the database

Usage:
    python scripts/analyze_embeddings.py
    python scripts/analyze_embeddings.py --perplexity 30
    python scripts/analyze_embeddings.py --method pca  # faster but less accurate
"""

import argparse
import os
import numpy as np
import psycopg2
from sklearn.manifold import TSNE
from sklearn.decomposition import PCA
from sklearn.cluster import DBSCAN, AgglomerativeClustering
from sklearn.preprocessing import StandardScaler

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
        SELECT id, title, story_type, embedding::text
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
    embeddings = []

    for row in rows:
        ids.append(row[0])
        titles.append(row[1])
        types.append(row[2])
        # Parse the vector string: [0.1,0.2,...] -> numpy array
        vec_str = row[3].strip('[]')
        vec = np.array([float(x) for x in vec_str.split(',')])
        embeddings.append(vec)

    return ids, titles, types, np.array(embeddings)


def run_tsne(embeddings, perplexity=30, learning_rate='auto'):
    """Run t-SNE dimensionality reduction."""
    print(f"Running t-SNE (perplexity={perplexity})...")

    # For small datasets, perplexity must be less than n_samples
    perplexity = min(perplexity, len(embeddings) - 1)

    tsne = TSNE(
        n_components=2,
        perplexity=perplexity,
        learning_rate=learning_rate,
        random_state=42,
        init='pca',
        max_iter=1000
    )

    coords = tsne.fit_transform(embeddings)
    return coords


def run_pca(embeddings):
    """Run PCA dimensionality reduction (faster, less accurate for viz)."""
    print("Running PCA...")

    pca = PCA(n_components=2, random_state=42)
    coords = pca.fit_transform(embeddings)

    print(f"  Explained variance: {pca.explained_variance_ratio_.sum():.1%}")
    return coords


def run_clustering(coords, method='agglomerative', n_clusters=None, eps=None):
    """Run clustering on 2D coordinates."""
    print(f"Running {method} clustering...")

    if method == 'dbscan':
        # DBSCAN finds clusters automatically
        if eps is None:
            # Estimate eps from data spread
            from sklearn.neighbors import NearestNeighbors
            nn = NearestNeighbors(n_neighbors=2)
            nn.fit(coords)
            distances, _ = nn.kneighbors(coords)
            eps = np.percentile(distances[:, 1], 90)

        clusterer = DBSCAN(eps=eps, min_samples=2)
        labels = clusterer.fit_predict(coords)
    else:
        # Agglomerative clustering - need to specify n_clusters
        if n_clusters is None:
            # Estimate reasonable number of clusters
            n_clusters = max(3, len(coords) // 10)

        clusterer = AgglomerativeClustering(
            n_clusters=n_clusters,
            metric='euclidean',
            linkage='ward'
        )
        labels = clusterer.fit_predict(coords)

    return labels


def update_database(ids, umap_coords, cluster_labels):
    """Store UMAP coordinates and cluster IDs back in the database."""
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
    data = [(float(umap_coords[i, 0]), float(umap_coords[i, 1]),
             int(cluster_labels[i]) if cluster_labels[i] >= 0 else None,
             ids[i])
            for i in range(len(ids))]

    cur.executemany("""
        UPDATE stories
        SET umap_x = %s, umap_y = %s, cluster_id = %s
        WHERE id = %s
    """, data)

    conn.commit()
    cur.close()
    conn.close()

    print(f"Updated {len(ids)} stories with UMAP coordinates and cluster IDs")


def print_cluster_analysis(titles, types, cluster_labels):
    """Print analysis of discovered clusters."""
    unique_clusters = set(cluster_labels)
    n_clusters = len([c for c in unique_clusters if c >= 0])
    n_noise = sum(1 for c in cluster_labels if c < 0)

    print(f"\n{'='*60}")
    print(f"CLUSTER ANALYSIS")
    print(f"{'='*60}")
    print(f"Total stories: {len(titles)}")
    print(f"Clusters found: {n_clusters}")
    print(f"Noise points (unclustered): {n_noise}")

    # Analyze each cluster
    for cluster_id in sorted(unique_clusters):
        if cluster_id < 0:
            continue

        indices = [i for i, c in enumerate(cluster_labels) if c == cluster_id]
        cluster_types = [types[i] for i in indices]
        cluster_titles = [titles[i] for i in indices]

        # Count types in this cluster
        type_counts = {}
        for t in cluster_types:
            type_counts[t] = type_counts.get(t, 0) + 1

        print(f"\n--- Cluster {cluster_id} ({len(indices)} stories) ---")
        print(f"Dominant types: {sorted(type_counts.items(), key=lambda x: -x[1])[:3]}")
        print(f"Stories:")
        for title in cluster_titles[:5]:
            print(f"  - {title}")
        if len(cluster_titles) > 5:
            print(f"  ... and {len(cluster_titles) - 5} more")


def main():
    parser = argparse.ArgumentParser(description='Analyze story embeddings with t-SNE + clustering')
    parser.add_argument('--method', choices=['tsne', 'pca'], default='tsne',
                       help='Dimensionality reduction method (default: tsne)')
    parser.add_argument('--perplexity', type=int, default=15,
                       help='t-SNE perplexity parameter (default: 15)')
    parser.add_argument('--cluster-method', choices=['dbscan', 'agglomerative'], default='agglomerative',
                       help='Clustering method (default: agglomerative)')
    parser.add_argument('--n-clusters', type=int, default=None,
                       help='Number of clusters for agglomerative (default: auto)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Run analysis but do not update database')
    args = parser.parse_args()

    # Load embeddings
    print("Loading embeddings from database...")
    ids, titles, types, embeddings = get_embeddings()
    print(f"Loaded {len(ids)} stories with {embeddings.shape[1]}-dimensional embeddings")

    if len(ids) < 5:
        print("Not enough stories for meaningful analysis (need at least 5)")
        return

    # Run dimensionality reduction
    if args.method == 'tsne':
        coords = run_tsne(embeddings, perplexity=min(args.perplexity, len(ids) - 1))
    else:
        coords = run_pca(embeddings)

    # Run clustering on 2D coordinates
    cluster_labels = run_clustering(
        coords,
        method=args.cluster_method,
        n_clusters=args.n_clusters
    )

    # Print analysis
    print_cluster_analysis(titles, types, cluster_labels)

    # Print coordinate ranges for TUI
    print(f"\n2D coordinate ranges:")
    print(f"  X: [{coords[:, 0].min():.2f}, {coords[:, 0].max():.2f}]")
    print(f"  Y: [{coords[:, 1].min():.2f}, {coords[:, 1].max():.2f}]")

    # Update database
    if not args.dry_run:
        update_database(ids, coords, cluster_labels)
        print("\nDatabase updated! Run the TUI visualize view to see the scatter plot.")
    else:
        print("\n[DRY RUN] Database not updated.")


if __name__ == '__main__':
    main()
