<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import * as THREE from 'three';
  import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
  import { EffectComposer } from 'three/examples/jsm/postprocessing/EffectComposer.js';
  import { RenderPass } from 'three/examples/jsm/postprocessing/RenderPass.js';
  import { UnrealBloomPass } from 'three/examples/jsm/postprocessing/UnrealBloomPass.js';
  import type { VectorPoint } from '$lib/api';
  import { formatStoryType, getStoryTypeColor, performanceMode } from '$lib/stores';
  import { createGlowTexture, createNebulaTexture } from '$lib/three/textures';
  import * as haptics from '$lib/utils/haptics';
  import { detectDevice } from '$lib/utils/device';
  import { getOptimalSettings } from '$lib/utils/performance';

  interface Props {
    points: VectorPoint[];
    onPointClick?: (point: VectorPoint) => void;
  }

  let { points, onPointClick }: Props = $props();

  let container: HTMLDivElement;
  let renderer: THREE.WebGLRenderer | null = null;
  let composer: EffectComposer | null = null;
  let scene: THREE.Scene | null = null;
  let camera: THREE.PerspectiveCamera | null = null;
  let controls: OrbitControls | null = null;
  let pointsMesh: THREE.Points | null = null;
  let haloMesh: THREE.Points | null = null;
  let wireframe: THREE.LineSegments | null = null;
  let hoverMarker: THREE.Mesh | null = null;
  let raycaster: THREE.Raycaster | null = null;
  let animationId: number | null = null;
  let hoveredIndex: number | null = null;
  let tooltip: { x: number; y: number; point: VectorPoint } | null = $state(null);

  const SPACE_SCALE = 80;
  const clock = new THREE.Clock();
  const mouse = new THREE.Vector2();
  let pointPositions: THREE.Vector3[] = [];
  let glowTexture: THREE.Texture | null = null;
  let nebulaTexture: THREE.Texture | null = null;

  function normalizeCoords(pts: VectorPoint[]) {
    if (pts.length === 0) return [];
    const xs = pts.map(p => p.x);
    const ys = pts.map(p => p.y);
    const zs = pts.map(p => p.z);

    const minX = Math.min(...xs);
    const maxX = Math.max(...xs);
    const minY = Math.min(...ys);
    const maxY = Math.max(...ys);
    const minZ = Math.min(...zs);
    const maxZ = Math.max(...zs);

    const rangeX = maxX - minX || 1;
    const rangeY = maxY - minY || 1;
    const rangeZ = maxZ - minZ || 1;

    return pts.map(p => ({
      x: ((p.x - minX) / rangeX - 0.5) * SPACE_SCALE,
      y: ((p.y - minY) / rangeY - 0.5) * SPACE_SCALE,
      z: ((p.z - minZ) / rangeZ - 0.5) * SPACE_SCALE,
    }));
  }

  function buildSpace() {
    if (!scene) return;

    if (pointsMesh) {
      scene.remove(pointsMesh);
      pointsMesh.geometry.dispose();
      (pointsMesh.material as THREE.Material).dispose();
    }
    if (haloMesh) {
      scene.remove(haloMesh);
      haloMesh.geometry.dispose();
      (haloMesh.material as THREE.Material).dispose();
    }

    if (points.length === 0) return;

    pointPositions = [];
    const normalized = normalizeCoords(points);
    const positions: number[] = [];
    const colors: number[] = [];

    normalized.forEach((coord, index) => {
      positions.push(coord.x, coord.y, coord.z);
      const hex = points[index].color || getStoryTypeColor(points[index].story_type);
      const color = new THREE.Color(hex);
      colors.push(color.r, color.g, color.b);
      pointPositions.push(new THREE.Vector3(coord.x, coord.y, coord.z));
    });

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
    geometry.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));

    const coreMaterial = new THREE.PointsMaterial({
      size: 1.6,
      vertexColors: true,
      transparent: true,
      opacity: 1.0,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
    });

    pointsMesh = new THREE.Points(geometry, coreMaterial);
    scene.add(pointsMesh);

    const haloGeometry = new THREE.BufferGeometry();
    haloGeometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
    haloGeometry.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));

    if (!glowTexture) {
      glowTexture = createGlowTexture();
    }
    const haloMaterial = new THREE.PointsMaterial({
      size: 6.4,
      map: glowTexture || undefined,
      vertexColors: true,
      transparent: true,
      opacity: 0.5,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
      sizeAttenuation: false,
    });

    haloMesh = new THREE.Points(haloGeometry, haloMaterial);
    scene.add(haloMesh);
  }

  function buildWireframe() {
    if (!scene) return;
    if (wireframe) {
      scene.remove(wireframe);
      wireframe.geometry.dispose();
      (wireframe.material as THREE.Material).dispose();
    }

    const geometry = new THREE.BoxGeometry(SPACE_SCALE * 1.05, SPACE_SCALE * 1.05, SPACE_SCALE * 1.05);
    const edges = new THREE.EdgesGeometry(geometry);
    const material = new THREE.LineBasicMaterial({ color: 0x5eead4, transparent: true, opacity: 0.25 });
    wireframe = new THREE.LineSegments(edges, material);
    scene.add(wireframe);
  }

  function buildHoverMarker() {
    if (!scene) return;
    if (hoverMarker) {
      scene.remove(hoverMarker);
      hoverMarker.geometry.dispose();
      (hoverMarker.material as THREE.Material).dispose();
    }
    const geometry = new THREE.RingGeometry(1.6, 2.4, 32);
    const material = new THREE.MeshBasicMaterial({
      color: 0xffffff,
      transparent: true,
      opacity: 0.0,
      side: THREE.DoubleSide,
      blending: THREE.AdditiveBlending,
    });
    hoverMarker = new THREE.Mesh(geometry, material);
    hoverMarker.visible = false;
    scene.add(hoverMarker);
  }

  function initScene() {
    scene = new THREE.Scene();
    scene.background = new THREE.Color('#060b1a');
    scene.fog = new THREE.FogExp2(0x060b1a, 0.009);

    camera = new THREE.PerspectiveCamera(60, container.clientWidth / container.clientHeight, 0.1, 600);
    camera.position.set(0, 40, 140);

    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'high-performance' });
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.2;
    container.appendChild(renderer.domElement);

    composer = new EffectComposer(renderer);
    composer.addPass(new RenderPass(scene, camera));

    // Conditional bloom based on performance mode
    const device = detectDevice();
    const settings = getOptimalSettings(device);

    // Check for query param override (dev mode)
    const urlParams = new URLSearchParams(window.location.search);
    const bloomOverride = urlParams.get('bloom');
    const shouldBloom = bloomOverride !== null
      ? bloomOverride === 'true'
      : settings.bloomEnabled;

    if (shouldBloom) {
      const bloomPass = new UnrealBloomPass(
        new THREE.Vector2(container.clientWidth, container.clientHeight),
        2.0, // Increased strength
        0.8, // Increased radius
        0.3  // Increased threshold
      );
      composer.addPass(bloomPass);
    }

    controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.15; // Smoother damping for touch
    controls.minDistance = 70;
    controls.maxDistance = 220;
    controls.autoRotate = true;
    controls.autoRotateSpeed = 0.4;

    // Touch controls (two-finger rotation and pinch work automatically)
    controls.touches = {
      ONE: THREE.TOUCH.ROTATE,
      TWO: THREE.TOUCH.DOLLY_PAN
    };

    raycaster = new THREE.Raycaster();
    raycaster.params.Points = { threshold: 1.2 };

    const ambient = new THREE.AmbientLight(0xbfe8ff, 0.55);
    scene.add(ambient);

    const hemi = new THREE.HemisphereLight(0x5eead4, 0x020617, 0.35);
    scene.add(hemi);

    const keyLight = new THREE.DirectionalLight(0xffffff, 1.0);
    keyLight.position.set(30, 60, 40);
    scene.add(keyLight);

    const rimLight = new THREE.PointLight(0x5eead4, 1.7, 240);
    rimLight.position.set(-40, -20, -40);
    scene.add(rimLight);

    if (!nebulaTexture) {
      nebulaTexture = createNebulaTexture();
    }
    if (nebulaTexture) {
      const sphere = new THREE.Mesh(
        new THREE.SphereGeometry(220, 32, 32),
        new THREE.MeshBasicMaterial({ map: nebulaTexture, side: THREE.BackSide, transparent: true, opacity: 0.9 })
      );
      scene.add(sphere);
    }

    buildWireframe();
    buildHoverMarker();
  }

  function updateScenePoints() {
    if (!scene) return;
    buildSpace();
  }

  function onResize() {
    if (!renderer || !camera || !composer) return;
    camera.aspect = container.clientWidth / container.clientHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(container.clientWidth, container.clientHeight);
    composer.setSize(container.clientWidth, container.clientHeight);
  }

  function updateHover(event: MouseEvent) {
    if (!raycaster || !camera || !pointsMesh || !hoverMarker) return;
    const rect = container.getBoundingClientRect();
    mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
    raycaster.setFromCamera(mouse, camera);

    const hits = raycaster.intersectObject(pointsMesh);
    if (hits.length > 0 && hits[0].index !== undefined) {
      hoveredIndex = hits[0].index;
      const point = points[hoveredIndex];
      tooltip = {
        x: event.clientX - rect.left,
        y: event.clientY - rect.top,
        point,
      };
      container.style.cursor = 'pointer';

      const pos = pointPositions[hoveredIndex];
      hoverMarker.visible = true;
      hoverMarker.position.copy(pos);
      const hoverMaterial = hoverMarker.material as THREE.MeshBasicMaterial;
      hoverMaterial.opacity = 0.85;
      const hoverHex = point.color || getStoryTypeColor(point.story_type);
      hoverMaterial.color.set(hoverHex);
    } else {
      hoveredIndex = null;
      tooltip = null;
      container.style.cursor = 'grab';
      hoverMarker.visible = false;
    }
  }

  function handleClick() {
    if (hoveredIndex !== null && onPointClick) {
      onPointClick(points[hoveredIndex]);
    }
  }

  function handleMouseLeave() {
    tooltip = null;
    hoveredIndex = null;
    if (hoverMarker) hoverMarker.visible = false;
    container.style.cursor = 'grab';
  }

  function animate() {
    animationId = requestAnimationFrame(animate);
    if (!scene || !camera || !composer) return;

    const elapsed = clock.getElapsedTime();
    if (controls) controls.update();

    if (haloMesh) {
      const material = haloMesh.material as THREE.PointsMaterial;
      material.size = 5.1 + Math.sin(elapsed * 1.4) * 0.6;
    }

    if (hoverMarker && hoverMarker.visible) {
      const pulse = 1 + Math.sin(elapsed * 5) * 0.22;
      hoverMarker.scale.set(pulse, pulse, pulse);
      hoverMarker.lookAt(camera.position);
    }

    composer.render();
  }

  // Touch gesture state
  let touchData = {
    initialDistance: 0,
    lastTapTime: 0,
    longPressTimer: null as ReturnType<typeof setTimeout> | null,
    touchStartPos: { x: 0, y: 0 },
  };

  // Touch handlers for enhanced mobile support
  function handleTouchStart(event: TouchEvent) {
    const touches = event.touches;

    if (touches.length === 1) {
      const touch = touches[0];
      touchData.touchStartPos = { x: touch.clientX, y: touch.clientY };

      touchData.longPressTimer = setTimeout(() => {
        handleLongPress(touch);
      }, 500);
    } else if (touches.length === 2) {
      const dx = touches[1].clientX - touches[0].clientX;
      const dy = touches[1].clientY - touches[0].clientY;
      touchData.initialDistance = Math.sqrt(dx * dx + dy * dy);

      if (touchData.longPressTimer) {
        clearTimeout(touchData.longPressTimer);
        touchData.longPressTimer = null;
      }
    }
  }

  function handleTouchMove(event: TouchEvent) {
    if (touchData.longPressTimer) {
      clearTimeout(touchData.longPressTimer);
      touchData.longPressTimer = null;
    }
  }

  function handleTouchEnd(event: TouchEvent) {
    if (touchData.longPressTimer) {
      clearTimeout(touchData.longPressTimer);
      touchData.longPressTimer = null;
    }

    const touch = event.changedTouches[0];
    if (!touch) return;

    const endX = touch.clientX;
    const endY = touch.clientY;
    const distance = Math.sqrt(
      Math.pow(endX - touchData.touchStartPos.x, 2) +
      Math.pow(endY - touchData.touchStartPos.y, 2)
    );

    if (distance < 10) {
      const now = Date.now();
      const timeSinceLast = now - touchData.lastTapTime;

      if (timeSinceLast < 300) {
        handleDoubleTap();
        touchData.lastTapTime = 0;
      } else {
        touchData.lastTapTime = now;
        handleTouchTap(touch);
      }
    }

    touchData.initialDistance = 0;
  }

  function handleLongPress(touch: Touch) {
    if (!raycaster || !camera || !pointsMesh) return;

    const rect = container.getBoundingClientRect();
    mouse.x = ((touch.clientX - rect.left) / rect.width) * 2 - 1;
    mouse.y = -((touch.clientY - rect.top) / rect.height) * 2 + 1;

    raycaster.setFromCamera(mouse, camera);
    const hits = raycaster.intersectObject(pointsMesh);

    if (hits.length > 0 && hits[0].index !== undefined) {
      const index = hits[0].index;
      haptics.medium();

      if (onPointClick) {
        onPointClick(points[index]);
      }
    }
  }

  function handleDoubleTap() {
    if (!camera || !controls) return;

    haptics.light();

    const startPos = camera.position.clone();
    const targetPos = new THREE.Vector3(0, 0, 150);

    const duration = 800;
    const startTime = Date.now();

    function animateReset() {
      const now = Date.now();
      const progress = Math.min((now - startTime) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);

      camera.position.lerpVectors(startPos, targetPos, eased);
      camera.lookAt(0, 0, 0);

      if (progress < 1) {
        requestAnimationFrame(animateReset);
      }
    }

    animateReset();
  }

  function handleTouchTap(touch: Touch) {
    if (!raycaster || !camera || !pointsMesh) return;

    const rect = container.getBoundingClientRect();
    mouse.x = ((touch.clientX - rect.left) / rect.width) * 2 - 1;
    mouse.y = -((touch.clientY - rect.top) / rect.height) * 2 + 1;

    raycaster.setFromCamera(mouse, camera);
    const hits = raycaster.intersectObject(pointsMesh);

    if (hits.length > 0 && hits[0].index !== undefined) {
      const index = hits[0].index;
      haptics.light();

      if (onPointClick) {
        onPointClick(points[index]);
      }
    }
  }

  onMount(() => {
    initScene();
    updateScenePoints();
    window.addEventListener('resize', onResize);
    container.addEventListener('mousemove', updateHover);
    container.addEventListener('mouseleave', handleMouseLeave);

    // Touch event listeners
    container.addEventListener('touchstart', handleTouchStart, { passive: false });
    container.addEventListener('touchmove', handleTouchMove, { passive: false });
    container.addEventListener('touchend', handleTouchEnd, { passive: true });

    animate();
  });

  onDestroy(() => {
    if (animationId !== null) cancelAnimationFrame(animationId);

    // Clean up long-press timer
    if (touchData.longPressTimer) {
      clearTimeout(touchData.longPressTimer);
    }

    window.removeEventListener('resize', onResize);
    container?.removeEventListener('mousemove', updateHover);
    container?.removeEventListener('mouseleave', handleMouseLeave);

    // Remove touch listeners
    container?.removeEventListener('touchstart', handleTouchStart);
    container?.removeEventListener('touchmove', handleTouchMove);
    container?.removeEventListener('touchend', handleTouchEnd);

    controls?.dispose();
    renderer?.dispose();
    composer?.dispose();

    if (pointsMesh) {
      pointsMesh.geometry.dispose();
      (pointsMesh.material as THREE.Material).dispose();
    }
    if (haloMesh) {
      haloMesh.geometry.dispose();
      (haloMesh.material as THREE.Material).dispose();
    }
    if (wireframe) {
      wireframe.geometry.dispose();
      (wireframe.material as THREE.Material).dispose();
    }
    if (hoverMarker) {
      hoverMarker.geometry.dispose();
      (hoverMarker.material as THREE.Material).dispose();
    }

    glowTexture?.dispose();
    nebulaTexture?.dispose();

    if (renderer && renderer.domElement && renderer.domElement.parentNode) {
      renderer.domElement.parentNode.removeChild(renderer.domElement);
    }
  });

  $effect(() => {
    if (scene) updateScenePoints();
  });
