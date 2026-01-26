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
    formatStoryType
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
</script>

<aside class="w-64 bg-[#1a1a2e] border-r border-gray-800 h-[calc(100vh-4rem)] overflow-y-auto">
  <div class="p-4">
    <!-- Story count -->
    <div class="mb-6">
      <div class="text-2xl font-bold text-white">{storyCount}</div>
      <div class="text-sm text-gray-500">stories displayed</div>
    </div>

    <!-- Frameworks -->
    <div class="mb-6">
      <h3 class="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">
        Frameworks
      </h3>
      <div class="space-y-1">
        <button
          class="w-full text-left px-3 py-2 rounded-lg text-sm transition-colors"
          class:bg-purple-600={!$selectedFramework}
          class:text-white={!$selectedFramework}
          class:text-gray-300={$selectedFramework}
          class:hover:bg-gray-800={$selectedFramework}
          onclick={() => selectFramework(null)}
        >
          All Stories
        </button>
        {#each Object.entries($frameworks) as [key, fw]}
          <button
            class="w-full text-left px-3 py-2 rounded-lg text-sm transition-colors"
            class:bg-purple-600={$selectedFramework === key}
            class:text-white={$selectedFramework === key}
            class:text-gray-300={$selectedFramework !== key}
            class:hover:bg-gray-800={$selectedFramework !== key}
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
        <h3 class="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">
          Categories
        </h3>
        <div class="space-y-1">
          <button
            class="w-full text-left px-3 py-2 rounded-lg text-sm transition-colors {!$selectedFrameworkCategory ? 'bg-purple-500 bg-opacity-50 text-white' : 'text-gray-300 hover:bg-gray-800'}"
            onclick={() => selectCategory(null)}
          >
            All in {$frameworks[$selectedFramework]?.name}
          </button>
          {#each $frameworkCategories as category}
            <button
              class="w-full text-left px-3 py-2 rounded-lg text-sm transition-colors capitalize {$selectedFrameworkCategory === category ? 'bg-purple-500 bg-opacity-50 text-white' : 'text-gray-300 hover:bg-gray-800'}"
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
      <h3 class="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">
        Story Types
      </h3>
      <div class="space-y-1">
        {#if $selectedFramework}
          {#each $filteredStoryTypes as type}
            <button
              class="w-full text-left px-3 py-2 rounded-lg text-sm transition-colors flex items-center gap-2"
              class:bg-gray-700={$selectedStoryType === type}
              class:text-white={$selectedStoryType === type}
              class:text-gray-300={$selectedStoryType !== type}
              class:hover:bg-gray-800={$selectedStoryType !== type}
              onclick={() => selectType($selectedStoryType === type ? null : type)}
            >
              <span
                class="w-3 h-3 rounded-full flex-shrink-0"
                style="background-color: {getStoryTypeColor(type)}"
              ></span>
              {formatStoryType(type)}
            </button>
          {/each}
        {:else}
          {#each $storyTypes as { type, count }}
            <button
              class="w-full text-left px-3 py-2 rounded-lg text-sm transition-colors flex items-center justify-between"
              class:bg-gray-700={$selectedStoryType === type}
              class:text-white={$selectedStoryType === type}
              class:text-gray-300={$selectedStoryType !== type}
              class:hover:bg-gray-800={$selectedStoryType !== type}
              onclick={() => selectType($selectedStoryType === type ? null : type)}
            >
              <div class="flex items-center gap-2">
                <span
                  class="w-3 h-3 rounded-full flex-shrink-0"
                  style="background-color: {getStoryTypeColor(type)}"
                ></span>
                {formatStoryType(type)}
              </div>
              <span class="text-gray-500 text-xs">{count}</span>
            </button>
          {/each}
        {/if}
      </div>
    </div>
  </div>
</aside>
