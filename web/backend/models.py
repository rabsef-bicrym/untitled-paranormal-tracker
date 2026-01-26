"""Pydantic models for API requests and responses."""

from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field


# Cardiff Anomalous Perceptions Scale (CAPS) categories
# Sleep Paralysis framework categories
# Hypnagogic/Hypnopompic framework categories
FRAMEWORK_CATEGORIES = {
    "caps": {
        "name": "Cardiff Anomalous Perceptions Scale",
        "description": "Psychological framework for evaluating anomalous perceptions",
        "categories": {
            "temporal_lobe": ["precognition", "time_slip", "deja_vu"],
            "clinical_perceptual": ["shadow_person", "ghost", "doppelganger"],
            "chemosensory": ["phantom_smell", "other"],
            "sleep_related": ["sleep_paralysis", "obe", "nde"],
            "external_agent": ["alien_encounter", "possession", "haunting"],
        }
    },
    "sleep_paralysis": {
        "name": "Sleep Paralysis Framework",
        "description": "Categories based on sleep paralysis research",
        "categories": {
            "intruder": ["shadow_person", "ghost", "alien_encounter"],
            "incubus": ["sleep_paralysis", "possession"],
            "vestibular_motor": ["obe", "nde", "time_slip"],
        }
    },
    "hypnagogic": {
        "name": "Hypnagogic/Hypnopompic Framework",
        "description": "Experiences during sleep-wake transitions",
        "categories": {
            "visual": ["ghost", "shadow_person", "doppelganger", "ufo"],
            "auditory": ["ghost", "haunting"],
            "tactile": ["sleep_paralysis", "possession"],
            "proprioceptive": ["obe", "time_slip"],
        }
    }
}


# Map story types to frameworks
def get_frameworks_for_type(story_type: str) -> dict[str, list[str]]:
    """Get all framework categories that include this story type."""
    result = {}
    for framework_key, framework in FRAMEWORK_CATEGORIES.items():
        matches = []
        for category, types in framework["categories"].items():
            if story_type in types:
                matches.append(category)
        if matches:
            result[framework_key] = matches
    return result


class StoryBase(BaseModel):
    """Base story model with common fields."""
    id: str
    title: str
    story_type: Optional[str] = None
    location: Optional[str] = None
    content: Optional[str] = None
    summary: Optional[str] = None


class StoryListItem(StoryBase):
    """Story item for list views."""
    podcast_name: Optional[str] = None
    air_date: Optional[date] = None
    umap_x: Optional[float] = None
    umap_y: Optional[float] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    frameworks: Optional[dict] = None


class StoryDetail(StoryListItem):
    """Full story details."""
    start_time_seconds: Optional[float] = None
    end_time_seconds: Optional[float] = None
    time_period: Optional[str] = None
    is_first_person: Optional[bool] = True
    created_at: Optional[datetime] = None


class SearchRequest(BaseModel):
    """Search request parameters."""
    query: str
    limit: int = Field(default=20, ge=1, le=100)
    search_type: str = Field(default="hybrid", pattern="^(hybrid|text|vector)$")
    alpha: float = Field(default=0.7, ge=0.0, le=1.0)
    story_types: Optional[list[str]] = None
    framework: Optional[str] = None
    framework_category: Optional[str] = None


class SearchResult(StoryListItem):
    """Search result with relevance scores."""
    score: Optional[float] = None
    text_score: Optional[float] = None
    vector_score: Optional[float] = None
    snippet: Optional[str] = None


class GeoLocation(BaseModel):
    """Geocoded location."""
    location: str
    lat: float
    lng: float
    state: Optional[str] = None
    country: str = "USA"


class MapStory(BaseModel):
    """Story for map display."""
    id: str
    title: str
    story_type: Optional[str] = None
    lat: float
    lng: float
    location: str


class VectorSpacePoint(BaseModel):
    """Point in 3D vector space for visualization."""
    id: str
    title: str
    story_type: Optional[str] = None
    x: float  # umap_x
    y: float  # umap_y
    z: float = 0.0  # Could add 3D UMAP later
    color: Optional[str] = None


class FrameworkFilter(BaseModel):
    """Framework filtering options."""
    framework: str
    category: Optional[str] = None


class StatsResponse(BaseModel):
    """Statistics about the stories database."""
    total_stories: int
    stories_with_location: int
    stories_with_embedding: int
    stories_with_umap: int
    story_types: dict[str, int]
    frameworks: dict[str, dict[str, int]]
