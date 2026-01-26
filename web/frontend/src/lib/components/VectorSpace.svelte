<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import * as THREE from 'three';
  import type { VectorPoint } from '$lib/api';
  import { getStoryTypeColor, formatStoryType } from '$lib/stores';

  interface Props {
    points: VectorPoint[];
    onPointClick?: (point: VectorPoint) => void;
  }

  let { points, onPointClick }: Props = $props();

  let container: HTMLDivElement;
  let renderer: THREE.WebGLRenderer | null = null;
  let scene: THREE.Scene | null = null;
  let camera: THREE.PerspectiveCamera | null = null;
  let pointsMesh: THREE.Points | null = null;
  let raycaster: THREE.Raycaster | null = null;
  let mouse: THREE.Vector2 | null = null;
  let animationId: number | null = null;
  let isDragging = false;
  let previousMouse = { x: 0, y: 0 };
  let rotation = { x: 0, y: 0 };
  let zoom = 50;

  let tooltip: { x: number; y: number; point: VectorPoint } | null = $state(null);
  let hoveredIndex: number | null = null;

  // Normalize UMAP coordinates to scene space
  function normalizeCoords(points: VectorPoint[]): { x: number; y: number; z: number }[] {
    if (points.length === 0) return [];

    const xs = points.map(p => p.x);
    const ys = points.map(p => p.y);

    const minX = Math.min(...xs);
    const maxX = Math.max(...xs);
    const minY = Math.min(...ys);
    const maxY = Math.max(...ys);

    const rangeX = maxX - minX || 1;
    const rangeY = maxY - minY || 1;
    const scale = 40; // Scene units

    return points.map(p => ({
      x: ((p.x - minX) / rangeX - 0.5) * scale,
      y: ((p.y - minY) / rangeY - 0.5) * scale,
      z: (Math.random() - 0.5) * 5, // Add slight z variation for depth
    }));
  }

  onMount(() => {
    // Initialize Three.js scene
    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0f0f1a);

    camera = new THREE.PerspectiveCamera(
      60,
      container.clientWidth / container.clientHeight,
      0.1,
      1000
    );
    camera.position.z = zoom;

    renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.setPixelRatio(window.devicePixelRatio);
    container.appendChild(renderer.domElement);

    raycaster = new THREE.Raycaster();
    raycaster.params.Points = { threshold: 0.5 };
    mouse = new THREE.Vector2();

    // Add grid helper
    const gridHelper = new THREE.GridHelper(50, 50, 0x333333, 0x222222);
    gridHelper.rotation.x = Math.PI / 2;
    scene.add(gridHelper);

    // Add ambient light
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.5);
    scene.add(ambientLight);

    updatePoints();

    // Event listeners
    container.addEventListener('mousedown', onMouseDown);
    container.addEventListener('mousemove', onMouseMove);
    container.addEventListener('mouseup', onMouseUp);
    container.addEventListener('mouseleave', onMouseUp);
    container.addEventListener('wheel', onWheel);
    window.addEventListener('resize', onResize);

    // Animation loop
    animate();
  });

  onDestroy(() => {
    if (animationId !== null) {
      cancelAnimationFrame(animationId);
    }
    if (renderer) {
      renderer.dispose();
      container?.removeChild(renderer.domElement);
    }
    container?.removeEventListener('mousedown', onMouseDown);
    container?.removeEventListener('mousemove', onMouseMove);
    container?.removeEventListener('mouseup', onMouseUp);
    container?.removeEventListener('mouseleave', onMouseUp);
    container?.removeEventListener('wheel', onWheel);
    window.removeEventListener('resize', onResize);
  });

  function updatePoints() {
    if (!scene) return;

    // Remove old points
    if (pointsMesh) {
      scene.remove(pointsMesh);
      pointsMesh.geometry.dispose();
      (pointsMesh.material as THREE.Material).dispose();
    }

    if (points.length === 0) return;

    const normalizedCoords = normalizeCoords(points);
    const geometry = new THREE.BufferGeometry();
    const positions: number[] = [];
    const colors: number[] = [];

    normalizedCoords.forEach((coord, i) => {
      positions.push(coord.x, coord.y, coord.z);

      const hex = points[i].color || getStoryTypeColor(points[i].story_type);
      const r = parseInt(hex.slice(1, 3), 16) / 255;
      const g = parseInt(hex.slice(3, 5), 16) / 255;
      const b = parseInt(hex.slice(5, 7), 16) / 255;
      colors.push(r, g, b);
    });

    geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
    geometry.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));

    const material = new THREE.PointsMaterial({
      size: 0.8,
      vertexColors: true,
      transparent: true,
      opacity: 0.9,
      sizeAttenuation: true,
    });

    pointsMesh = new THREE.Points(geometry, material);
    scene.add(pointsMesh);
  }

  function animate() {
    animationId = requestAnimationFrame(animate);

    if (scene && camera && renderer && pointsMesh) {
      // Apply rotation
      pointsMesh.rotation.x = rotation.x;
      pointsMesh.rotation.y = rotation.y;

      // Auto-rotate slightly when not interacting
      if (!isDragging) {
        rotation.y += 0.001;
      }

      renderer.render(scene, camera);
    }
  }

  function onMouseDown(e: MouseEvent) {
    isDragging = true;
    previousMouse = { x: e.clientX, y: e.clientY };
  }

  function onMouseMove(e: MouseEvent) {
    if (isDragging) {
      const deltaX = e.clientX - previousMouse.x;
      const deltaY = e.clientY - previousMouse.y;
      rotation.y += deltaX * 0.005;
      rotation.x += deltaY * 0.005;
      previousMouse = { x: e.clientX, y: e.clientY };
      tooltip = null;
    } else {
      // Check for hover
      checkHover(e);
    }
  }

  function onMouseUp() {
    isDragging = false;
  }

  function onWheel(e: WheelEvent) {
    e.preventDefault();
    zoom += e.deltaY * 0.05;
    zoom = Math.max(20, Math.min(150, zoom));
    if (camera) {
      camera.position.z = zoom;
    }
  }

  function onResize() {
    if (!camera || !renderer) return;
    camera.aspect = container.clientWidth / container.clientHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(container.clientWidth, container.clientHeight);
  }

  function checkHover(e: MouseEvent) {
    if (!raycaster || !mouse || !camera || !pointsMesh) return;

    const rect = container.getBoundingClientRect();
    mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
    mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

    raycaster.setFromCamera(mouse, camera);
    const intersects = raycaster.intersectObject(pointsMesh);

    if (intersects.length > 0) {
      const index = intersects[0].index;
      if (index !== undefined && index < points.length) {
        hoveredIndex = index;
        tooltip = { x: e.clientX - rect.left, y: e.clientY - rect.top, point: points[index] };
        container.style.cursor = 'pointer';
      }
    } else {
      hoveredIndex = null;
      tooltip = null;
      container.style.cursor = 'grab';
    }
  }

  function handleClick(e: MouseEvent) {
    if (isDragging) return;
    checkHover(e);
    if (hoveredIndex !== null && onPointClick) {
      onPointClick(points[hoveredIndex]);
    }
  }

  $effect(() => {
    if (points) {
      updatePoints();
    }
  });
