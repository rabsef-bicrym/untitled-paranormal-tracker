<script lang="ts">
  import { onDestroy } from 'svelte';
  import { api, type MapStory, type StoryDetail } from '$lib/api';
  import { formatStoryType, getStoryTypeColor } from '$lib/stores';

  interface Props {
    stories: MapStory[];
    count: number;
    position: { x: number; y: number };
    onClose: () => void;
    onOpenStory?: (story: MapStory) => void;
  }

  let { stories, count, position, onClose, onOpenStory }: Props = $props();

  let windowPosition = $state({ x: position.x, y: position.y });
  let dragOffset = { x: 0, y: 0 };
  let isDragging = false;

  let details = $state<Record<string, StoryDetail | null>>({});
  let loading = $state<Record<string, boolean>>({});
  let errors = $state<Record<string, string>>({});

  function clamp(value: number, min: number, max: number) {
    return Math.min(Math.max(value, min), max);
  }

  function clampPosition(pos: { x: number; y: number }) {
    const width = 420;
    const height = 520;
    const maxX = Math.max(24, window.innerWidth - width - 24);
    const maxY = Math.max(24, window.innerHeight - height - 24);
    return {
      x: clamp(pos.x, 24, maxX),
      y: clamp(pos.y, 24, maxY),
    };
  }

  $effect(() => {
    void stories;
    windowPosition = clampPosition(position);
    details = {};
    loading = {};
    errors = {};
  });

  function startDrag(event: PointerEvent) {
    event.preventDefault();
    isDragging = true;
    dragOffset = {
      x: event.clientX - windowPosition.x,
      y: event.clientY - windowPosition.y,
    };
    window.addEventListener('pointermove', onDrag);
    window.addEventListener('pointerup', stopDrag);
  }

  function onDrag(event: PointerEvent) {
    if (!isDragging) return;
    windowPosition = clampPosition({
      x: event.clientX - dragOffset.x,
      y: event.clientY - dragOffset.y,
    });
  }

  function stopDrag() {
    isDragging = false;
    window.removeEventListener('pointermove', onDrag);
    window.removeEventListener('pointerup', stopDrag);
  }

  onDestroy(() => {
    stopDrag();
  });

  async function loadStory(storyId: string) {
    if (details[storyId] || loading[storyId]) return;
    loading[storyId] = true;
    errors[storyId] = '';

    try {
      details[storyId] = await api.getStory(storyId);
    } catch (err) {
      errors[storyId] = err instanceof Error ? err.message : 'Failed to load story';
    } finally {
      loading[storyId] = false;
    }
  }

  function handleToggle(event: Event, storyId: string) {
    const target = event.currentTarget as HTMLDetailsElement;
    if (target.open) {
      loadStory(storyId);
    }
  }
</script>

<svelte:window onkeydown={(event) => event.key === 'Escape' && onClose()} />

<div
  class="fixed z-40 w-[420px] max-w-[90vw] max-h-[75vh] bg-slate-950/90 border border-cyan-500/30 shadow-[0_0_30px_rgba(34,211,238,0.25)] rounded-xl backdrop-blur"
  style="left: {windowPosition.x}px; top: {windowPosition.y}px;"
  onclick={(event) => event.stopPropagation()}
>
  <div
    class="cursor-grab active:cursor-grabbing flex items-center justify-between px-4 py-3 border-b border-cyan-500/20"
    onpointerdown={startDrag}
  >
    <div>
      <div class="text-xs uppercase tracking-[0.25em] text-cyan-200">Area Window</div>
      <div class="text-sm text-slate-200">{count} stories in this area</div>
    </div>
    <button
      class="text-slate-400 hover:text-white text-lg leading-none"
      onclick={onClose}
      aria-label="Close"
    >
      &times;
    </button>
  </div>

  <div class="p-4 overflow-y-auto max-h-[65vh] space-y-2">
    {#each stories as story}
      <details
        class="group border border-slate-800/80 rounded-lg bg-slate-900/40"
        ontoggle={(event) => handleToggle(event, story.id)}
      >
        <summary class="list-none cursor-pointer px-3 py-2 flex items-center justify-between gap-2">
          <div class="flex items-center gap-2">
            <span
              class="w-2 h-2 rounded-full"
              style="background-color: {getStoryTypeColor(story.story_type)}"
            ></span>
            <div class="text-sm text-slate-100">{story.title}</div>
          </div>
          <div class="text-xs text-slate-400">{story.location ?? 'Unknown'}</div>
        </summary>

        <div class="px-3 pb-3 text-sm text-slate-300 border-t border-slate-800/80">
          {#if loading[story.id]}
            <div class="text-xs text-slate-500 mt-2">Loading story…</div>
          {:else if errors[story.id]}
            <div class="text-xs text-red-400 mt-2">{errors[story.id]}</div>
          {:else if details[story.id]}
            <div class="mt-2 space-y-2">
              <div class="text-xs text-cyan-200">
                {details[story.id]?.story_type ? formatStoryType(details[story.id]?.story_type || '') : 'Uncategorized'}
              </div>
              {#if details[story.id]?.summary}
                <p class="text-sm text-slate-200">{details[story.id]?.summary}</p>
              {:else}
                <p class="text-sm text-slate-200 whitespace-pre-wrap">{details[story.id]?.content}</p>
              {/if}
              {#if onOpenStory}
                <button
                  class="mt-2 text-xs uppercase tracking-[0.2em] text-cyan-200/80 hover:text-cyan-100"
                  onclick={() => onOpenStory?.(story)}
                >
                  Open Full Story
                </button>
              {/if}
            </div>
          {:else}
            <div class="text-xs text-slate-500 mt-2">Expand to load story details.</div>
          {/if}
        </div>
      </details>
    {/each}
  </div>
</div>
