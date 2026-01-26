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
    mobileFiltersOpen
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

  function closeMobileFilters() {
    mobileFiltersOpen.set(false);
  }
</script>

<!-- Mobile drawer overlay -->
{#if $mobileFiltersOpen}
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div
    class="lg:hidden fixed inset-0 bg-black/50 z-40 transition-opacity"
    onclick={closeMobileFilters}
  ></div>
{/if}

<!-- Sidebar/Drawer -->
<aside
  class="
    fixed lg:static
    top-0 bottom-0 left-0
    w-[85vw] max-w-sm lg:w-64
    bg-[#1a1a2e]
    border-r border-gray-800
    z-50 lg:z-0
    transform transition-transform duration-300 ease-in-out
    lg:transform-none
    overflow-y-auto
    {$mobileFiltersOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
  "
  style="height: 100vh; top: 0; padding-top: env(safe-area-inset-top);"
>
  <!-- Mobile header -->
  <div class="lg:hidden sticky top-0 z-10 bg-[#1a1a2e] border-b border-gray-800 px-4 py-3 flex items-center justify-between">
    <h2 class="text-lg font-semibold text-white">Filters</h2>
    <button
      class="p-2 -mr-2 text-gray-400 hover:text-white active:text-purple-400 transition-colors touch-manipulation"
      onclick={closeMobileFilters}
      aria-label="Close filters"
    >
      <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
      </svg>
    </button>
  </div>

  <div class="p-4 pb-20 lg:pb-4">
    <!-- Story count -->
    <div class="mb-6">
      <div class="text-2xl md:text-3xl font-bold text-white">{storyCount}</div>
      <div class="text-sm text-gray-500">stories displayed</div>
    </div>

    <!-- Frameworks -->
    <div class="mb-6">
      <h3 class="text-xs md:text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">
        Frameworks
      </h3>
      <div class="space-y-2">
        <button
          class="w-full text-left px-4 py-3 rounded-lg text-sm md:text-base transition-colors touch-manipulation min-h-[44px] flex items-center"
          class:bg-purple-600={!$selectedFramework}
          class:text-white={!$selectedFramework}
          class:text-gray-300={$selectedFramework}
          class:hover:bg-gray-800={$selectedFramework}
          class:active:bg-gray-700={$selectedFramework}
          onclick={() => selectFramework(null)}
        >
          All Stories
        </button>
        {#each Object.entries($frameworks) as [key, fw]}
          <button
            class="w-full text-left px-4 py-3 rounded-lg text-sm md:text-base transition-colors touch-manipulation min-h-[44px] flex items-center"
            class:bg-purple-600={$selectedFramework === key}
            class:text-white={$selectedFramework === key}
            class:text-gray-300={$selectedFramework !== key}
            class:hover:bg-gray-800={$selectedFramework !== key}
            class:active:bg-gray-700={$selectedFramework !== key}
            onclick={() => selectFramework(key)}
          >
            {fw.name}
          </button>
        {/each}
      </div>
    </div>

    <!-- Framework Categories (when a framework is selected) -->
    {#if $selectedFramework && $frameworkCategories.length > 0}
      <div class="mb-6">
        <h3 class="text-xs md:text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">
          Categories
        </h3>
        <div class="space-y-2">
          <button
            class="w-full text-left px-4 py-3 rounded-lg text-sm md:text-base transition-colors touch-manipulation min-h-[44px] flex items-center {!$selectedFrameworkCategory ? 'bg-purple-500 bg-opacity-50 text-white' : 'text-gray-300 hover:bg-gray-800 active:bg-gray-700'}"
            onclick={() => selectCategory(null)}
          >
            All in {$frameworks[$selectedFramework]?.name}
          </button>
          {#each $frameworkCategories as category}
            <button
              class="w-full text-left px-4 py-3 rounded-lg text-sm md:text-base transition-colors capitalize touch-manipulation min-h-[44px] flex items-center {$selectedFrameworkCategory === category ? 'bg-purple-500 bg-opacity-50 text-white' : 'text-gray-300 hover:bg-gray-800 active:bg-gray-700'}"
              onclick={() => selectCategory(category)}
            >
              {category.replace(/_/g, ' ')}
            </button>
          {/each}
        </div>
      </div>
    {/if}

    <!-- Story Types -->
    <div class="mb-6">
      <h3 class="text-xs md:text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">
        Story Types
      </h3>
      <div class="space-y-2">
        {#if $selectedFramework}
          {#each $filteredStoryTypes as type}
            <button
              class="w-full text-left px-4 py-3 rounded-lg text-sm md:text-base transition-colors flex items-center gap-3 touch-manipulation min-h-[44px]"
              class:bg-gray-700={$selectedStoryType === type}
              class:text-white={$selectedStoryType === type}
              class:text-gray-300={$selectedStoryType !== type}
              class:hover:bg-gray-800={$selectedStoryType !== type}
              class:active:bg-gray-600={$selectedStoryType !== type}
              onclick={() => selectType($selectedStoryType === type ? null : type)}
            >
              <span
                class="w-4 h-4 rounded-full flex-shrink-0"
                style="background-color: {getStoryTypeColor(type)}"
              ></span>
              {formatStoryType(type)}
            </button>
          {/each}
        {:else}
          {#each $storyTypes as { type, count }}
            <button
              class="w-full text-left px-4 py-3 rounded-lg text-sm md:text-base transition-colors flex items-center justify-between touch-manipulation min-h-[44px]"
              class:bg-gray-700={$selectedStoryType === type}
              class:text-white={$selectedStoryType === type}
              class:text-gray-300={$selectedStoryType !== type}
              class:hover:bg-gray-800={$selectedStoryType !== type}
              class:active:bg-gray-600={$selectedStoryType !== type}
              onclick={() => selectType($selectedStoryType === type ? null : type)}
            >
              <div class="flex items-center gap-3">
                <span
                  class="w-4 h-4 rounded-full flex-shrink-0"
                  style="background-color: {getStoryTypeColor(type)}"
                ></span>
                {formatStoryType(type)}
              </div>
              <span class="text-gray-500 text-xs md:text-sm font-medium">{count}</span>
            </button>
          {/each}
        {/if}
      </div>
    </div>
  </div>
</aside>
