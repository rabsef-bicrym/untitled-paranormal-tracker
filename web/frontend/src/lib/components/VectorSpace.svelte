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

    // Event listeners - both mouse and touch
    container.addEventListener('mousedown', onMouseDown);
    container.addEventListener('mousemove', onMouseMove);
    container.addEventListener('mouseup', onMouseUp);
    container.addEventListener('mouseleave', onMouseUp);
    container.addEventListener('wheel', onWheel, { passive: false });

    // Touch events for mobile
    container.addEventListener('touchstart', onTouchStart, { passive: false });
    container.addEventListener('touchmove', onTouchMove, { passive: false });
    container.addEventListener('touchend', onTouchEnd);

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
    container?.removeEventListener('touchstart', onTouchStart);
    container?.removeEventListener('touchmove', onTouchMove);
    container?.removeEventListener('touchend', onTouchEnd);
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

    // Larger points on mobile for better touch targets
    const isMobile = typeof window !== 'undefined' && window.innerWidth < 768;
    const pointSize = isMobile ? 1.2 : 0.8;

    const material = new THREE.PointsMaterial({
      size: pointSize,
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

  // Touch event handlers for mobile
  let touchStartDistance = 0;
  let lastTouchX = 0;
  let lastTouchY = 0;

  function onTouchStart(e: TouchEvent) {
    if (e.touches.length === 1) {
      isDragging = true;
      lastTouchX = e.touches[0].clientX;
      lastTouchY = e.touches[0].clientY;
    } else if (e.touches.length === 2) {
      // Pinch to zoom
      isDragging = false;
      const dx = e.touches[0].clientX - e.touches[1].clientX;
      const dy = e.touches[0].clientY - e.touches[1].clientY;
      touchStartDistance = Math.sqrt(dx * dx + dy * dy);
    }
  }

  function onTouchMove(e: TouchEvent) {
    e.preventDefault();

    if (e.touches.length === 1 && isDragging) {
      // Rotate
      const deltaX = e.touches[0].clientX - lastTouchX;
      const deltaY = e.touches[0].clientY - lastTouchY;
      rotation.y += deltaX * 0.01;
      rotation.x += deltaY * 0.01;
      lastTouchX = e.touches[0].clientX;
      lastTouchY = e.touches[0].clientY;
      tooltip = null;
    } else if (e.touches.length === 2) {
      // Pinch to zoom
      const dx = e.touches[0].clientX - e.touches[1].clientX;
      const dy = e.touches[0].clientY - e.touches[1].clientY;
      const distance = Math.sqrt(dx * dx + dy * dy);
      const delta = touchStartDistance - distance;
      zoom += delta * 0.1;
      zoom = Math.max(20, Math.min(150, zoom));
      if (camera) {
        camera.position.z = zoom;
      }
      touchStartDistance = distance;
    }
  }

  function onTouchEnd() {
    isDragging = false;
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
  class="relative w-full h-full touch-none cursor-grab active:cursor-grabbing"
  bind:this={container}
  onclick={handleClick}
>
  {#if tooltip}
    <div
      class="absolute z-10 px-3 md:px-4 py-2 md:py-3 bg-[#1a1a2e]/95 backdrop-blur border border-gray-700 rounded-lg md:rounded-xl shadow-xl pointer-events-none max-w-[280px] md:max-w-sm"
      style="left: {Math.min(tooltip.x + 10, typeof window !== 'undefined' ? window.innerWidth - 300 : tooltip.x + 10)}px; top: {tooltip.y + 10}px;"
    >
      <div class="font-semibold text-white text-sm md:text-base leading-snug">{tooltip.point.title}</div>
      {#if tooltip.point.story_type}
        <div class="flex items-center gap-2 mt-1.5">
          <span
            class="w-2.5 h-2.5 md:w-3 md:h-3 rounded-full flex-shrink-0"
            style="background-color: {getStoryTypeColor(tooltip.point.story_type)}"
          ></span>
          <span class="text-xs md:text-sm text-gray-400 font-medium">{formatStoryType(tooltip.point.story_type)}</span>
        </div>
      {/if}
    </div>
  {/if}

  <!-- Legend -->
  <div class="absolute bottom-3 md:bottom-4 left-3 md:left-4 bg-[#1a1a2e]/95 backdrop-blur border border-gray-700 rounded-lg md:rounded-xl p-2.5 md:p-3 z-10 max-w-[180px] md:max-w-none">
    <div class="text-xs md:text-sm text-gray-400 mb-2 font-semibold">Story Types</div>
    <div class="grid grid-cols-1 md:grid-cols-2 gap-x-4 gap-y-1.5 text-xs md:text-sm">
      {#each Object.entries({ ghost: '#9b59b6', shadow_person: '#2c3e50', ufo: '#3498db', alien_encounter: '#1abc9c', cryptid: '#27ae60', haunting: '#8e44ad' }) as [type, color]}
        <div class="flex items-center gap-1.5">
          <span class="w-2 h-2 md:w-2.5 md:h-2.5 rounded-full flex-shrink-0" style="background-color: {color}"></span>
          <span class="text-gray-300 truncate">{formatStoryType(type)}</span>
        </div>
      {/each}
    </div>
  </div>

  <!-- Instructions -->
  <div class="absolute top-3 md:top-4 right-3 md:right-4 bg-[#1a1a2e]/95 backdrop-blur border border-gray-700 rounded-lg md:rounded-xl p-2.5 md:p-3 z-10 text-xs md:text-sm text-gray-400">
    <div class="hidden md:block">
      <div>Drag to rotate</div>
      <div>Scroll to zoom</div>
      <div>Click to select</div>
    </div>
    <div class="md:hidden">
      <div>Drag to rotate</div>
      <div>Pinch to zoom</div>
      <div>Tap to select</div>
    </div>
  </div>
</div>
