<script lang="ts">
  import { viewMode } from '$lib/stores';

  function setView(mode: 'map' | 'vector' | 'list') {
    viewMode.set(mode);
  }
</script>

<nav class="fixed bottom-0 left-0 right-0 z-40 lg:hidden bg-gradient-to-t from-slate-900 to-slate-900/95 border-t border-purple-500/20 backdrop-blur-sm pb-[env(safe-area-inset-bottom,0px)]">
  <div class="flex items-stretch justify-around">
    <!-- Map Tab -->
    <button
      onclick={() => setView('map')}
      class="flex-1 flex flex-col items-center justify-center min-h-[56px] py-2 transition-all relative {$viewMode === 'map' ? 'text-purple-400' : 'text-slate-400'}"
      aria-label="Map view"
      aria-current={$viewMode === 'map' ? 'page' : undefined}
    >
      {#if $viewMode === 'map'}
        <div class="absolute top-0 left-1/2 -translate-x-1/2 w-12 h-0.5 bg-gradient-to-r from-transparent via-purple-400 to-transparent rounded-full"></div>
      {/if}
      <svg class="w-6 h-6 mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
      </svg>
      <span class="text-xs font-medium">Map</span>
    </button>

    <!-- Vector Tab -->
    <button
      onclick={() => setView('vector')}
      class="flex-1 flex flex-col items-center justify-center min-h-[56px] py-2 transition-all relative {$viewMode === 'vector' ? 'text-purple-400' : 'text-slate-400'}"
      aria-label="Vector view"
      aria-current={$viewMode === 'vector' ? 'page' : undefined}
    >
      {#if $viewMode === 'vector'}
        <div class="absolute top-0 left-1/2 -translate-x-1/2 w-12 h-0.5 bg-gradient-to-r from-transparent via-purple-400 to-transparent rounded-full"></div>
      {/if}
      <svg class="w-6 h-6 mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" />
      </svg>
      <span class="text-xs font-medium">Vector</span>
    </button>

    <!-- List Tab -->
    <button
      onclick={() => setView('list')}
      class="flex-1 flex flex-col items-center justify-center min-h-[56px] py-2 transition-all relative {$viewMode === 'list' ? 'text-purple-400' : 'text-slate-400'}"
      aria-label="List view"
      aria-current={$viewMode === 'list' ? 'page' : undefined}
    >
      {#if $viewMode === 'list'}
        <div class="absolute top-0 left-1/2 -translate-x-1/2 w-12 h-0.5 bg-gradient-to-r from-transparent via-purple-400 to-transparent rounded-full"></div>
      {/if}
      <svg class="w-6 h-6 mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 10h16M4 14h16M4 18h16" />
      </svg>
      <span class="text-xs font-medium">List</span>
    </button>
  </div>
</nav>
