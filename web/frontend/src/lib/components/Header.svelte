<script lang="ts">
  import { viewMode, searchQuery, sidebarOpen } from '$lib/stores';

  interface Props {
    storyCount?: number;
  }

  let { storyCount = 0 }: Props = $props();

  let showMobileSearch = $state(false);

  function toggleSidebar() {
    sidebarOpen.set(!$sidebarOpen);
  }

  function clearFilters() {
    searchQuery.set('');
    // Additional filter clearing will be added when filters are implemented
  }

  function toggleMobileSearch() {
    showMobileSearch = !showMobileSearch;
  }
</script>

<header class="h-14 md:h-16 bg-gradient-to-r from-slate-900 via-purple-900/30 to-slate-900 border-b border-purple-500/20 flex items-center px-4 gap-4 shrink-0 z-50">
  <!-- Hamburger menu (mobile only) -->
  <button
    onclick={toggleSidebar}
    class="lg:hidden p-2 hover:bg-white/5 rounded transition-colors"
    aria-label="Toggle menu"
  >
    <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
    </svg>
  </button>

  <!-- App title + story count -->
  <div class="flex items-center gap-3 shrink-0">
    <h1 class="text-lg md:text-xl font-bold bg-gradient-to-r from-cyan-400 to-purple-400 bg-clip-text text-transparent font-['Orbitron']">
      Paranormal Tracker
    </h1>
    <span class="px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-300 text-xs font-medium border border-purple-500/30">
      {storyCount}
    </span>
  </div>

  <!-- View mode tabs (desktop only) -->
  <div class="hidden lg:flex gap-1 mx-4">
    <button
      onclick={() => viewMode.set('map')}
      class="px-4 py-1.5 rounded text-sm font-medium transition-all {$viewMode === 'map' ? 'bg-purple-500/20 text-purple-300 border border-purple-500/50' : 'text-slate-400 hover:text-slate-200 hover:bg-white/5'}"
    >
      Map
    </button>
    <button
      onclick={() => viewMode.set('vector')}
      class="px-4 py-1.5 rounded text-sm font-medium transition-all {$viewMode === 'vector' ? 'bg-purple-500/20 text-purple-300 border border-purple-500/50' : 'text-slate-400 hover:text-slate-200 hover:bg-white/5'}"
    >
      Vector
    </button>
    <button
      onclick={() => viewMode.set('list')}
      class="px-4 py-1.5 rounded text-sm font-medium transition-all {$viewMode === 'list' ? 'bg-purple-500/20 text-purple-300 border border-purple-500/50' : 'text-slate-400 hover:text-slate-200 hover:bg-white/5'}"
    >
      List
    </button>
  </div>

  <!-- Desktop search (always visible on desktop) -->
  <div class="hidden lg:flex flex-1 max-w-md">
    <div class="relative w-full">
      <input
        type="text"
        placeholder="Search stories..."
        bind:value={$searchQuery}
        class="w-full px-4 py-2 bg-slate-800/50 border border-slate-700 rounded-lg text-sm focus:outline-none focus:border-purple-500/50 focus:bg-slate-800/80 transition-colors"
      />
      <svg class="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
      </svg>
    </div>
  </div>

  <!-- Mobile search toggle button -->
  <button
    onclick={toggleMobileSearch}
    class="lg:hidden p-2 hover:bg-white/5 rounded transition-colors {showMobileSearch ? 'text-purple-400' : ''}"
    aria-label="Search"
  >
    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
    </svg>
  </button>

  <!-- Clear filters button -->
  {#if $searchQuery.trim()}
    <button
      onclick={clearFilters}
      class="p-2 hover:bg-white/5 rounded transition-colors text-slate-400 hover:text-slate-200"
      aria-label="Clear filters"
    >
      <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
      </svg>
    </button>
  {/if}
</header>

<!-- Mobile search bar (expandable) -->
{#if showMobileSearch}
  <div class="lg:hidden bg-slate-900 border-b border-slate-800 px-4 py-3 animate-slide-down">
    <div class="relative">
      <input
        type="text"
        placeholder="Search stories..."
        bind:value={$searchQuery}
        class="w-full px-4 py-2 bg-slate-800/50 border border-slate-700 rounded-lg text-sm focus:outline-none focus:border-purple-500/50 focus:bg-slate-800/80 transition-colors"
        autofocus
      />
      <svg class="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
      </svg>
    </div>
  </div>
{/if}

<style>
  @keyframes slide-down {
    from {
      opacity: 0;
      transform: translateY(-10px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  .animate-slide-down {
    animation: slide-down 0.2s ease-out;
  }
</style>
