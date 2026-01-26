/**
 * API client for the Paranormal Tracker backend
 */

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export interface Story {
  id: string;
  title: string;
  story_type?: string;
  location?: string;
  content?: string;
  summary?: string;
  podcast_name?: string;
  air_date?: string;
  umap_x?: number;
  umap_y?: number;
  lat?: number;
  lng?: number;
  frameworks?: Record<string, string[]>;
}

export interface StoryDetail extends Story {
  start_time_seconds?: number;
  end_time_seconds?: number;
  time_period?: string;
  is_first_person?: boolean;
  created_at?: string;
}

export interface SearchResult extends Story {
  score?: number;
  text_score?: number;
  vector_score?: number;
  snippet?: string;
}

export interface MapStory {
  id: string;
  title: string;
  story_type?: string;
  lat: number;
  lng: number;
  location: string;
}

export interface VectorPoint {
  id: string;
  title: string;
  story_type?: string;
  x: number;
  y: number;
  z: number;
  color?: string;
}

export interface StoryType {
  type: string;
  count: number;
}

export interface Stats {
  total_stories: number;
  stories_with_location: number;
  stories_with_embedding: number;
  stories_with_umap: number;
  story_types: Record<string, number>;
  frameworks: Record<string, Record<string, number>>;
}

export interface Framework {
  name: string;
  description: string;
  categories: Record<string, string[]>;
}

export type Frameworks = Record<string, Framework>;

async function fetchJson<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`API error: ${response.status} - ${error}`);
  }

  return response.json();
}

export const api = {
  async getStats(): Promise<Stats> {
    return fetchJson('/api/stats');
  },

  async getStories(params?: {
    limit?: number;
    offset?: number;
    story_type?: string;
    framework?: string;
    framework_category?: string;
  }): Promise<Story[]> {
    const searchParams = new URLSearchParams();
    if (params?.limit) searchParams.set('limit', params.limit.toString());
    if (params?.offset) searchParams.set('offset', params.offset.toString());
    if (params?.story_type) searchParams.set('story_type', params.story_type);
    if (params?.framework) searchParams.set('framework', params.framework);
    if (params?.framework_category) searchParams.set('framework_category', params.framework_category);

    const query = searchParams.toString();
    return fetchJson(`/api/stories${query ? `?${query}` : ''}`);
  },

  async getStory(id: string): Promise<StoryDetail> {
    return fetchJson(`/api/stories/${id}`);
  },

  async search(params: {
    query: string;
    limit?: number;
    search_type?: 'hybrid' | 'text' | 'vector';
    alpha?: number;
    story_types?: string[];
    framework?: string;
    framework_category?: string;
  }): Promise<SearchResult[]> {
    return fetchJson('/api/search', {
      method: 'POST',
      body: JSON.stringify({
        query: params.query,
        limit: params.limit || 20,
        search_type: params.search_type || 'hybrid',
        alpha: params.alpha || 0.7,
        story_types: params.story_types,
        framework: params.framework,
        framework_category: params.framework_category,
      }),
    });
  },

  async getMapStories(params?: {
    story_type?: string;
    framework?: string;
    framework_category?: string;
  }): Promise<MapStory[]> {
    const searchParams = new URLSearchParams();
    if (params?.story_type) searchParams.set('story_type', params.story_type);
    if (params?.framework) searchParams.set('framework', params.framework);
    if (params?.framework_category) searchParams.set('framework_category', params.framework_category);

    const query = searchParams.toString();
    return fetchJson(`/api/map/stories${query ? `?${query}` : ''}`);
  },

  async getVectorPoints(params?: {
    story_type?: string;
    framework?: string;
    framework_category?: string;
  }): Promise<VectorPoint[]> {
    const searchParams = new URLSearchParams();
    if (params?.story_type) searchParams.set('story_type', params.story_type);
    if (params?.framework) searchParams.set('framework', params.framework);
    if (params?.framework_category) searchParams.set('framework_category', params.framework_category);

    const query = searchParams.toString();
    return fetchJson(`/api/vector-space/points${query ? `?${query}` : ''}`);
  },

  async getFrameworks(): Promise<Frameworks> {
    return fetchJson('/api/frameworks');
  },

  async getStoryTypes(): Promise<StoryType[]> {
    return fetchJson('/api/story-types');
  },
};