</script>

<!-- svelte-ignore a11y_click_events_have_key_events -->
<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
  class="relative w-full h-full cursor-grab"
  bind:this={container}
  onclick={handleClick}
>
  {#if tooltip}
    <div
      class="absolute z-10 px-3 py-2 bg-[#1a1a2e] border border-gray-700 rounded-lg shadow-lg pointer-events-none"
      style="left: {tooltip.x + 10}px; top: {tooltip.y + 10}px; max-width: 300px;"
    >
      <div class="font-medium text-white text-sm">{tooltip.point.title}</div>
      {#if tooltip.point.story_type}
        <div class="flex items-center gap-2 mt-1">
          <span
            class="w-2 h-2 rounded-full"
            style="background-color: {getStoryTypeColor(tooltip.point.story_type)}"
          ></span>
          <span class="text-xs text-gray-400">{formatStoryType(tooltip.point.story_type)}</span>
        </div>
      {/if}
    </div>
  {/if}

  <!-- Legend -->
  <div class="absolute bottom-4 left-4 bg-[#1a1a2e]/90 border border-gray-700 rounded-lg p-3 z-10">
    <div class="text-xs text-gray-400 mb-2">Story Types</div>
    <div class="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
      {#each Object.entries({ ghost: '#9b59b6', shadow_person: '#2c3e50', ufo: '#3498db', alien_encounter: '#1abc9c', cryptid: '#27ae60', haunting: '#8e44ad' }) as [type, color]}
        <div class="flex items-center gap-1">
          <span class="w-2 h-2 rounded-full" style="background-color: {color}"></span>
          <span class="text-gray-300">{formatStoryType(type)}</span>
        </div>
      {/each}
    </div>
  </div>

  <!-- Instructions -->
  <div class="absolute top-4 right-4 bg-[#1a1a2e]/90 border border-gray-700 rounded-lg p-3 z-10 text-xs text-gray-400">
    <div>Drag to rotate</div>
    <div>Scroll to zoom</div>
    <div>Click to select</div>
  </div>
</div>
