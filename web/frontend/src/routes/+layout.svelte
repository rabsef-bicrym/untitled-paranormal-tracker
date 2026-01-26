<script lang="ts">
  import '../app.css';
  import { onMount } from 'svelte';
  import { api } from '$lib/api';
  import {
    frameworks,
    storyTypes,
    stats,
    isLoading,
    viewMode,
    selectedFramework,
    selectedFrameworkCategory,
    selectedStoryType,
    searchQuery,
    mobileFiltersOpen
  } from '$lib/stores';

  let { children } = $props();
  let showMobileSearch = $state(false);

  onMount(async () => {
    isLoading.set(true);
    try {
      const [fw, types, st] = await Promise.all([
        api.getFrameworks(),
        api.getStoryTypes(),
        api.getStats()
      ]);
      frameworks.set(fw);
      storyTypes.set(types);
      stats.set(st);
    } catch (err) {
      console.error('Failed to load initial data:', err);
    } finally {
      isLoading.set(false);
    }
  });

  function clearFilters() {
    selectedFramework.set(null);
    selectedFrameworkCategory.set(null);
    selectedStoryType.set(null);
    searchQuery.set('');
  }

  function toggleMobileFilters() {
    mobileFiltersOpen.set(!$mobileFiltersOpen);
  }
</script>

<svelte:head>
  <title>Paranormal Tracker</title>
  <meta name="description" content="Interactive map and visualization of first-person paranormal experiences" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
</svelte:head>

