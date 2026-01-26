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
    sidebarOpen
  } from '$lib/stores';

  let { children } = $props();

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
</script>

<svelte:head>
  <title>Paranormal Tracker</title>
  <meta name="description" content="Interactive map and visualization of first-person paranormal experiences" />
</svelte:head>

<div class="min-h-screen bg-[#0f0f1a] text-gray-100">
  <!-- Header -->
  <header class="fixed top-0 left-0 right-0 z-50 bg-[#1a1a2e]/95 backdrop-blur border-b border-gray-800">
    <div class="flex items-center justify-between px-4 py-3 gap-2">
      <div class="flex items-center gap-2 md:gap-4 min-w-0">
        <!-- Hamburger button (mobile only) -->
        <button
          class="md:hidden p-2.5 -ml-2.5 text-gray-400 hover:text-white active:text-purple-400"
          onclick={() => sidebarOpen.set(true)}
          aria-label="Open filters"
        >
          <svg class="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>

        <h1 class="text-lg md:text-xl font-bold text-purple-400 truncate">
          Paranormal Tracker
        </h1>
        {#if $stats}
          <span class="hidden sm:inline text-sm text-gray-500">
            {$stats.total_stories} stories
          </span>
        {/if}
      </div>

      <!-- View Mode Tabs (desktop only) -->
      <div class="hidden md:flex items-center gap-1 bg-[#0f0f1a] rounded-lg p-1">
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

      <!-- Search -->
      <div class="flex items-center gap-2 md:gap-4 min-w-0 flex-1 md:flex-initial justify-end">
        <form
          class="relative w-full md:w-auto"
          onsubmit={(e) => { e.preventDefault(); }}
        >
          <input
            type="text"
            placeholder="Search..."
            class="w-full md:w-64 px-3 md:px-4 py-2 bg-[#0f0f1a] border border-gray-700 rounded-lg text-sm focus:outline-none focus:border-purple-500"
            bind:value={$searchQuery}
          />
          {#if $searchQuery}
            <button
              type="button"
              class="absolute right-2 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300"
              onclick={() => searchQuery.set('')}
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          {/if}
        </form>

        {#if $selectedFramework || $selectedStoryType}
          <button
            class="hidden md:block text-sm text-gray-400 hover:text-white whitespace-nowrap"
            onclick={clearFilters}
          >
            Clear filters
          </button>
        {/if}
      </div>
    </div>
  </header>

  <!-- Main Content -->
  <main class="pt-16">
    {@render children()}
  </main>
</div>
