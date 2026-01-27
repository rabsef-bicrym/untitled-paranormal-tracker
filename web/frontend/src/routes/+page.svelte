<script lang="ts">
  import { onMount } from 'svelte';
  import { api, type MapStory, type VectorPoint, type Story, type SearchResult } from '$lib/api';
  import {
    viewMode,
    selectedFramework,
    selectedFrameworkCategory,
    selectedStoryType,
    searchQuery,
  } from '$lib/stores';
  import USMap from '$lib/components/USMap.svelte';
  import VectorSpace from '$lib/components/VectorSpace.svelte';
  import FilterSidebar from '$lib/components/FilterSidebar.svelte';
  import StoryList from '$lib/components/StoryList.svelte';
  import StoryDetail from '$lib/components/StoryDetail.svelte';

  let mapStories: MapStory[] = $state([]);
  let vectorPoints: VectorPoint[] = $state([]);
  let listStories: Story[] = $state([]);
  let searchResults: SearchResult[] = $state([]);
  let selectedStoryId: string | null = $state(null);
  let loading = $state(false);

  // Debounce search
  let searchTimeout: ReturnType<typeof setTimeout>;

  async function loadData() {
    loading = true;

    const params = {
      story_type: $selectedStoryType || undefined,
      framework: $selectedFramework || undefined,
      framework_category: $selectedFrameworkCategory || undefined,
    };

    try {
      if ($searchQuery.trim()) {
        // Perform search
        searchResults = await api.search({
          query: $searchQuery,
          limit: 50,
          ...params,
        });
        // Also load map/vector data for visualization
        const [map, vector] = await Promise.all([
          api.getMapStories(params),
          api.getVectorPoints(params),
        ]);
        mapStories = map;
        vectorPoints = vector;
      } else {
        // Load all data
        const [map, vector, list] = await Promise.all([
          api.getMapStories(params),
          api.getVectorPoints(params),
          api.getStories({ ...params, limit: 100 }),
        ]);
        mapStories = map;
        vectorPoints = vector;
        listStories = list;
        searchResults = [];
      }
    } catch (err) {
      console.error('Failed to load data:', err);
    } finally {
      loading = false;
    }
  }

  // Load data on mount and when filters change
  onMount(() => {
    loadData();
  });

  $effect(() => {
    // Re-load when filters change
    void $selectedFramework;
    void $selectedFrameworkCategory;
    void $selectedStoryType;
    loadData();
  });

  $effect(() => {
    // Debounced search
    clearTimeout(searchTimeout);
    if ($searchQuery.trim()) {
      searchTimeout = setTimeout(loadData, 300);
    } else {
      loadData();
    }
  });

  function handleStoryClick(story: { id: string }) {
    selectedStoryId = story.id;
  }

  function closeDetail() {
    selectedStoryId = null;
  }

  // Get display count based on current view
  function getDisplayCount(): number {
    if ($searchQuery.trim()) {
      return searchResults.length;
    }
    switch ($viewMode) {
      case 'map':
        return mapStories.length;
      case 'vector':
        return vectorPoints.length;
      case 'list':
        return listStories.length;
      default:
        return 0;
    }
  }
</script>

<div class="flex h-[calc(100vh-4rem)]">
  <!-- Sidebar -->
  <FilterSidebar storyCount={getDisplayCount()} />

  <!-- Main content area -->
  <div class="flex-1 relative">
    {#if $viewMode === 'map'}
      <USMap stories={mapStories} onStoryClick={handleStoryClick} />
    {:else if $viewMode === 'vector'}
      <VectorSpace points={vectorPoints} onPointClick={handleStoryClick} />
    {:else if $viewMode === 'list'}
      <StoryList
        stories={$searchQuery.trim() ? searchResults : listStories}
        onStoryClick={handleStoryClick}
        {loading}
      />
    {/if}

    <!-- Loading overlay -->
    {#if loading && $viewMode !== 'list'}
      <div class="absolute inset-0 bg-black/30 flex items-center justify-center">
        <div class="text-white">Loading...</div>
      </div>
    {/if}
  </div>

  <!-- Search results panel (overlay on map/vector views) -->
  {#if $searchQuery.trim() && $viewMode !== 'list' && searchResults.length > 0}
    <div class="absolute right-0 top-16 bottom-0 w-80 bg-[#1a1a2e]/95 border-l border-gray-800 z-10">
      <div class="p-3 border-b border-gray-800">
        <h3 class="text-sm font-medium text-white">
          Search Results ({searchResults.length})
        </h3>
      </div>
      <StoryList
        stories={searchResults}
        onStoryClick={handleStoryClick}
        {loading}
      />
    </div>
  {/if}
</div>

<!-- Story detail modal -->
{#if selectedStoryId}
  <StoryDetail storyId={selectedStoryId} onClose={closeDetail} />
{/if}