<div class="min-h-screen bg-[#0f0f1a] text-gray-100">
  <!-- Header -->
  <header class="fixed top-0 left-0 right-0 z-50 bg-[#1a1a2e]/95 backdrop-blur border-b border-gray-800">
    <div class="flex items-center justify-between px-3 md:px-4 py-2.5 md:py-3">
      <!-- Left: Hamburger (mobile) + Title -->
      <div class="flex items-center gap-2 md:gap-4 flex-1 min-w-0">
        <!-- Hamburger menu for mobile -->
        <button
          class="lg:hidden p-2 -ml-2 text-gray-400 hover:text-white active:text-purple-400 transition-colors touch-manipulation"
          onclick={toggleMobileFilters}
          aria-label="Toggle filters"
        >
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>

        <h1 class="text-lg md:text-xl font-bold text-purple-400 truncate">
          Paranormal Tracker
        </h1>
        {#if $stats}
          <span class="hidden sm:inline text-xs md:text-sm text-gray-500 whitespace-nowrap">
            {$stats.total_stories} stories
          </span>
        {/if}
      </div>

      <!-- Center: View Mode Tabs (hidden on mobile) -->
      <div class="hidden lg:flex items-center gap-1 bg-[#0f0f1a] rounded-lg p-1">
        <button
          class="px-4 py-2 rounded-md text-sm font-medium transition-colors"
          class:bg-purple-600={$viewMode === 'map'}
          class:text-white={$viewMode === 'map'}
          class:text-gray-400={$viewMode !== 'map'}
          class:hover:text-gray-200={$viewMode !== 'map'}
          onclick={() => viewMode.set('map')}
        >
          US Map
        </button>
        <button
          class="px-4 py-2 rounded-md text-sm font-medium transition-colors"
          class:bg-purple-600={$viewMode === 'vector'}
          class:text-white={$viewMode === 'vector'}
          class:text-gray-400={$viewMode !== 'vector'}
          class:hover:text-gray-200={$viewMode !== 'vector'}
          onclick={() => viewMode.set('vector')}
        >
          Vector Space
        </button>
        <button
          class="px-4 py-2 rounded-md text-sm font-medium transition-colors"
          class:bg-purple-600={$viewMode === 'list'}
          class:text-white={$viewMode === 'list'}
          class:text-gray-400={$viewMode !== 'list'}
          class:hover:text-gray-200={$viewMode !== 'list'}
          onclick={() => viewMode.set('list')}
        >
          List
        </button>
      </div>

      <!-- Right: Search + Actions -->
      <div class="flex items-center gap-2 md:gap-4 flex-1 justify-end min-w-0">
        <!-- Mobile search toggle -->
        <button
          class="lg:hidden p-2 text-gray-400 hover:text-white active:text-purple-400 transition-colors touch-manipulation"
          onclick={() => showMobileSearch = !showMobileSearch}
          aria-label="Toggle search"
        >
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
        </button>

        <!-- Desktop search -->
        <form
          class="hidden lg:block relative"
          onsubmit={(e) => { e.preventDefault(); }}
        >
          <input
            type="text"
            placeholder="Search stories..."
            class="w-64 px-4 py-2 bg-[#0f0f1a] border border-gray-700 rounded-lg text-sm focus:outline-none focus:border-purple-500"
            bind:value={$searchQuery}
          />
          {#if $searchQuery}
            <button
              type="button"
              class="absolute right-2 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300"
              onclick={() => searchQuery.set('')}
            >
              &times;
            </button>
          {/if}
        </form>

        {#if $selectedFramework || $selectedStoryType}
          <button
            class="hidden md:block text-xs md:text-sm text-gray-400 hover:text-white whitespace-nowrap"
            onclick={clearFilters}
          >
            Clear filters
          </button>
        {/if}
      </div>
    </div>

    <!-- Mobile search bar (expandable) -->
    {#if showMobileSearch}
      <div class="lg:hidden px-3 pb-3 border-t border-gray-800">
        <form
          class="relative mt-3"
          onsubmit={(e) => { e.preventDefault(); }}
        >
          <input
            type="text"
            placeholder="Search stories..."
            class="w-full px-4 py-3 bg-[#0f0f1a] border border-gray-700 rounded-lg text-base focus:outline-none focus:border-purple-500"
            bind:value={$searchQuery}
            autofocus
          />
          {#if $searchQuery}
            <button
              type="button"
              class="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300 p-1 touch-manipulation"
              onclick={() => searchQuery.set('')}
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          {/if}
        </form>
      </div>
    {/if}
  </header>

  <!-- Main Content -->
  <main class="pt-14 md:pt-16 pb-16 lg:pb-0">
    {@render children()}
  </main>

  <!-- Bottom Navigation (mobile only) -->
  <nav class="lg:hidden fixed bottom-0 left-0 right-0 z-50 bg-[#1a1a2e]/95 backdrop-blur border-t border-gray-800 safe-area-inset-bottom">
    <div class="flex items-center justify-around px-2 py-2">
      <button
        class="flex flex-col items-center gap-1 px-4 py-2 rounded-lg transition-colors touch-manipulation min-w-[64px] min-h-[56px]"
        class:text-purple-400={$viewMode === 'map'}
        class:text-gray-400={$viewMode !== 'map'}
        onclick={() => viewMode.set('map')}
      >
        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
        </svg>
        <span class="text-xs font-medium">Map</span>
      </button>
      <button
        class="flex flex-col items-center gap-1 px-4 py-2 rounded-lg transition-colors touch-manipulation min-w-[64px] min-h-[56px]"
        class:text-purple-400={$viewMode === 'vector'}
        class:text-gray-400={$viewMode !== 'vector'}
        onclick={() => viewMode.set('vector')}
      >
        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01" />
        </svg>
        <span class="text-xs font-medium">Vector</span>
      </button>
      <button
        class="flex flex-col items-center gap-1 px-4 py-2 rounded-lg transition-colors touch-manipulation min-w-[64px] min-h-[56px]"
        class:text-purple-400={$viewMode === 'list'}
        class:text-gray-400={$viewMode !== 'list'}
        onclick={() => viewMode.set('list')}
      >
        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 10h16M4 14h16M4 18h16" />
        </svg>
        <span class="text-xs font-medium">List</span>
      </button>
    </div>
  </nav>
</div>

<style>
  .safe-area-inset-bottom {
    padding-bottom: env(safe-area-inset-bottom);
  }
</style>
