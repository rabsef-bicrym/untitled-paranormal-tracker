"""FastAPI backend for Paranormal Tracker."""

from contextlib import asynccontextmanager
from datetime import date
from typing import Optional
import time
import httpx

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from database import get_db_cursor
from models import (
    StoryListItem, StoryDetail, SearchRequest, SearchResult,
    MapStory, VectorSpacePoint, StatsResponse,
    FRAMEWORK_CATEGORIES, get_frameworks_for_type
)
from geocoding import geocode_location


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Verify database connection on startup
    try:
        with get_db_cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM stories")
            count = cur.fetchone()["count"]
            print(f"Connected to database. Found {count} stories.")
    except Exception as e:
        print(f"Warning: Database connection failed: {e}")
    yield


app = FastAPI(
    title="Paranormal Tracker API",
    description="API for searching and visualizing paranormal stories",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_query_embedding(query: str, max_retries: int = 3) -> Optional[list[float]]:
    """Get embedding for search query via Voyage AI."""
    if not settings.voyage_api_key:
        return None

    for attempt in range(max_retries):
        try:
            response = httpx.post(
                settings.voyage_api_url,
                headers={
                    "Authorization": f"Bearer {settings.voyage_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.voyage_model,
                    "input": [query],
                },
                timeout=30.0,
            )

            if response.status_code == 429:
                wait_time = 2 ** attempt
                time.sleep(wait_time)
                continue

            response.raise_for_status()
            result = response.json()
            return result["data"][0]["embedding"]
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"Embedding failed: {e}")
                return None
            time.sleep(1)

    return None


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Paranormal Tracker API", "version": "1.0.0"}


@app.get("/api/health")
async def health():
    """Health check endpoint."""
    try:
        with get_db_cursor() as cur:
            cur.execute("SELECT 1")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        # Return degraded status but still 200 for basic health checks
        return {"status": "degraded", "database": "disconnected", "error": str(e)}


@app.get("/api/stats", response_model=StatsResponse)
async def get_stats():
    """Get database statistics."""
    with get_db_cursor() as cur:
        # Total stories
        cur.execute("SELECT COUNT(*) FROM stories")
        total = cur.fetchone()["count"]

        # Stories with location
        cur.execute("SELECT COUNT(*) FROM stories WHERE location IS NOT NULL AND location != ''")
        with_location = cur.fetchone()["count"]

        # Stories with embedding
        cur.execute("SELECT COUNT(*) FROM stories WHERE embedding IS NOT NULL")
        with_embedding = cur.fetchone()["count"]

        # Stories with UMAP
        cur.execute("SELECT COUNT(*) FROM stories WHERE umap_x IS NOT NULL AND umap_y IS NOT NULL")
        with_umap = cur.fetchone()["count"]

        # Story types count
        cur.execute("""
            SELECT story_type, COUNT(*) as count
            FROM stories
            WHERE story_type IS NOT NULL
            GROUP BY story_type
            ORDER BY count DESC
        """)
        story_types = {row["story_type"]: row["count"] for row in cur.fetchall()}

    # Calculate framework statistics
    frameworks = {}
    for framework_key, framework in FRAMEWORK_CATEGORIES.items():
        frameworks[framework_key] = {}
        for category, types in framework["categories"].items():
            count = sum(story_types.get(t, 0) for t in types)
            frameworks[framework_key][category] = count

    return StatsResponse(
        total_stories=total,
        stories_with_location=with_location,
        stories_with_embedding=with_embedding,
        stories_with_umap=with_umap,
        story_types=story_types,
        frameworks=frameworks,
    )


