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
    searchQuery
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
    <div class="flex items-center justify-between px-4 py-3">
      <div class="flex items-center gap-4">
        <h1 class="text-xl font-bold text-purple-400">
          Paranormal Tracker
        </h1>
        {#if $stats}
          <span class="text-sm text-gray-500">
            {$stats.total_stories} stories
          </span>
        {/if}
      </div>

      <!-- View Mode Tabs -->
      <div class="flex items-center gap-1 bg-[#0f0f1a] rounded-lg p-1">
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
      <div class="flex items-center gap-4">
        <form
          class="relative"
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
            class="text-sm text-gray-400 hover:text-white"
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
