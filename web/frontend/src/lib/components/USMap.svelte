<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { Deck } from '@deck.gl/core';
  import { ScatterplotLayer } from '@deck.gl/layers';
  import maplibregl from 'maplibre-gl';
  import 'maplibre-gl/dist/maplibre-gl.css';
  import type { MapStory } from '$lib/api';
  import { getStoryTypeColor, formatStoryType } from '$lib/stores';

  interface Props {
    stories: MapStory[];
    onStoryClick?: (story: MapStory) => void;
  }

  let { stories, onStoryClick }: Props = $props();

  let container: HTMLDivElement;
  let map: maplibregl.Map | null = null;
  let deck: Deck | null = null;
  let tooltip: { x: number; y: number; story: MapStory } | null = $state(null);

  // US center coordinates
  const INITIAL_VIEW = {
    longitude: -98.5795,
    latitude: 39.8283,
    zoom: 4,
    pitch: 0,
    bearing: 0,
  };

  onMount(() => {
    // Initialize MapLibre map
    map = new maplibregl.Map({
      container,
      style: {
        version: 8,
        sources: {
          'osm': {
            type: 'raster',
            tiles: [
              'https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png',
              'https://b.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png',
              'https://c.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png',
            ],
            tileSize: 256,
            attribution: '&copy; OpenStreetMap contributors, &copy; CARTO',
          },
        },
        layers: [
          {
            id: 'osm',
            type: 'raster',
            source: 'osm',
            minzoom: 0,
            maxzoom: 19,
          },
        ],
      },
      center: [INITIAL_VIEW.longitude, INITIAL_VIEW.latitude],
      zoom: INITIAL_VIEW.zoom,
      pitch: INITIAL_VIEW.pitch,
      bearing: INITIAL_VIEW.bearing,
    });

    map.addControl(new maplibregl.NavigationControl(), 'top-right');

    // Initialize deck.gl overlay
    deck = new Deck({
      parent: container,
      style: { position: 'absolute', top: '0', left: '0', zIndex: '1', pointerEvents: 'none' },
      initialViewState: INITIAL_VIEW,
      controller: false,
      layers: [],
      getTooltip: null,
    });

    // Sync deck.gl with map movement
    map.on('move', () => {
      if (!map || !deck) return;
      const center = map.getCenter();
      deck.setProps({
        viewState: {
          longitude: center.lng,
          latitude: center.lat,
          zoom: map.getZoom(),
          pitch: map.getPitch(),
          bearing: map.getBearing(),
        },
      });
    });

    // Handle clicks on deck.gl layer
    map.on('click', (e) => {
      if (!deck) return;
      const picked = deck.pickObject({
        x: e.point.x,
        y: e.point.y,
        radius: 10,
      });
      if (picked?.object && onStoryClick) {
        onStoryClick(picked.object as MapStory);
      }
    });

    // Handle hover for tooltip
    map.on('mousemove', (e) => {
      if (!deck) return;
      const picked = deck.pickObject({
        x: e.point.x,
        y: e.point.y,
        radius: 10,
      });
      if (picked?.object) {
        tooltip = { x: e.point.x, y: e.point.y, story: picked.object as MapStory };
        container.style.cursor = 'pointer';
      } else {
        tooltip = null;
        container.style.cursor = '';
      }
    });

    updateLayers();
  });

  onDestroy(() => {
    deck?.finalize();
    map?.remove();
  });

  function updateLayers() {
    if (!deck) return;

    const scatterLayer = new ScatterplotLayer({
      id: 'stories',
      data: stories,
      pickable: true,
      opacity: 0.8,
      stroked: true,
      filled: true,
      radiusScale: 1,
      radiusMinPixels: 6,
      radiusMaxPixels: 20,
      lineWidthMinPixels: 1,
      getPosition: (d: MapStory) => [d.lng, d.lat],
      getRadius: 8,
      getFillColor: (d: MapStory) => {
        const hex = getStoryTypeColor(d.story_type);
        const r = parseInt(hex.slice(1, 3), 16);
        const g = parseInt(hex.slice(3, 5), 16);
        const b = parseInt(hex.slice(5, 7), 16);
        return [r, g, b, 200];
      },
      getLineColor: [255, 255, 255, 100],
    });

    deck.setProps({ layers: [scatterLayer] });
  }

  $effect(() => {
    if (stories) {
      updateLayers();
    }
  });
</script>

<div class="relative w-full h-full" bind:this={container}>
  {#if tooltip}
    <div
      class="absolute z-10 px-3 py-2 bg-[#1a1a2e] border border-gray-700 rounded-lg shadow-lg pointer-events-none"
      style="left: {tooltip.x + 10}px; top: {tooltip.y + 10}px; max-width: 300px;"
    >
      <div class="font-medium text-white text-sm">{tooltip.story.title}</div>
      {#if tooltip.story.story_type}
        <div class="flex items-center gap-2 mt-1">
          <span
            class="w-2 h-2 rounded-full"
            style="background-color: {getStoryTypeColor(tooltip.story.story_type)}"
          ></span>
          <span class="text-xs text-gray-400">{formatStoryType(tooltip.story.story_type)}</span>
        </div>
      {/if}
      {#if tooltip.story.location}
        <div class="text-xs text-gray-500 mt-1">{tooltip.story.location}</div>
      {/if}
    </div>
  {/if}
</div>

<style>
  :global(.maplibregl-canvas-container) {
    position: absolute !important;
  }
</style>
