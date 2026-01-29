<script lang="ts">
  import {
    frameworks,
    storyTypes,
    selectedFramework,
    selectedFrameworkCategory,
    selectedStoryType,
    frameworkCategories,
    filteredStoryTypes,
    getStoryTypeColor,
    formatStoryType,
    sidebarOpen,
  } from '$lib/stores';

  interface Props {
    storyCount?: number;
  }

  let { storyCount = 0 }: Props = $props();

  function selectFramework(fw: string | null) {
    selectedFramework.set(fw);
    selectedFrameworkCategory.set(null);
    selectedStoryType.set(null);
  }

  function selectCategory(cat: string | null) {
    selectedFrameworkCategory.set(cat);
    selectedStoryType.set(null);
  }

  function selectType(type: string | null) {
    selectedStoryType.set(type);
  }

  function closeSidebar() {
    sidebarOpen.set(false);
  }

  function handleBackdropClick() {
    closeSidebar();
  }
</script>

<!-- Backdrop overlay (mobile only) -->
{#if $sidebarOpen}
  <button
    onclick={handleBackdropClick}
    class="lg:hidden fixed inset-0 bg-black/60 backdrop-blur-sm z-40"
    aria-label="Close sidebar"
  ></button>
{/if}

<!-- Sidebar -->
<aside
  class="
    fixed lg:static top-0 bottom-0 left-0 z-50
    w-[85vw] max-w-[384px] lg:w-64
    bg-slate-900 border-r border-slate-800
    overflow-y-auto
    transition-transform duration-300
    {$sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
  "
>
  <!-- Mobile close button -->
  <div class="lg:hidden sticky top-0 bg-slate-900 border-b border-slate-800 p-4 flex items-center justify-between z-10">
    <h2 class="text-lg font-bold text-white font-['Orbitron']">Filters</h2>
    <button
      onclick={closeSidebar}
      class="p-2 hover:bg-white/5 rounded transition-colors"
      aria-label="Close filters"
    >
      <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
      </svg>
    </button>
  </div>

  <div class="p-4 space-y-6">
  <!-- Story count -->
  <div>
    <div class="text-3xl font-bold text-white tabular-nums">{storyCount}</div>
    <div class="text-sm text-slate-500">stories displayed</div>
  </div>

  <!-- Frameworks -->
  <div>
    <h3 class="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
      Frameworks
    </h3>
    <div class="space-y-0.5">
      <button
        class="w-full text-left px-3 py-2 rounded-lg text-sm transition-colors {!$selectedFramework ? 'bg-violet-600 text-white' : 'text-slate-300 hover:bg-slate-800'}"
        onclick={() => selectFramework(null)}
      >
        All Stories
      </button>
      {#each Object.entries($frameworks) as [key, fw]}
        <button
          class="w-full text-left px-3 py-2 rounded-lg text-sm transition-colors {$selectedFramework === key ? 'bg-violet-600 text-white' : 'text-slate-300 hover:bg-slate-800'}"
          onclick={() => selectFramework(key)}
        >
          {fw.name}
        </button>
      {/each}
    </div>
  </div>

  <!-- Framework Categories -->
  {#if $selectedFramework && $frameworkCategories.length > 0}
    <div>
      <h3 class="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
        Categories
      </h3>
      <div class="space-y-0.5">
        <button
          class="w-full text-left px-3 py-2 rounded-lg text-sm transition-colors {!$selectedFrameworkCategory ? 'bg-violet-500/50 text-white' : 'text-slate-300 hover:bg-slate-800'}"
          onclick={() => selectCategory(null)}
        >
          All in {$frameworks[$selectedFramework]?.name}
        </button>
        {#each $frameworkCategories as category}
          <button
            class="w-full text-left px-3 py-2 rounded-lg text-sm transition-colors capitalize {$selectedFrameworkCategory === category ? 'bg-violet-500/50 text-white' : 'text-slate-300 hover:bg-slate-800'}"
            onclick={() => selectCategory(category)}
          >
            {category.replace(/_/g, ' ')}
          </button>
        {/each}
      </div>
    </div>
  {/if}

  <!-- Story Types -->
  <div>
    <h3 class="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
      Story Types
    </h3>
    <div class="space-y-0.5">
      {#if $selectedFramework}
        {#each $filteredStoryTypes as type}
          <button
            class="w-full text-left px-3 py-2 rounded-lg text-sm transition-colors flex items-center gap-2 {$selectedStoryType === type ? 'bg-slate-700 text-white' : 'text-slate-300 hover:bg-slate-800'}"
            onclick={() => selectType($selectedStoryType === type ? null : type)}
          >
            <span
              class="w-2.5 h-2.5 rounded-full shrink-0"
              style="background-color: {getStoryTypeColor(type)}"
            ></span>
            {formatStoryType(type)}
          </button>
        {/each}
      {:else}
        {#each $storyTypes as { type, count }}
          <button
            class="w-full text-left px-3 py-2 rounded-lg text-sm transition-colors flex items-center justify-between {$selectedStoryType === type ? 'bg-slate-700 text-white' : 'text-slate-300 hover:bg-slate-800'}"
            onclick={() => selectType($selectedStoryType === type ? null : type)}
          >
            <div class="flex items-center gap-2">
              <span
                class="w-2.5 h-2.5 rounded-full shrink-0"
                style="background-color: {getStoryTypeColor(type)}"
              ></span>
              {formatStoryType(type)}
            </div>
            <span class="text-slate-500 text-xs tabular-nums">{count}</span>
          </button>
        {/each}
      {/if}
    </div>
  </div>
  </div>
</aside>