@app.get("/api/stories", response_model=list[StoryListItem])
async def list_stories(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    story_type: Optional[str] = None,
    framework: Optional[str] = None,
    framework_category: Optional[str] = None,
):
    """List stories with optional filtering."""
    # Build type filter from framework if specified
    type_filter = []
    if framework and framework in FRAMEWORK_CATEGORIES:
        fw = FRAMEWORK_CATEGORIES[framework]
        if framework_category and framework_category in fw["categories"]:
            type_filter = fw["categories"][framework_category]
        else:
            # All types in this framework
            for types in fw["categories"].values():
                type_filter.extend(types)
            type_filter = list(set(type_filter))
    elif story_type:
        type_filter = [story_type]

    with get_db_cursor() as cur:
        if type_filter:
            cur.execute("""
                SELECT
                    s.id::text, s.title, s.story_type, s.location, s.summary,
                    e.podcast_name, e.air_date,
                    s.umap_x, s.umap_y
                FROM stories s
                LEFT JOIN episodes e ON s.episode_id = e.id
                WHERE s.story_type = ANY(%s)
                ORDER BY e.air_date DESC NULLS LAST, s.created_at DESC
                LIMIT %s OFFSET %s
            """, (type_filter, limit, offset))
        else:
            cur.execute("""
                SELECT
                    s.id::text, s.title, s.story_type, s.location, s.summary,
                    e.podcast_name, e.air_date,
                    s.umap_x, s.umap_y
                FROM stories s
                LEFT JOIN episodes e ON s.episode_id = e.id
                ORDER BY e.air_date DESC NULLS LAST, s.created_at DESC
                LIMIT %s OFFSET %s
            """, (limit, offset))

        rows = cur.fetchall()

    stories = []
    for row in rows:
        geo = geocode_location(row["location"]) if row["location"] else None
        story = StoryListItem(
            id=row["id"],
            title=row["title"],
            story_type=row["story_type"],
            location=row["location"],
            summary=row["summary"],
            podcast_name=row["podcast_name"],
            air_date=row["air_date"],
            umap_x=row["umap_x"],
            umap_y=row["umap_y"],
            lat=geo.lat if geo else None,
            lng=geo.lng if geo else None,
            frameworks=get_frameworks_for_type(row["story_type"]) if row["story_type"] else None,
        )
        stories.append(story)

    return stories


@app.get("/api/stories/{story_id}", response_model=StoryDetail)
async def get_story(story_id: str):
    """Get a single story by ID."""
    with get_db_cursor() as cur:
        cur.execute("""
            SELECT
                s.id::text, s.title, s.story_type, s.location, s.content, s.summary,
                s.start_time_seconds, s.end_time_seconds, s.time_period,
                s.is_first_person, s.umap_x, s.umap_y, s.created_at,
                e.podcast_name, e.air_date
            FROM stories s
            LEFT JOIN episodes e ON s.episode_id = e.id
            WHERE s.id = %s::uuid
        """, (story_id,))
        row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Story not found")

    geo = geocode_location(row["location"]) if row["location"] else None

    return StoryDetail(
        id=row["id"],
        title=row["title"],
        story_type=row["story_type"],
        location=row["location"],
        content=row["content"],
        summary=row["summary"],
        podcast_name=row["podcast_name"],
        air_date=row["air_date"],
        start_time_seconds=row["start_time_seconds"],
        end_time_seconds=row["end_time_seconds"],
        time_period=row["time_period"],
        is_first_person=row["is_first_person"],
        umap_x=row["umap_x"],
        umap_y=row["umap_y"],
        lat=geo.lat if geo else None,
        lng=geo.lng if geo else None,
        created_at=row["created_at"],
        frameworks=get_frameworks_for_type(row["story_type"]) if row["story_type"] else None,
    )


