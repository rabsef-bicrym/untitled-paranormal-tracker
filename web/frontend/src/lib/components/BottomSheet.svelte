<script lang="ts">
  import { onMount } from 'svelte';
  import { gesture } from '$lib/utils/gestures';

  interface Props {
    open: boolean;
    onClose: () => void;
    title?: string;
    height?: number; // percentage height (default 80)
    children?: any;
  }

  let { open = $bindable(false), onClose, title = '', height = 80, children }: Props = $props();

  let sheetElement: HTMLDivElement;
  let dragStartY = 0;
  let currentTranslateY = 0;
  let isDragging = false;

  const DISMISS_THRESHOLD = 100; // pixels to drag down before dismissing

  function handleBackdropClick() {
    onClose();
  }

  function handleDragStart(e: TouchEvent) {
    isDragging = true;
    dragStartY = e.touches[0].clientY;
    currentTranslateY = 0;
  }

  function handleDragMove(e: TouchEvent) {
    if (!isDragging) return;

    const currentY = e.touches[0].clientY;
    const deltaY = currentY - dragStartY;

    // Only allow dragging down (positive deltaY)
    if (deltaY > 0) {
      currentTranslateY = deltaY;
      if (sheetElement) {
        sheetElement.style.transform = `translateY(${deltaY}px)`;
      }
    }
  }

  function handleDragEnd() {
    if (!isDragging) return;

    isDragging = false;

    if (currentTranslateY > DISMISS_THRESHOLD) {
      // Dismiss
      onClose();
    } else {
      // Snap back
      if (sheetElement) {
        sheetElement.style.transform = 'translateY(0)';
      }
    }

    currentTranslateY = 0;
  }

  onMount(() => {
    if (sheetElement) {
      sheetElement.addEventListener('touchstart', handleDragStart, { passive: true });
      sheetElement.addEventListener('touchmove', handleDragMove, { passive: true });
      sheetElement.addEventListener('touchend', handleDragEnd, { passive: true });
    }

    return () => {
      if (sheetElement) {
        sheetElement.removeEventListener('touchstart', handleDragStart);
        sheetElement.removeEventListener('touchmove', handleDragMove);
        sheetElement.removeEventListener('touchend', handleDragEnd);
      }
    };
  });
</script>

{#if open}
  <!-- Backdrop -->
  <button
    onclick={handleBackdropClick}
    class="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 animate-fade-in"
    aria-label="Close"
  ></button>

  <!-- Bottom Sheet -->
  <div
    bind:this={sheetElement}
    class="fixed bottom-0 left-0 right-0 z-50 bg-slate-900 rounded-t-2xl border-t border-purple-500/20 shadow-2xl animate-slide-up"
    style="height: {height}vh; max-height: {height}vh; padding-bottom: env(safe-area-inset-bottom, 0px);"
  >
    <!-- Drag Handle -->
    <div class="flex justify-center pt-3 pb-2 cursor-grab active:cursor-grabbing">
      <div class="w-12 h-1 bg-slate-600 rounded-full"></div>
    </div>

    <!-- Header -->
    {#if title}
      <div class="px-4 pb-3 border-b border-slate-800">
        <h2 class="text-lg font-bold text-white font-['Orbitron']">{title}</h2>
      </div>
    {/if}

    <!-- Content (scrollable) -->
    <div class="overflow-y-auto overscroll-contain h-[calc(100%-3rem)] px-4 py-4">
      {@render children?.()}
    </div>
  </div>
{/if}

<style>
  @keyframes fade-in {
    from {
      opacity: 0;
    }
    to {
      opacity: 1;
    }
  }

  @keyframes slide-up {
    from {
      transform: translateY(100%);
    }
    to {
      transform: translateY(0);
    }
  }

  .animate-fade-in {
    animation: fade-in 0.2s ease-out;
  }

  .animate-slide-up {
    animation: slide-up 0.3s cubic-bezier(0.32, 0.72, 0, 1);
  }

  /* Smooth momentum scrolling on iOS */
  .overscroll-contain {
    -webkit-overflow-scrolling: touch;
    overscroll-behavior: contain;
  }
</style>
