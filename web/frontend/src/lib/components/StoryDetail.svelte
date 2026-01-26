<script lang="ts">
  import { onMount } from 'svelte';
  import { api, type StoryDetail } from '$lib/api';
  import { getStoryTypeColor, formatStoryType } from '$lib/stores';

  interface Props {
    storyId: string;
    onClose: () => void;
  }

  let { storyId, onClose }: Props = $props();

  let story: StoryDetail | null = $state(null);
  let loading = $state(true);
  let error: string | null = $state(null);

  onMount(async () => {
    try {
      story = await api.getStory(storyId);
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to load story';
    } finally {
      loading = false;
    }
  });
</script>

<!-- svelte-ignore a11y_click_events_have_key_events -->
<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
  class="fixed inset-0 bg-black/70 lg:bg-black/50 z-50 flex items-end lg:items-center justify-center lg:p-4"
  onclick={(e) => { if (e.target === e.currentTarget) onClose(); }}
>
  <div class="
    bg-[#1a1a2e]
    border-t lg:border border-gray-700
    rounded-t-2xl lg:rounded-xl
    max-w-2xl
    w-full
    h-[92vh] lg:h-auto lg:max-h-[85vh]
    overflow-hidden
    flex flex-col
    animate-slide-up lg:animate-none
  ">
    <!-- Header -->
    <div class="flex items-start justify-between p-4 md:p-5 border-b border-gray-800 flex-shrink-0">
      <div class="flex-1 min-w-0 pr-4">
        {#if loading}
          <div class="h-6 md:h-7 w-48 bg-gray-700 animate-pulse rounded"></div>
        {:else if story}
          <h2 class="text-lg md:text-xl lg:text-2xl font-bold text-white leading-tight">
            {story.title}
          </h2>
          {#if story.story_type}
            <div class="flex items-center gap-2 mt-2">
              <span
                class="w-3 h-3 md:w-4 md:h-4 rounded-full flex-shrink-0"
                style="background-color: {getStoryTypeColor(story.story_type)}"
              ></span>
              <span class="text-sm md:text-base text-gray-400 font-medium">
                {formatStoryType(story.story_type)}
              </span>
            </div>
          {/if}
        {/if}
      </div>
      <button
        class="flex-shrink-0 p-2 -mr-2 -mt-1 text-gray-500 hover:text-white active:text-purple-400 transition-colors touch-manipulation"
        onclick={onClose}
        aria-label="Close"
      >
        <svg class="w-6 h-6 md:w-7 md:h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>

    <!-- Content -->
    <div class="flex-1 overflow-y-auto overscroll-contain p-4 md:p-5 lg:p-6">
      {#if loading}
        <div class="space-y-3 md:space-y-4">
          <div class="h-4 md:h-5 bg-gray-700 animate-pulse rounded w-3/4"></div>
          <div class="h-4 md:h-5 bg-gray-700 animate-pulse rounded w-full"></div>
          <div class="h-4 md:h-5 bg-gray-700 animate-pulse rounded w-5/6"></div>
        </div>
      {:else if error}
        <div class="text-red-400 text-sm md:text-base">{error}</div>
      {:else if story}
        <!-- Metadata -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 md:gap-4 mb-6 text-sm md:text-base">
          {#if story.podcast_name}
            <div class="flex flex-col sm:block">
              <span class="text-gray-500 font-medium">Show:</span>
              <span class="text-gray-300 sm:ml-2">{story.podcast_name}</span>
            </div>
          {/if}
          {#if story.air_date}
            <div class="flex flex-col sm:block">
              <span class="text-gray-500 font-medium">Date:</span>
              <span class="text-gray-300 sm:ml-2">{story.air_date}</span>
            </div>
          {/if}
          {#if story.location}
            <div class="flex flex-col sm:block">
              <span class="text-gray-500 font-medium">Location:</span>
              <span class="text-gray-300 sm:ml-2">{story.location}</span>
            </div>
          {/if}
          {#if story.time_period}
            <div class="flex flex-col sm:block">
              <span class="text-gray-500 font-medium">Time Period:</span>
              <span class="text-gray-300 sm:ml-2">{story.time_period}</span>
            </div>
          {/if}
        </div>

        <!-- Frameworks -->
        {#if story.frameworks && Object.keys(story.frameworks).length > 0}
          <div class="mb-6">
            <h3 class="text-xs md:text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">
              Framework Classifications
            </h3>
            <div class="flex flex-wrap gap-2">
              {#each Object.entries(story.frameworks) as [framework, categories]}
                {#each categories as category}
                  <span class="px-3 py-1.5 bg-purple-900/30 border border-purple-700/50 rounded-lg text-xs md:text-sm text-purple-300 font-medium">
                    {framework}: {category.replace(/_/g, ' ')}
                  </span>
                {/each}
              {/each}
            </div>
          </div>
        {/if}

        <!-- Story content -->
        {#if story.summary}
          <div class="mb-6">
            <h3 class="text-xs md:text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">
              Summary
            </h3>
            <p class="text-gray-300 text-sm md:text-base leading-relaxed">{story.summary}</p>
          </div>
        {/if}

        <div class="pb-safe">
          <h3 class="text-xs md:text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">
            Full Story
          </h3>
          <div class="text-gray-300 text-sm md:text-base whitespace-pre-wrap leading-relaxed">
            {story.content}
          </div>
        </div>

        <!-- Vector coordinates -->
        {#if story.umap_x !== null && story.umap_y !== null}
          <div class="mt-6 pt-4 border-t border-gray-800 pb-safe">
            <div class="text-xs md:text-sm text-gray-500">
              Vector Position: ({story.umap_x?.toFixed(3)}, {story.umap_y?.toFixed(3)})
            </div>
          </div>
        {/if}
      {/if}
    </div>
  </div>
</div>

<style>
  @keyframes slide-up {
    from {
      transform: translateY(100%);
    }
    to {
      transform: translateY(0);
    }
  }

  .animate-slide-up {
    animation: slide-up 0.3s ease-out;
  }

  .pb-safe {
    padding-bottom: max(1rem, env(safe-area-inset-bottom));
  }
</style>
