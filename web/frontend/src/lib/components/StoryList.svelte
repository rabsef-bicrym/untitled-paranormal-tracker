<script lang="ts">
  import { onMount } from 'svelte';
  import type { Story, SearchResult } from '$lib/api';
  import { getStoryTypeColor, formatStoryType } from '$lib/stores';

  interface Props {
    stories: (Story | SearchResult)[];
    onStoryClick?: (story: Story | SearchResult) => void;
    loading?: boolean;
  }

  let { stories, onStoryClick, loading = false }: Props = $props();

  function isSearchResult(story: Story | SearchResult): story is SearchResult {
    return 'score' in story;
  }

  // Virtual scrolling state
  const ITEM_HEIGHT = 120; // Approximate height of each story card
  const BUFFER_SIZE = 5; // Extra items to render above and below viewport

  let scrollContainer: HTMLDivElement;
  let scrollTop = $state(0);
  let containerHeight = $state(0);

  // Calculate visible range
  let visibleStart = $derived(Math.max(0, Math.floor(scrollTop / ITEM_HEIGHT) - BUFFER_SIZE));
  let visibleEnd = $derived(Math.min(
    stories.length,
    Math.ceil((scrollTop + containerHeight) / ITEM_HEIGHT) + BUFFER_SIZE
  ));
  let visibleStories = $derived(stories.slice(visibleStart, visibleEnd));

  function handleScroll(e: Event) {
    scrollTop = (e.target as HTMLDivElement).scrollTop;
  }

  onMount(() => {
    if (scrollContainer) {
      containerHeight = scrollContainer.clientHeight;
    }
  });
</script>

<div class="h-full overflow-y-auto" bind:this={scrollContainer} onscroll={handleScroll}>
  {#if loading}
    <div class="p-4 space-y-4">
      {#each Array(5) as _, i}
        <div class="bg-[#1a1a2e] border border-gray-800 rounded-lg p-4 animate-pulse">
          <div class="h-5 bg-gray-700 rounded w-3/4 mb-2"></div>
          <div class="h-4 bg-gray-700 rounded w-1/2 mb-2"></div>
          <div class="h-4 bg-gray-700 rounded w-full"></div>
        </div>
      {/each}
    </div>
  {:else if stories.length === 0}
    <div class="flex items-center justify-center h-full text-gray-500">
      No stories found
    </div>
  {:else}
    <!-- Virtual scroll container with spacer -->
    <div style="height: {stories.length * ITEM_HEIGHT}px; position: relative;">
      <div
        class="p-2 sm:p-4 space-y-2 sm:space-y-3"
        style="position: absolute; top: {visibleStart * ITEM_HEIGHT}px; left: 0; right: 0;"
      >
        {#each visibleStories as story, index}
        <button
          class="w-full text-left bg-[#1a1a2e] border border-gray-800 rounded-lg p-3 sm:p-4 hover:border-purple-600/50 active:bg-slate-800 transition-colors"
          onclick={() => onStoryClick?.(story)}
        >
          <div class="flex items-start justify-between gap-4">
            <div class="flex-1 min-w-0">
              <h3 class="font-medium text-white truncate">{story.title}</h3>

              <div class="flex items-center gap-2 mt-1 text-sm text-gray-400 flex-wrap">
                {#if story.story_type}
                  <div class="flex items-center gap-1.5">
                    <span
                      class="w-2 h-2 rounded-full flex-shrink-0"
                      style="background-color: {getStoryTypeColor(story.story_type)}"
                    ></span>
                    <span>{formatStoryType(story.story_type)}</span>
                  </div>
                {/if}
                {#if story.story_type && story.location}
                  <span class="text-gray-600">·</span>
                {/if}
                {#if story.location}
                  <span class="text-gray-500 truncate">{story.location}</span>
                {/if}
              </div>

              {#if story.podcast_name || story.air_date}
                <div class="mt-1 text-xs text-gray-500">
                  {story.podcast_name}
                  {#if story.air_date}
                    &middot; {story.air_date}
                  {/if}
                </div>
              {/if}

              {#if isSearchResult(story) && story.snippet}
                <p class="mt-2 text-sm text-gray-400 line-clamp-2">
                  {story.snippet}...
                </p>
              {:else if story.summary}
                <p class="mt-2 text-sm text-gray-400 line-clamp-2">
                  {story.summary}
                </p>
              {/if}
            </div>

            {#if isSearchResult(story) && story.score !== undefined}
              <div class="flex-shrink-0 text-right">
                <div class="text-xs text-gray-500">Score</div>
                <div class="text-sm text-purple-400 font-medium">
                  {(story.score * 100).toFixed(0)}%
                </div>
              </div>
            {/if}
          </div>
        </button>
      {/each}
      </div>
    </div>
  {/if}
</div>
