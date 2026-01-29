<script lang="ts">
  import { onMount } from 'svelte';
  import { browser } from '$app/environment';
  import { api, type MapStory, type VectorPoint, type Story, type SearchResult } from '$lib/api';
  import {
    viewMode,
    selectedFramework,
    selectedFrameworkCategory,
    selectedStoryType,
    searchQuery,
    frameworks,
    storyTypes,
    sidebarOpen,
  } from '$lib/stores';
  import FilterSidebar from '$lib/components/FilterSidebar.svelte';
  import StoryList from '$lib/components/StoryList.svelte';
  import StoryDetail from '$lib/components/StoryDetail.svelte';
  import { gesture } from '$lib/utils/gestures';
  import * as haptics from '$lib/utils/haptics';

  // Lazy load Three.js visualizations
  let RetroMapComponent: any = null;
  let VectorSpaceComponent: any = null;

  async function loadRetroMap() {
    if (!RetroMapComponent) {
      const module = await import('$lib/components/RetroMap.svelte');
      RetroMapComponent = module.default;
    }
    return RetroMapComponent;
  }

  async function loadVectorSpace() {
    if (!VectorSpaceComponent) {
      const module = await import('$lib/components/VectorSpace.svelte');
      VectorSpaceComponent = module.default;
    }
    return VectorSpaceComponent;
  }

  // Preload on idle (after initial load)
  if (browser) {
    if ('requestIdleCallback' in window) {
      requestIdleCallback(() => {
        loadRetroMap();
        loadVectorSpace();
      });
    } else {
      // Fallback for browsers without requestIdleCallback
      setTimeout(() => {
        loadRetroMap();
        loadVectorSpace();
      }, 1000);
    }
  }

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
  onMount(async () => {
    // Load frameworks and story types first
    try {
      const [fwData, typesData] = await Promise.all([
        api.getFrameworks(),
        api.getStoryTypes(),
      ]);
      frameworks.set(fwData);
      storyTypes.set(typesData);
    } catch (err) {
      console.error('Failed to load metadata:', err);
    }

    // Then load story data
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

  // Swipe gesture handlers (mobile only)
  function handleSwipeRight() {
    // Open sidebar on mobile
    if (window.innerWidth < 1024) {
      sidebarOpen.set(true);
      haptics.light();
    }
  }

  function handleSwipeLeft() {
    // Close sidebar or search panel
    if (window.innerWidth < 1024) {
      if ($sidebarOpen) {
        sidebarOpen.set(false);
        haptics.light();
      } else if ($searchQuery.trim()) {
        searchQuery.set('');
        haptics.light();
      }
    }
  }

  function handleSwipeUp() {
    // Cycle view mode forward: map → vector → list → map
    if (window.innerWidth < 1024) {
      const modes: Array<'map' | 'vector' | 'list'> = ['map', 'vector', 'list'];
      const currentIndex = modes.indexOf($viewMode);
      const nextIndex = (currentIndex + 1) % modes.length;
      viewMode.set(modes[nextIndex]);
      haptics.medium();
    }
  }
</script>

<div class="flex flex-col lg:flex-row h-full">
  <!-- Sidebar (drawer on mobile, fixed on desktop) -->
  <FilterSidebar storyCount={getDisplayCount()} />

  <!-- Main content area with gesture support -->
  <div
    class="flex-1 relative overflow-hidden"
    use:gesture={{
      onSwipeRight: handleSwipeRight,
      onSwipeLeft: handleSwipeLeft,
      onSwipeUp: handleSwipeUp,
    }}
  >
    {#if $viewMode === 'map'}
      {#await loadRetroMap()}
        <div class="absolute inset-0 flex items-center justify-center">
          <div class="text-white">Loading map...</div>
        </div>
      {:then RetroMap}
        <RetroMap stories={mapStories} onStoryClick={handleStoryClick} />
      {/await}
    {:else if $viewMode === 'vector'}
      {#await loadVectorSpace()}
        <div class="absolute inset-0 flex items-center justify-center">
          <div class="text-white">Loading vector space...</div>
        </div>
      {:then VectorSpace}
        <VectorSpace points={vectorPoints} onPointClick={handleStoryClick} />
      {/await}
    {:else if $viewMode === 'list'}
      <StoryList
        stories={$searchQuery.trim() ? searchResults : listStories}
        onStoryClick={handleStoryClick}
        {loading}
      />
    {/if}

    <!-- Loading overlay -->
    {#if loading && $viewMode !== 'list'}
      <div class="absolute inset-0 bg-black/30 flex items-center justify-center pointer-events-none">
        <div class="text-white">Loading...</div>
      </div>
    {/if}
  </div>

  <!-- Search results panel (responsive positioning) -->
  {#if $searchQuery.trim() && $viewMode !== 'list' && searchResults.length > 0}
    <div class="
      fixed lg:absolute
      bottom-0 lg:bottom-auto lg:right-0 lg:top-0
      left-0 right-0 lg:left-auto
      h-[80vh] lg:h-full
      w-full lg:w-80 max-w-full lg:max-w-[480px]
      bg-[#1a1a2e]/95 backdrop-blur
      border-t lg:border-t-0 lg:border-l border-gray-800
      z-30
      overflow-y-auto
      rounded-t-2xl lg:rounded-none
    ">
      <!-- Drag handle (mobile only) -->
      <div class="lg:hidden flex justify-center pt-2 pb-1">
        <div class="w-12 h-1 bg-gray-600 rounded-full"></div>
      </div>

      <div class="p-3 border-b border-gray-800 sticky top-0 bg-[#1a1a2e]">
        <h3 class="text-sm font-medium text-white">
          Search Results ({searchResults.length})
        </h3>
      </div>
      <div class="divide-y divide-gray-800">
        {#each searchResults as result}
          <button
            onclick={() => handleStoryClick(result)}
            class="w-full text-left p-3 hover:bg-white/5 transition-colors"
          >
            <div class="text-sm font-medium text-white mb-1">{result.title}</div>
            {#if result.snippet}
              <div class="text-xs text-gray-400 line-clamp-2">{result.snippet}</div>
            {/if}
            {#if result.score}
              <div class="text-xs text-cyan-400 mt-1">
                Score: {(result.score * 100).toFixed(0)}%
              </div>
            {/if}
          </button>
        {/each}
      </div>
    </div>
  {/if}
</div>

<!-- Story detail modal -->
{#if selectedStoryId}
  <StoryDetail storyId={selectedStoryId} onClose={closeDetail} />
{/if}