</script>

<!-- svelte-ignore a11y_click_events_have_key_events -->
<!-- svelte-ignore a11y_no_static_element_interactions -->
<div class="relative w-full h-full" bind:this={container} onclick={handleClick}>
  {#if points.length === 0}
    <div class="absolute inset-0 flex items-center justify-center">
      <div class="text-center px-8 max-w-sm">
        <div class="w-16 h-16 mx-auto mb-4 rounded-2xl bg-slate-800/50 flex items-center justify-center">
          <svg class="w-8 h-8 text-slate-500" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 3v11.25A2.25 2.25 0 006 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0118 16.5h-2.25m-7.5 0h7.5m-7.5 0l-1 3m8.5-3l1 3m0 0l.5 1.5m-.5-1.5h-9.5m0 0l-.5 1.5M9 11.25v1.5M12 9v3.75m3-6v6" />
          </svg>
        </div>
        <h2 class="text-lg font-semibold text-slate-200 mb-2">Vector Space</h2>
        <p class="text-sm text-slate-500 leading-relaxed">
          Semantic embeddings haven't been generated yet. Once computed, you'll be able to explore stories in 3D space where similar experiences cluster together.
        </p>
      </div>
    </div>
  {:else}
    <div class="absolute bottom-4 left-4 px-3 py-2 bg-slate-950/80 backdrop-blur-md rounded-lg border border-teal-300/30 text-xs text-teal-100 shadow-[0_0_20px_rgba(94,234,212,0.25)]">
      Drag to orbit - Scroll to zoom - Click to inspect
    </div>

    {#if tooltip}
      <div
        class="absolute z-10 px-3 py-2 bg-slate-950/90 backdrop-blur-md border border-teal-300/40 rounded-lg shadow-[0_0_24px_rgba(45,212,191,0.35)] pointer-events-none max-w-[280px]"
        style="left: {tooltip.x + 12}px; top: {tooltip.y + 12}px;"
      >
        <div class="font-medium text-sm text-white">{tooltip.point.title}</div>
        {#if tooltip.point.story_type}
          <div class="flex items-center gap-1.5 mt-1">
            <span
              class="w-2 h-2 rounded-full"
              style="background-color: {getStoryTypeColor(tooltip.point.story_type)}"
            ></span>
            <span class="text-xs text-teal-100">{formatStoryType(tooltip.point.story_type)}</span>
          </div>
        {/if}
      </div>
    {/if}
  {/if}
</div>
