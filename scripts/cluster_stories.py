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
from scipy.cluster.hierarchy import linkage
from scipy.spatial.distance import pdist

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
    Extract phenomenological features for each cluster.

    Categorizes language by:
    - Sensory modality (visual, auditory, tactile, etc.)
    - Entity characteristics (humanoid, shadow, light, etc.)
    - Physical effects (paralysis, cold, touched, etc.)
    - Setting/context (bedroom, night, sleep, etc.)
    - Emotional response (fear, peace, confusion, etc.)

    This helps interpret what "brain state" each cluster might represent.
    """
    print("\n" + "="*60)
    print("PHENOMENOLOGICAL ANALYSIS")
    print("="*60)

    import re
    from collections import Counter

    # Phenomenological feature categories
    # These help identify what type of experience is being described
    feature_categories = {
        'visual': {
            'saw', 'see', 'seen', 'looked', 'looking', 'appeared', 'visible',
            'shape', 'figure', 'form', 'shadow', 'silhouette', 'outline',
            'light', 'bright', 'glow', 'glowing', 'dark', 'darkness',
            'eyes', 'face', 'transparent', 'solid', 'floating', 'hovering'
        },
        'auditory': {
            'heard', 'hear', 'sound', 'sounds', 'noise', 'noises', 'voice',
            'voices', 'whisper', 'whispered', 'scream', 'screamed', 'bang',
            'footsteps', 'knock', 'knocking', 'music', 'singing', 'called',
            'speaking', 'talking', 'loud', 'quiet', 'silent', 'silence'
        },
        'tactile': {
            'felt', 'feel', 'feeling', 'touched', 'touch', 'grabbed',
            'pressure', 'pushed', 'pulled', 'held', 'hand', 'hands',
            'cold', 'warm', 'hot', 'freezing', 'tingling', 'vibration',
            'weight', 'heavy', 'breath', 'breathing'
        },
        'paralysis_sleep': {
            'paralyzed', 'paralysis', "couldn't move", 'frozen', 'stuck',
            'sleep', 'sleeping', 'asleep', 'awake', 'woke', 'waking',
            'dream', 'dreaming', 'bed', 'bedroom', 'laying', 'lying'
        },
        'entity_humanoid': {
            'man', 'woman', 'person', 'figure', 'someone', 'somebody',
            'human', 'people', 'child', 'children', 'old', 'tall',
            'standing', 'walking', 'sat', 'sitting', 'wearing', 'clothes'
        },
        'entity_shadow': {
            'shadow', 'shadows', 'dark', 'black', 'silhouette', 'outline',
            'darker', 'blackness', 'mass', 'blob', 'shapeless'
        },
        'entity_light': {
            'light', 'lights', 'bright', 'glowing', 'orb', 'orbs',
            'white', 'beam', 'flash', 'shining', 'luminous', 'radiant'
        },
        'movement_behavior': {
            'moved', 'moving', 'approached', 'coming', 'left', 'disappeared',
            'vanished', 'flew', 'flying', 'floated', 'floating', 'hovered',
            'watching', 'staring', 'followed', 'following', 'chased'
        },
        'physical_effects': {
            'moved', 'fell', 'opened', 'closed', 'door', 'doors',
            'objects', 'thrown', 'knocked', 'slammed', 'lights',
            'electronics', 'turned', 'unplugged', 'batteries'
        },
        'time_context': {
            'night', 'midnight', 'morning', 'evening', 'afternoon',
            '3am', 'dark', 'daylight', 'hours', 'minutes', 'seconds',
            'suddenly', 'instant', 'moment', 'childhood', 'years'
        },
        'location_setting': {
            'house', 'home', 'room', 'bedroom', 'bathroom', 'kitchen',
            'hallway', 'stairs', 'basement', 'attic', 'outside', 'woods',
            'forest', 'road', 'car', 'driving', 'field', 'cemetery'
        },
        'emotional': {
            'scared', 'afraid', 'fear', 'terrified', 'terror', 'panic',
            'calm', 'peaceful', 'peace', 'confused', 'curious',
            'angry', 'sad', 'happy', 'comfort', 'dread', 'uneasy'
        }
    }

    # General stopwords (for "other notable" section)
    stopwords = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'as', 'is', 'was', 'were', 'been', 'be',
        'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
        'should', 'may', 'might', 'must', 'shall', 'can', 'need', 'it', 'its',
        'this', 'that', 'these', 'those', 'i', 'me', 'my', 'myself', 'we',
        'our', 'you', 'your', 'he', 'him', 'his', 'she', 'her', 'they', 'them',
        'their', 'what', 'which', 'who', 'when', 'where', 'why', 'how', 'all',
        'each', 'every', 'both', 'few', 'more', 'most', 'other', 'some', 'no',
        'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very', 'just',
        'about', 'into', 'through', 'during', 'before', 'after', 'above',
        'below', 'between', 'under', 'again', 'then', 'once', 'here', 'there',
        'up', 'down', 'out', 'off', 'over', 'any', 'if', 'because', 'until',
        'while', 'although', 'though', 'since', 'unless', 'like', 'also',
        'back', 'even', 'still', 'well', 'around', 'really', 'something',
        'thing', 'things', 'going', 'went', 'got', 'get', 'know', 'knew',
        'think', 'thought', 'said', 'say', 'told', 'tell', 'one', 'two',
        'first', 'time', 'make', 'made', 'way', 'come', 'came', 'being', 'now',
        'never', 'always', 'much', 'many', 'such', 'kind', 'started', 'began',
        'point', 'looked', 'looking', 'asked', 'didn', 'don', 'couldn', 'wasn',
        'weren', 'isn', 'aren', 'hadn', 'wouldn', 'shouldn', 'hasn', 'haven',
        'let', 'getting', 'yes', 'yeah', 'okay', 'right', 'left', 'sure'
    }

    unique_clusters = sorted(set(discovered_labels))

    for cluster_id in unique_clusters:
        if cluster_id == -1:
            continue

        indices = [i for i, c in enumerate(discovered_labels) if c == cluster_id]

        # Combine all content in cluster
        cluster_text = ' '.join(contents[i] for i in indices).lower()

        # Tokenize
        words = re.findall(r'\b[a-z]{3,}\b', cluster_text)
        word_counts = Counter(words)
        total_words = len(words)

        print(f"\n{'='*50}")
        print(f"CLUSTER {cluster_id} ({len(indices)} stories)")
        print(f"{'='*50}")

        # Score each phenomenological category
        category_scores = {}
        category_words = {}

        for category, keywords in feature_categories.items():
            matches = [(w, word_counts[w]) for w in keywords if word_counts[w] > 0]
            if matches:
                score = sum(c for _, c in matches)
                category_scores[category] = score
                category_words[category] = sorted(matches, key=lambda x: -x[1])[:5]

        # Sort categories by score
        sorted_categories = sorted(category_scores.items(), key=lambda x: -x[1])

        if sorted_categories:
            print("\nDominant phenomenological features:")
            for category, score in sorted_categories[:6]:
                words_str = ', '.join(f"{w}({c})" for w, c in category_words[category][:4])
                print(f"  {category.upper():20} [{score:3}] {words_str}")

        # Find notable words not in any category
        all_category_words = set()
        for keywords in feature_categories.values():
            all_category_words.update(keywords)

        other_words = [
            (w, c) for w, c in word_counts.most_common(50)
            if w not in all_category_words and w not in stopwords and c >= 2
        ]

        if other_words[:8]:
            print(f"\n  Other notable: {', '.join(w for w, c in other_words[:8])}")

        # Suggest possible interpretation
        if sorted_categories:
            top_cats = [c for c, _ in sorted_categories[:3]]
            print(f"\n  → Possible interpretation: ", end="")

            if 'paralysis_sleep' in top_cats and 'entity_shadow' in top_cats:
                print("Hypnagogic/hypnopompic hallucination (sleep paralysis)")
            elif 'entity_light' in top_cats and 'movement_behavior' in top_cats:
                print("Luminous aerial phenomenon")
            elif 'auditory' in top_cats and not 'visual' in top_cats[:2]:
                print("Auditory hallucination / EVP-type experience")
            elif 'physical_effects' in top_cats:
                print("Poltergeist-type / PK phenomenon")
            elif 'entity_humanoid' in top_cats and 'emotional' in top_cats:
                print("Apparitional experience (full figure)")
            elif 'tactile' in top_cats:
                print("Somatic/tactile hallucination")
            elif 'entity_shadow' in top_cats:
                print("Shadow figure phenomenon")
            elif 'visual' in top_cats and 'time_context' in top_cats:
                print("Brief visual anomaly")
            else:
                print("Mixed/unclassified phenomenology")


def analyze_hierarchy(coords_5d, cluster_labels, titles):
    """
    Analyze hierarchical relationships between clusters.

    Shows which clusters are most similar to each other,
    revealing potential meta-categories (e.g., "sleep-related phenomena").
    """
    print("\n" + "="*60)
    print("HIERARCHICAL CLUSTER RELATIONSHIPS")
    print("="*60)

    # Get unique clusters (excluding noise)
    unique_clusters = sorted(set(c for c in cluster_labels if c >= 0))

    if len(unique_clusters) < 2:
        print("Need at least 2 clusters for hierarchy analysis")
        return

    # Compute cluster centroids
    centroids = []
    cluster_names = []
    for cluster_id in unique_clusters:
        mask = cluster_labels == cluster_id
        centroid = coords_5d[mask].mean(axis=0)
        centroids.append(centroid)
        cluster_names.append(f"Cluster {cluster_id}")

    centroids = np.array(centroids)

    # Compute hierarchical clustering on centroids
    distances = pdist(centroids, metric='euclidean')
    Z = linkage(distances, method='ward')

    # Print merge order (text-based dendrogram)
    print("\nCluster merge order (most similar → least similar):")
    n = len(unique_clusters)
    cluster_map = {i: cluster_names[i] for i in range(n)}

    for i, (c1, c2, dist, _) in enumerate(Z):
        c1, c2 = int(c1), int(c2)
        name1 = cluster_map.get(c1, f"Group {c1-n+1}")
        name2 = cluster_map.get(c2, f"Group {c2-n+1}")
        new_name = f"({name1} + {name2})"
        cluster_map[n + i] = new_name
        print(f"  {dist:6.2f}: {name1} ↔ {name2}")


def analyze_stability(embeddings, n_neighbors_range=[10, 15, 20, 25],
                     min_cluster_sizes=[3, 5, 7]):
    """
    Test cluster stability across different parameters.

    Robust clusters should form consistently regardless of parameter choices.
    """
    from sklearn.metrics import adjusted_rand_score

    print("\n" + "="*60)
    print("CLUSTER STABILITY ANALYSIS")
    print("="*60)
    print("Testing if clusters are robust to parameter changes...\n")

    results = []

    # Run with different parameter combinations
    for n_neighbors in n_neighbors_range:
        for min_cluster_size in min_cluster_sizes:
            # UMAP
            reducer = umap.UMAP(
                n_neighbors=n_neighbors,
                n_components=5,
                min_dist=0.0,
                metric='cosine',
                random_state=42,
                verbose=False
            )
            coords = reducer.fit_transform(embeddings)

            # HDBSCAN
            clusterer = hdbscan.HDBSCAN(
                min_cluster_size=min_cluster_size,
                min_samples=2,
                metric='euclidean'
            )
            labels = clusterer.fit_predict(coords)

            n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
            noise_pct = sum(1 for l in labels if l == -1) / len(labels)

            results.append({
                'n_neighbors': n_neighbors,
                'min_cluster_size': min_cluster_size,
                'labels': labels,
                'n_clusters': n_clusters,
                'noise_pct': noise_pct
            })

    # Compare all pairs of results
    print("Parameter combinations tested:")
    for r in results:
        print(f"  n_neighbors={r['n_neighbors']:2}, min_cluster_size={r['min_cluster_size']}: "
              f"{r['n_clusters']} clusters, {r['noise_pct']:.1%} noise")

    # Find the most stable result (highest average ARI with others)
    print("\nStability scores (average ARI with other parameter settings):")
    stabilities = []
    for i, r1 in enumerate(results):
        aris = []
        for j, r2 in enumerate(results):
            if i != j:
                ari = adjusted_rand_score(r1['labels'], r2['labels'])
                aris.append(ari)
        avg_ari = np.mean(aris)
        stabilities.append((avg_ari, r1))
        print(f"  n={r1['n_neighbors']:2}, mcs={r1['min_cluster_size']}: stability={avg_ari:.3f}")

    # Recommend most stable
    stabilities.sort(reverse=True)
    best = stabilities[0][1]
    print(f"\n→ Most stable parameters: n_neighbors={best['n_neighbors']}, "
          f"min_cluster_size={best['min_cluster_size']}")

    return best['labels']


def analyze_soft_membership(clusterer, coords_5d, titles, threshold=0.3):
    """
    Analyze soft cluster membership probabilities.

    Stories with low confidence may represent transitional experiences
    or mixed phenomena - interesting edge cases.
    """
    print("\n" + "="*60)
    print("SOFT CLUSTER MEMBERSHIP")
    print("="*60)

    # Get soft cluster assignments
    soft_clusters = hdbscan.all_points_membership_vectors(clusterer)

    print("\nStories with ambiguous cluster membership (max prob < 70%):")
    print("These may represent transitional or mixed experiences.\n")

    ambiguous = []
    for i, probs in enumerate(soft_clusters):
        max_prob = probs.max()
        if max_prob < 0.7 and max_prob > 0:  # Not noise, but uncertain
            top_2 = np.argsort(probs)[-2:][::-1]
            ambiguous.append({
                'title': titles[i],
                'probs': probs,
                'max_prob': max_prob,
                'top_clusters': [(c, probs[c]) for c in top_2 if probs[c] > 0.1]
            })

    ambiguous.sort(key=lambda x: x['max_prob'])

    for item in ambiguous[:10]:  # Show top 10 most ambiguous
        title = item['title'][:45] + "..." if len(item['title']) > 45 else item['title']
        clusters_str = ", ".join(f"C{c}:{p:.0%}" for c, p in item['top_clusters'])
        print(f"  [{item['max_prob']:.0%}] {title}")
        print(f"       → {clusters_str}")

    if len(ambiguous) > 10:
        print(f"  ... and {len(ambiguous) - 10} more ambiguous stories")

    return soft_clusters


def run_bertopic(contents, embeddings):
    """
    Run BERTopic to get interpretable topic labels for clusters.

    BERTopic extracts representative words/phrases for each topic,
    making clusters more interpretable.
    """
    try:
        from bertopic import BERTopic
    except ImportError:
        print("\n[BERTopic not installed - skipping topic extraction]")
        print("  Install with: pip install bertopic")
        return None

    print("\n" + "="*60)
    print("BERTOPIC ANALYSIS")
    print("="*60)
    print("Extracting interpretable topic labels...\n")

    # Configure BERTopic to use our pre-computed embeddings
    topic_model = BERTopic(
        embedding_model=None,  # We provide embeddings
        umap_model=umap.UMAP(
            n_neighbors=15,
            n_components=5,
            min_dist=0.0,
            metric='cosine',
            random_state=42
        ),
        hdbscan_model=hdbscan.HDBSCAN(
            min_cluster_size=5,
            min_samples=2,
            metric='euclidean',
            prediction_data=True
        ),
        verbose=False
    )

    topics, probs = topic_model.fit_transform(contents, embeddings=embeddings)

    # Get topic info
    topic_info = topic_model.get_topic_info()

    print("Discovered topics with representative words:\n")
    for _, row in topic_info.iterrows():
        topic_id = row['Topic']
        if topic_id == -1:
            continue  # Skip outlier topic
        count = row['Count']
        # Get top words for this topic
        topic_words = topic_model.get_topic(topic_id)
        if topic_words:
            words = [w for w, _ in topic_words[:6]]
            print(f"  Topic {topic_id} ({count} stories): {', '.join(words)}")

    return topic_model


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
    parser.add_argument('--stability', action='store_true',
                       help='Run cluster stability analysis across parameters')
    parser.add_argument('--hierarchy', action='store_true',
                       help='Show hierarchical relationships between clusters')
    parser.add_argument('--soft', action='store_true',
                       help='Show soft cluster membership (ambiguous stories)')
    parser.add_argument('--bertopic', action='store_true',
                       help='Run BERTopic for interpretable topic labels')
    parser.add_argument('--all-analysis', action='store_true',
                       help='Run all analysis types')
    args = parser.parse_args()

    # --all-analysis enables all optional analyses
    if args.all_analysis:
        args.stability = True
        args.hierarchy = True
        args.soft = True
        args.bertopic = True

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

    # Step 6: Hierarchical analysis (optional)
    if args.hierarchy:
        analyze_hierarchy(coords_5d, cluster_labels, titles)

    # Step 7: Soft membership analysis (optional)
    if args.soft:
        analyze_soft_membership(clusterer, coords_5d, titles)

    # Step 8: Stability analysis (optional)
    if args.stability:
        analyze_stability(embeddings)

    # Step 9: BERTopic analysis (optional)
    if args.bertopic:
        run_bertopic(contents, embeddings)

    # Step 10: UMAP to 2D for visualization
    coords_2d = run_umap_viz(
        embeddings,
        n_neighbors=args.n_neighbors,
        min_dist=args.viz_min_dist
    )

    print(f"\n2D visualization coordinate ranges:")
    print(f"  X: [{coords_2d[:, 0].min():.2f}, {coords_2d[:, 0].max():.2f}]")
    print(f"  Y: [{coords_2d[:, 1].min():.2f}, {coords_2d[:, 1].max():.2f}]")

    # Step 11: Update database
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