@app.post("/api/search", response_model=list[SearchResult])
async def search_stories(request: SearchRequest):
    """Search stories using text, vector, or hybrid search."""
    type_filter = []
    if request.framework and request.framework in FRAMEWORK_CATEGORIES:
        fw = FRAMEWORK_CATEGORIES[request.framework]
        if request.framework_category and request.framework_category in fw["categories"]:
            type_filter = fw["categories"][request.framework_category]
        else:
            for types in fw["categories"].values():
                type_filter.extend(types)
            type_filter = list(set(type_filter))
    elif request.story_types:
        type_filter = request.story_types

    # Get query embedding for vector/hybrid search
    query_embedding = None
    if request.search_type in ("vector", "hybrid"):
        query_embedding = get_query_embedding(request.query)
        if not query_embedding and request.search_type == "vector":
            raise HTTPException(status_code=400, detail="Vector search requires embedding API")

    results = []

    with get_db_cursor() as cur:
        if request.search_type == "text" or (request.search_type == "hybrid" and not query_embedding):
            # Text search
            if type_filter:
                cur.execute("""
                    SELECT
                        s.id::text, s.title, s.story_type, s.location,
                        e.podcast_name, e.air_date,
                        ts_rank(s.search_vector, plainto_tsquery('english', %s)) as rank,
                        substring(s.content, 1, 200) as snippet,
                        s.umap_x, s.umap_y
                    FROM stories s
                    LEFT JOIN episodes e ON s.episode_id = e.id
                    WHERE s.search_vector @@ plainto_tsquery('english', %s)
                      AND s.story_type = ANY(%s)
                    ORDER BY rank DESC
                    LIMIT %s
                """, (request.query, request.query, type_filter, request.limit))
            else:
                cur.execute("""
                    SELECT
                        s.id::text, s.title, s.story_type, s.location,
                        e.podcast_name, e.air_date,
                        ts_rank(s.search_vector, plainto_tsquery('english', %s)) as rank,
                        substring(s.content, 1, 200) as snippet,
                        s.umap_x, s.umap_y
                    FROM stories s
                    LEFT JOIN episodes e ON s.episode_id = e.id
                    WHERE s.search_vector @@ plainto_tsquery('english', %s)
                    ORDER BY rank DESC
                    LIMIT %s
                """, (request.query, request.query, request.limit))

            for row in cur.fetchall():
                geo = geocode_location(row["location"]) if row["location"] else None
                results.append(SearchResult(
                    id=row["id"],
                    title=row["title"],
                    story_type=row["story_type"],
                    location=row["location"],
                    podcast_name=row["podcast_name"],
                    air_date=row["air_date"],
                    score=row["rank"],
                    text_score=row["rank"],
                    snippet=row["snippet"],
                    umap_x=row["umap_x"],
                    umap_y=row["umap_y"],
                    lat=geo.lat if geo else None,
                    lng=geo.lng if geo else None,
                    frameworks=get_frameworks_for_type(row["story_type"]) if row["story_type"] else None,
                ))

        elif request.search_type == "vector":
            # Vector-only search
            if type_filter:
                cur.execute("""
                    SELECT
                        s.id::text, s.title, s.story_type, s.location,
                        e.podcast_name, e.air_date,
                        1 - (s.embedding <=> %s::vector) as similarity,
                        substring(s.content, 1, 200) as snippet,
                        s.umap_x, s.umap_y
                    FROM stories s
                    LEFT JOIN episodes e ON s.episode_id = e.id
                    WHERE s.embedding IS NOT NULL AND s.story_type = ANY(%s)
                    ORDER BY s.embedding <=> %s::vector
                    LIMIT %s
                """, (query_embedding, type_filter, query_embedding, request.limit))
            else:
                cur.execute("""
                    SELECT
                        s.id::text, s.title, s.story_type, s.location,
                        e.podcast_name, e.air_date,
                        1 - (s.embedding <=> %s::vector) as similarity,
                        substring(s.content, 1, 200) as snippet,
                        s.umap_x, s.umap_y
                    FROM stories s
                    LEFT JOIN episodes e ON s.episode_id = e.id
                    WHERE s.embedding IS NOT NULL
                    ORDER BY s.embedding <=> %s::vector
                    LIMIT %s
                """, (query_embedding, query_embedding, request.limit))

            for row in cur.fetchall():
                geo = geocode_location(row["location"]) if row["location"] else None
                results.append(SearchResult(
                    id=row["id"],
                    title=row["title"],
                    story_type=row["story_type"],
                    location=row["location"],
                    podcast_name=row["podcast_name"],
                    air_date=row["air_date"],
                    score=row["similarity"],
                    vector_score=row["similarity"],
                    snippet=row["snippet"],
                    umap_x=row["umap_x"],
                    umap_y=row["umap_y"],
                    lat=geo.lat if geo else None,
                    lng=geo.lng if geo else None,
                    frameworks=get_frameworks_for_type(row["story_type"]) if row["story_type"] else None,
                ))

        else:
            # Hybrid search - combine text and vector results
            text_results = {}
            vector_results = {}

            # Text search
            type_clause = "AND s.story_type = ANY(%s)" if type_filter else ""
            text_params = [request.query, request.query]
            if type_filter:
                text_params.append(type_filter)
            text_params.append(request.limit * 2)

            cur.execute(f"""
                SELECT
                    s.id::text, s.title, s.story_type, s.location,
                    e.podcast_name, e.air_date,
                    ts_rank(s.search_vector, plainto_tsquery('english', %s)) as rank,
                    substring(s.content, 1, 200) as snippet,
                    s.umap_x, s.umap_y
                FROM stories s
                LEFT JOIN episodes e ON s.episode_id = e.id
                WHERE s.search_vector @@ plainto_tsquery('english', %s)
                {type_clause}
                ORDER BY rank DESC
                LIMIT %s
            """, text_params)

            for row in cur.fetchall():
                text_results[row["id"]] = dict(row)

            # Vector search
            vec_params = [query_embedding]
            if type_filter:
                vec_params.append(type_filter)
            vec_params.extend([query_embedding, request.limit * 2])

            cur.execute(f"""
                SELECT
                    s.id::text, s.title, s.story_type, s.location,
                    e.podcast_name, e.air_date,
                    1 - (s.embedding <=> %s::vector) as similarity,
                    substring(s.content, 1, 200) as snippet,
                    s.umap_x, s.umap_y
                FROM stories s
                LEFT JOIN episodes e ON s.episode_id = e.id
                WHERE s.embedding IS NOT NULL
                {type_clause}
                ORDER BY s.embedding <=> %s::vector
                LIMIT %s
            """, vec_params)

            for row in cur.fetchall():
                vector_results[row["id"]] = dict(row)

            # Normalize and combine scores
            max_text = max((r.get("rank", 0) for r in text_results.values()), default=1) or 1
            max_vec = max((r.get("similarity", 0) for r in vector_results.values()), default=1) or 1

            all_ids = set(text_results.keys()) | set(vector_results.keys())
            combined = []

            for id_ in all_ids:
                text_score = text_results.get(id_, {}).get("rank", 0) / max_text
                vec_score = vector_results.get(id_, {}).get("similarity", 0) / max_vec
                hybrid_score = request.alpha * vec_score + (1 - request.alpha) * text_score

                row = text_results.get(id_) or vector_results.get(id_)
                geo = geocode_location(row["location"]) if row.get("location") else None

                combined.append(SearchResult(
                    id=row["id"],
                    title=row["title"],
                    story_type=row["story_type"],
                    location=row["location"],
                    podcast_name=row["podcast_name"],
                    air_date=row["air_date"],
                    score=hybrid_score,
                    text_score=text_score,
                    vector_score=vec_score,
                    snippet=row.get("snippet"),
                    umap_x=row.get("umap_x"),
                    umap_y=row.get("umap_y"),
                    lat=geo.lat if geo else None,
                    lng=geo.lng if geo else None,
                    frameworks=get_frameworks_for_type(row["story_type"]) if row.get("story_type") else None,
                ))

            combined.sort(key=lambda x: x.score or 0, reverse=True)
            results = combined[:request.limit]

    return results


