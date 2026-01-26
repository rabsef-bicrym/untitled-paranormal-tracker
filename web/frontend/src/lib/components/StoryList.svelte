<script lang="ts">
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
</script>

<div class="h-full overflow-y-auto overscroll-contain">
  {#if loading}
    <div class="p-3 md:p-4 space-y-3 md:space-y-4">
      {#each Array(5) as _, i}
        <div class="bg-[#1a1a2e] border border-gray-800 rounded-lg p-4 md:p-5 animate-pulse">
          <div class="h-5 md:h-6 bg-gray-700 rounded w-3/4 mb-2"></div>
          <div class="h-4 bg-gray-700 rounded w-1/2 mb-2"></div>
          <div class="h-4 bg-gray-700 rounded w-full"></div>
        </div>
      {/each}
    </div>
  {:else if stories.length === 0}
    <div class="flex items-center justify-center h-full text-gray-500 text-base md:text-lg px-4">
      No stories found
    </div>
  {:else}
    <div class="p-3 md:p-4 space-y-3 md:space-y-4 pb-safe">
      {#each stories as story}
        <button
          class="w-full text-left bg-[#1a1a2e] border border-gray-800 rounded-xl p-4 md:p-5 hover:border-purple-600/50 active:border-purple-500 active:bg-[#20203a] transition-colors touch-manipulation min-h-[88px]"
          onclick={() => onStoryClick?.(story)}
        >
          <div class="flex items-start justify-between gap-3 md:gap-4">
            <div class="flex-1 min-w-0">
              <h3 class="font-semibold text-base md:text-lg text-white line-clamp-2 leading-snug">
                {story.title}
              </h3>

              <div class="flex items-center flex-wrap gap-2 md:gap-3 mt-2 text-xs md:text-sm text-gray-400">
                {#if story.story_type}
                  <div class="flex items-center gap-1.5">
                    <span
                      class="w-2.5 h-2.5 md:w-3 md:h-3 rounded-full flex-shrink-0"
                      style="background-color: {getStoryTypeColor(story.story_type)}"
                    ></span>
                    <span class="font-medium">{formatStoryType(story.story_type)}</span>
                  </div>
                {/if}
                {#if story.location}
                  <span class="text-gray-500 truncate">{story.location}</span>
                {/if}
              </div>

              {#if story.podcast_name || story.air_date}
                <div class="mt-1.5 text-xs text-gray-500">
                  {story.podcast_name}
                  {#if story.air_date}
                    &middot; {story.air_date}
                  {/if}
                </div>
              {/if}

              {#if isSearchResult(story) && story.snippet}
                <p class="mt-2 md:mt-3 text-sm md:text-base text-gray-400 line-clamp-2 leading-relaxed">
                  {story.snippet}...
                </p>
              {:else if story.summary}
                <p class="mt-2 md:mt-3 text-sm md:text-base text-gray-400 line-clamp-2 leading-relaxed">
                  {story.summary}
                </p>
              {/if}
            </div>

            {#if isSearchResult(story) && story.score !== undefined}
              <div class="flex-shrink-0 text-right">
                <div class="text-xs text-gray-500">Score</div>
                <div class="text-base md:text-lg text-purple-400 font-bold">
                  {(story.score * 100).toFixed(0)}%
                </div>
              </div>
            {/if}
          </div>
        </button>
      {/each}
    </div>
  {/if}
</div>

<style>
  .pb-safe {
    padding-bottom: max(1rem, env(safe-area-inset-bottom));
  }
</style>
