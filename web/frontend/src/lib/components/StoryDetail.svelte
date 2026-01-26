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
  class="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4"
  onclick={(e) => { if (e.target === e.currentTarget) onClose(); }}
>
  <div class="bg-[#1a1a2e] border border-gray-700 rounded-xl max-w-2xl w-full max-h-[80vh] overflow-hidden flex flex-col">
    <!-- Header -->
    <div class="flex items-start justify-between p-4 border-b border-gray-800">
      <div>
        {#if loading}
          <div class="h-6 w-48 bg-gray-700 animate-pulse rounded"></div>
        {:else if story}
          <h2 class="text-xl font-bold text-white">{story.title}</h2>
          {#if story.story_type}
            <div class="flex items-center gap-2 mt-2">
              <span
                class="w-3 h-3 rounded-full"
                style="background-color: {getStoryTypeColor(story.story_type)}"
              ></span>
              <span class="text-sm text-gray-400">{formatStoryType(story.story_type)}</span>
            </div>
          {/if}
        {/if}
      </div>
      <button
        class="text-gray-500 hover:text-white text-2xl leading-none"
        onclick={onClose}
      >
        &times;
      </button>
    </div>

    <!-- Content -->
    <div class="flex-1 overflow-y-auto p-4">
      {#if loading}
        <div class="space-y-3">
          <div class="h-4 bg-gray-700 animate-pulse rounded w-3/4"></div>
          <div class="h-4 bg-gray-700 animate-pulse rounded w-full"></div>
          <div class="h-4 bg-gray-700 animate-pulse rounded w-5/6"></div>
        </div>
      {:else if error}
        <div class="text-red-400">{error}</div>
      {:else if story}
        <!-- Metadata -->
        <div class="grid grid-cols-2 gap-4 mb-6 text-sm">
          {#if story.podcast_name}
            <div>
              <span class="text-gray-500">Show:</span>
              <span class="text-gray-300 ml-2">{story.podcast_name}</span>
            </div>
          {/if}
          {#if story.air_date}
            <div>
              <span class="text-gray-500">Date:</span>
              <span class="text-gray-300 ml-2">{story.air_date}</span>
            </div>
          {/if}
          {#if story.location}
            <div>
              <span class="text-gray-500">Location:</span>
              <span class="text-gray-300 ml-2">{story.location}</span>
            </div>
          {/if}
          {#if story.time_period}
            <div>
              <span class="text-gray-500">Time Period:</span>
              <span class="text-gray-300 ml-2">{story.time_period}</span>
            </div>
          {/if}
        </div>

        <!-- Frameworks -->
        {#if story.frameworks && Object.keys(story.frameworks).length > 0}
          <div class="mb-6">
            <h3 class="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-2">
              Framework Classifications
            </h3>
            <div class="flex flex-wrap gap-2">
              {#each Object.entries(story.frameworks) as [framework, categories]}
                {#each categories as category}
                  <span class="px-2 py-1 bg-purple-900/30 border border-purple-700/50 rounded text-xs text-purple-300">
                    {framework}: {category.replace(/_/g, ' ')}
                  </span>
                {/each}
              {/each}
            </div>
          </div>
        {/if}

        <!-- Story content -->
        {#if story.summary}
          <div class="mb-4">
            <h3 class="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-2">
              Summary
            </h3>
            <p class="text-gray-300 text-sm">{story.summary}</p>
          </div>
        {/if}

        <div>
          <h3 class="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-2">
            Full Story
          </h3>
          <div class="text-gray-300 text-sm whitespace-pre-wrap leading-relaxed">
            {story.content}
          </div>
        </div>

        <!-- Vector coordinates -->
        {#if story.umap_x !== null && story.umap_y !== null}
          <div class="mt-6 pt-4 border-t border-gray-800">
            <div class="text-xs text-gray-500">
              Vector Position: ({story.umap_x?.toFixed(3)}, {story.umap_y?.toFixed(3)})
            </div>
          </div>
        {/if}
      {/if}
    </div>
  </div>
</div>