@app.get("/api/map/stories", response_model=list[MapStory])
async def get_map_stories(
    story_type: Optional[str] = None,
    framework: Optional[str] = None,
    framework_category: Optional[str] = None,
):
    """Get all stories with geocoded locations for map display."""
    type_filter = []
    if framework and framework in FRAMEWORK_CATEGORIES:
        fw = FRAMEWORK_CATEGORIES[framework]
        if framework_category and framework_category in fw["categories"]:
            type_filter = fw["categories"][framework_category]
        else:
            for types in fw["categories"].values():
                type_filter.extend(types)
            type_filter = list(set(type_filter))
    elif story_type:
        type_filter = [story_type]

    with get_db_cursor() as cur:
        if type_filter:
            cur.execute("""
                SELECT id::text, title, story_type, location
                FROM stories
                WHERE location IS NOT NULL AND location != '' AND location != 'Unknown'
                  AND story_type = ANY(%s)
            """, (type_filter,))
        else:
            cur.execute("""
                SELECT id::text, title, story_type, location
                FROM stories
                WHERE location IS NOT NULL AND location != '' AND location != 'Unknown'
            """)

        rows = cur.fetchall()

    stories = []
    for row in rows:
        geo = geocode_location(row["location"])
        if geo:
            stories.append(MapStory(
                id=row["id"],
                title=row["title"],
                story_type=row["story_type"],
                lat=geo.lat,
                lng=geo.lng,
                location=row["location"],
            ))

    return stories


