<script lang="ts">
  import { onMount } from 'svelte';
  import '../app.css';
  import Header from '$lib/components/Header.svelte';
  import BottomNav from '$lib/components/BottomNav.svelte';
  import { stats } from '$lib/stores';
  import { api } from '$lib/api';

  let { children } = $props();
  let storyCount = $state(0);

  onMount(async () => {
    // Load stats for story count
    try {
      const statsData = await api.getStats();
      stats.set(statsData);
      storyCount = statsData.total_stories || 0;
    } catch (err) {
      console.error('Failed to load stats:', err);
    }

    // Detect mobile platform
    const isMobile = window.innerWidth < 1024;
    // Add to store if needed in the future
  });
</script>

<svelte:head>
  <title>Retro US Grid</title>
  <meta name="description" content="Retrofuturistic three.js rendering of the contiguous United States." />
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
</svelte:head>

<div class="h-screen w-screen overflow-hidden bg-[#05070f] text-slate-100 flex flex-col">
  <Header {storyCount} />
  <main class="flex-1 overflow-hidden">
    {@render children()}
  </main>
  <BottomNav />
</div>
