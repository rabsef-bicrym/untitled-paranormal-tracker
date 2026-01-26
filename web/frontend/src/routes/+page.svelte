<script lang="ts">
  import { onMount } from 'svelte';
  import { api, type MapStory, type VectorPoint, type Story, type SearchResult } from '$lib/api';
  import {
    viewMode,
    selectedFramework,
    selectedFrameworkCategory,
    selectedStoryType,
    searchQuery,
    sidebarOpen,
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

<div class="flex h-[calc(100vh-4rem)] md:h-[calc(100vh-4rem)]">
  <!-- Mobile overlay backdrop -->
  {#if $sidebarOpen}
    <button
      class="md:hidden fixed inset-0 bg-black/50 z-40"
      onclick={() => sidebarOpen.set(false)}
      aria-label="Close filters"
    ></button>
  {/if}

  <!-- Sidebar - slide-out on mobile, fixed on desktop -->
  <div
    class="fixed md:relative top-16 md:top-0 left-0 bottom-0 md:bottom-auto z-50 md:z-0
           w-64 transform transition-transform duration-300 ease-in-out
           {$sidebarOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}"
  >
    <FilterSidebar storyCount={getDisplayCount()} />
  </div>

  <!-- Main content area -->
  <div class="flex-1 relative pb-14 md:pb-0">
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
    <div class="absolute right-0 top-16 bottom-14 md:bottom-0 w-80 bg-[#1a1a2e]/95 border-l border-gray-800 z-10">
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

<!-- Bottom Navigation (mobile only) -->
<nav class="md:hidden fixed bottom-0 left-0 right-0 z-30 bg-[#1a1a2e] border-t border-gray-800" style="height: 56px;">
  <div class="flex items-center justify-around h-full">
    <button
      class="flex flex-col items-center justify-center gap-1 px-4 py-2 flex-1 transition-colors"
      class:text-purple-400={$viewMode === 'map'}
      class:text-gray-400={$viewMode !== 'map'}
      onclick={() => viewMode.set('map')}
    >
      <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
      </svg>
      <span class="text-xs">Map</span>
    </button>

    <button
      class="flex flex-col items-center justify-center gap-1 px-4 py-2 flex-1 transition-colors"
      class:text-purple-400={$viewMode === 'vector'}
      class:text-gray-400={$viewMode !== 'vector'}
      onclick={() => viewMode.set('vector')}
    >
      <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01" />
      </svg>
      <span class="text-xs">Vector</span>
    </button>

    <button
      class="flex flex-col items-center justify-center gap-1 px-4 py-2 flex-1 transition-colors"
      class:text-purple-400={$viewMode === 'list'}
      class:text-gray-400={$viewMode !== 'list'}
      onclick={() => viewMode.set('list')}
    >
      <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 10h16M4 14h16M4 18h16" />
      </svg>
      <span class="text-xs">List</span>
    </button>
  </div>
</nav>

<!-- Story detail modal -->
{#if selectedStoryId}
  <StoryDetail storyId={selectedStoryId} onClose={closeDetail} />
{/if}