@app.get("/api/vector-space/points", response_model=list[VectorSpacePoint])
async def get_vector_space_points(
    story_type: Optional[str] = None,
    framework: Optional[str] = None,
    framework_category: Optional[str] = None,
):
    """Get all stories with UMAP coordinates for 3D vector space visualization."""
    type_filter = []
    if framework and framework in FRAMEWORK_CATEGORIES:
        fw = FRAMEWORK_CATEGORIES[framework]
        if framework_category and framework_category in fw["categories"]:
            type_filter = fw["categories"][framework_category]
        else:
            for types in fw["categories"].values():
                type_filter.extend(types)
            type_filter = list(set(type_filter))
    elif story_type:
        type_filter = [story_type]

    # Color mapping for story types
    type_colors = {
        "ghost": "#9b59b6",
        "shadow_person": "#2c3e50",
        "cryptid": "#27ae60",
        "ufo": "#3498db",
        "alien_encounter": "#1abc9c",
        "haunting": "#8e44ad",
        "poltergeist": "#e74c3c",
        "precognition": "#f39c12",
        "nde": "#e67e22",
        "obe": "#16a085",
        "time_slip": "#2980b9",
        "doppelganger": "#c0392b",
        "sleep_paralysis": "#7f8c8d",
        "possession": "#d35400",
        "other": "#95a5a6",
    }

    with get_db_cursor() as cur:
        if type_filter:
            cur.execute("""
                SELECT id::text, title, story_type, umap_x, umap_y
                FROM stories
                WHERE umap_x IS NOT NULL AND umap_y IS NOT NULL
                  AND story_type = ANY(%s)
            """, (type_filter,))
        else:
            cur.execute("""
                SELECT id::text, title, story_type, umap_x, umap_y
                FROM stories
                WHERE umap_x IS NOT NULL AND umap_y IS NOT NULL
            """)

        rows = cur.fetchall()

    points = []
    for row in rows:
        color = type_colors.get(row["story_type"], "#95a5a6")
        points.append(VectorSpacePoint(
            id=row["id"],
            title=row["title"],
            story_type=row["story_type"],
            x=row["umap_x"],
            y=row["umap_y"],
            z=0.0,  # 2D UMAP for now
            color=color,
        ))

    return points


@app.get("/api/frameworks")
async def get_frameworks():
    """Get all framework definitions."""
    return FRAMEWORK_CATEGORIES


@app.get("/api/story-types")
async def get_story_types():
    """Get all story types with counts."""
    with get_db_cursor() as cur:
        cur.execute("""
            SELECT story_type, COUNT(*) as count
            FROM stories
            WHERE story_type IS NOT NULL
            GROUP BY story_type
            ORDER BY count DESC
        """)
        rows = cur.fetchall()

    return [{"type": row["story_type"], "count": row["count"]} for row in rows]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
