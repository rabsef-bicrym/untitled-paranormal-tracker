<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import * as THREE from 'three';
  import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls';
  import usStates from '$lib/assets/us-states.json';
  import reliefUrl from '$lib/assets/ne_gray_relief_2048.png';

  type GeoJSONGeometry =
    | { type: 'Polygon'; coordinates: number[][][] }
    | { type: 'MultiPolygon'; coordinates: number[][][][] };

  type GeoJSONFeature = {
    type: 'Feature';
    properties?: { name?: string };
    geometry: GeoJSONGeometry;
  };

  type GeoJSONCollection = {
    type: 'FeatureCollection';
    features: GeoJSONFeature[];
  };

  const STATES = usStates as GeoJSONCollection;
  const EXCLUDED = new Set(['Alaska', 'Hawaii', 'Puerto Rico']);

  // Map dimensions
  const MAP_WIDTH = 140;
  const MAP_HEIGHT = 84;

  // Hexagon grid settings
  const HEX_RADIUS = 0.8;  // Size of each hexagon
  const HEX_SPACING = HEX_RADIUS * 1.73; // Hex width (sqrt(3) * radius)

  // Height settings
  const MIN_HEIGHT = 0.3;
  const MAX_HEIGHT = 3;

  // Color palette (purple -> pink -> orange -> yellow)
  const PALETTE = [
    new THREE.Color(0x1a0728),  // Deep purple
    new THREE.Color(0x3b0a5a),  // Purple
    new THREE.Color(0x7c3aed),  // Bright purple
    new THREE.Color(0xec4899),  // Pink
    new THREE.Color(0xf97316),  // Orange
    new THREE.Color(0xfbbf24),  // Yellow
  ];

  let container: HTMLDivElement;
  let scene: THREE.Scene;
  let camera: THREE.PerspectiveCamera;
  let renderer: THREE.WebGLRenderer;
  let controls: OrbitControls;
  let animationId: number;

  let maskData: Uint8ClampedArray | null = null;
  let maskWidth = 0;
  let maskHeight = 0;
  let borderData: Uint8ClampedArray | null = null;
  let borderWidth = 0;
  let borderHeight = 0;
  let heightData: Uint8ClampedArray | null = null;
  let heightWidth = 0;
  let heightHeight = 0;

  // Compute bounds for contiguous US
  function computeBounds(features: GeoJSONFeature[]) {
    let minLng = Infinity, maxLng = -Infinity;
    let minLat = Infinity, maxLat = -Infinity;

    const visit = (coords: number[]) => {
      const [lng, lat] = coords;
      if (lng < minLng) minLng = lng;
      if (lng > maxLng) maxLng = lng;
      if (lat < minLat) minLat = lat;
      if (lat > maxLat) maxLat = lat;
    };

    features.forEach((feature) => {
      const name = feature.properties?.name;
      if (name && EXCLUDED.has(name)) return;

      if (feature.geometry.type === 'Polygon') {
        feature.geometry.coordinates.forEach((ring) => ring.forEach(visit));
      } else {
        feature.geometry.coordinates.forEach((poly) =>
          poly.forEach((ring) => ring.forEach(visit))
        );
      }
    });

    return { minLng, maxLng, minLat, maxLat };
  }

  const BOUNDS = computeBounds(STATES.features);

  // Build mask canvas to check if point is in contiguous US
  function buildMaskCanvas(width: number, height: number) {
    const canvas = document.createElement('canvas');
    canvas.width = width;
    canvas.height = height;
    const ctx = canvas.getContext('2d');
    if (!ctx) return null;

    ctx.fillStyle = 'black';
    ctx.fillRect(0, 0, width, height);
    ctx.fillStyle = 'white';

    STATES.features.forEach((feature) => {
      const name = feature.properties?.name;
      if (name && EXCLUDED.has(name)) return;

      const drawRings = (rings: number[][][]) => {
        ctx.beginPath();
        rings.forEach((ring) => {
          if (ring.length < 2) return;
          ring.forEach(([lng, lat], i) => {
            const x = ((lng - BOUNDS.minLng) / (BOUNDS.maxLng - BOUNDS.minLng)) * width;
            const y = height - ((lat - BOUNDS.minLat) / (BOUNDS.maxLat - BOUNDS.minLat)) * height;
            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
          });
          ctx.closePath();
        });
        ctx.fill('evenodd');
      };

      if (feature.geometry.type === 'Polygon') {
        drawRings(feature.geometry.coordinates);
      } else {
        feature.geometry.coordinates.forEach(drawRings);
      }
    });

    return canvas;
  }

  // Initialize mask data
  function ensureMaskData() {
    if (maskData) return;
    const width = 960;
    const height = 576;
    const maskCanvas = buildMaskCanvas(width, height);
    if (!maskCanvas) return;
    const ctx = maskCanvas.getContext('2d');
    if (!ctx) return;
    const image = ctx.getImageData(0, 0, width, height);
    maskData = image.data;
    maskWidth = width;
    maskHeight = height;

  }

  // Check if UV coordinate is inside contiguous US
  function isLand(u: number, v: number) {
    if (!maskData) return false;
    const x = Math.min(maskWidth - 1, Math.max(0, Math.floor(u * maskWidth)));
    const y = Math.min(maskHeight - 1, Math.max(0, Math.floor(v * maskHeight)));
    const idx = (y * maskWidth + x) * 4;
    // Check red channel (it's white on black, so R should be 255 for land)
    const r = maskData[idx];
    return r > 128;
  }

  // Check if UV coordinate is on a state border
  function isOnBorder(u: number, v: number) {
    if (!borderData) return false;
    const x = Math.min(borderWidth - 1, Math.max(0, Math.floor(u * borderWidth)));
    const y = Math.min(borderHeight - 1, Math.max(0, Math.floor(v * borderHeight)));
    const idx = (y * borderWidth + x) * 4;
    const r = borderData[idx];
    return r < 128; // Black pixels are borders
  }

  // Build border mask canvas
  function buildBorderCanvas(width: number, height: number) {
    const canvas = document.createElement('canvas');
    canvas.width = width;
    canvas.height = height;
    const ctx = canvas.getContext('2d');
    if (!ctx) return null;

    ctx.fillStyle = 'white';
    ctx.fillRect(0, 0, width, height);
    ctx.strokeStyle = 'black';
    ctx.lineWidth = 8; // Thicker lines = wider gaps between states

    STATES.features.forEach((feature) => {
      const name = feature.properties?.name;
      if (name && EXCLUDED.has(name)) return;

      const drawRings = (rings: number[][][]) => {
        rings.forEach((ring) => {
          if (ring.length < 2) return;
          ctx.beginPath();
          ring.forEach(([lng, lat], i) => {
            const x = ((lng - BOUNDS.minLng) / (BOUNDS.maxLng - BOUNDS.minLng)) * width;
            const y = height - ((lat - BOUNDS.minLat) / (BOUNDS.maxLat - BOUNDS.minLat)) * height;
            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
          });
          ctx.closePath();
          ctx.stroke();
        });
      };

      if (feature.geometry.type === 'Polygon') {
        drawRings(feature.geometry.coordinates);
      } else {
        feature.geometry.coordinates.forEach(drawRings);
      }
    });

    return canvas;
  }

  // Initialize border data
  function ensureBorderData() {
    if (borderData) return;
    const width = 960;
    const height = 576;
    const borderCanvas = buildBorderCanvas(width, height);
    if (!borderCanvas) return;
    const ctx = borderCanvas.getContext('2d');
    if (!ctx) return;
    const image = ctx.getImageData(0, 0, width, height);
    borderData = image.data;
    borderWidth = width;
    borderHeight = height;
  }

  // Load heightmap texture
  async function loadHeightmap() {
    if (heightData) return;
    const image = new Image();
    image.src = reliefUrl;
    await image.decode();

    const canvas = document.createElement('canvas');
    canvas.width = image.width;
    canvas.height = image.height;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.drawImage(image, 0, 0);
    const imgData = ctx.getImageData(0, 0, canvas.width, canvas.height);
    heightData = imgData.data;
    heightWidth = canvas.width;
    heightHeight = canvas.height;
  }

  // Sample height at lat/lng
  function sampleHeight(lng: number, lat: number): number {
    if (!heightData) return 0;
    const u = (lng + 180) / 360;
    const v = (90 - lat) / 180;
    const x = Math.min(heightWidth - 1, Math.max(0, Math.floor(u * heightWidth)));
    const y = Math.min(heightHeight - 1, Math.max(0, Math.floor(v * heightHeight)));
    const idx = (y * heightWidth + x) * 4;
    return heightData[idx] / 255;
  }

  // Get color from height value (0-1)
  function colorFromHeight(h: number): THREE.Color {
    const clamped = Math.max(0, Math.min(1, h));
    const scaled = clamped * (PALETTE.length - 1);
    const idx = Math.floor(scaled);
    const next = Math.min(idx + 1, PALETTE.length - 1);
    const t = scaled - idx;
    return PALETTE[idx].clone().lerp(PALETTE[next], t);
  }

  // Create hexagon geometry (flat-top orientation)
  function createHexGeometry(radius: number, height: number) {
    const shape = new THREE.Shape();
    for (let i = 0; i < 6; i++) {
      const angle = (Math.PI / 3) * i;
      const x = radius * Math.cos(angle);
      const y = radius * Math.sin(angle);
      if (i === 0) shape.moveTo(x, y);
      else shape.lineTo(x, y);
    }
    shape.closePath();

    const extrudeSettings = {
      depth: height,
      bevelEnabled: false,
    };

    return new THREE.ExtrudeGeometry(shape, extrudeSettings);
  }

  // Build hexagonal grid
  function buildHexGrid() {
    if (!scene || !maskData || !heightData || !borderData) return;

    ensureMaskData();
    ensureBorderData();

    const hexGroup = new THREE.Group();

    // Calculate grid dimensions
    const hexWidth = HEX_SPACING;
    const hexHeight = HEX_RADIUS * 1.5;
    const cols = Math.ceil(MAP_WIDTH / hexWidth) + 2;
    const rows = Math.ceil(MAP_HEIGHT / hexHeight) + 2;

    for (let row = 0; row < rows; row++) {
      for (let col = 0; col < cols; col++) {
        // Hexagon offset grid (every other row is offset)
        const xOffset = (row % 2) * (hexWidth / 2);
        const x = col * hexWidth + xOffset - MAP_WIDTH / 2;
        const z = row * hexHeight - MAP_HEIGHT / 2;

        // Convert to UV coordinates
        const u = (x + MAP_WIDTH / 2) / MAP_WIDTH;
        const v = (z + MAP_HEIGHT / 2) / MAP_HEIGHT;

        // Skip if outside contiguous US
        const land = isLand(u, v);
        if (!land) continue;

        const onBorder = isOnBorder(u, v);

        let geometry, material, heightValue;

        if (onBorder) {
          // Create a low, dull white hex for state borders
          heightValue = 0.15;
          geometry = createHexGeometry(HEX_RADIUS * 0.75, heightValue);
          material = new THREE.MeshBasicMaterial({
            color: new THREE.Color(0x2a2a2a), // Dark gray
            transparent: true,
            opacity: 0.8
          });
        } else {
          // Get lat/lng
          const lng = BOUNDS.minLng + u * (BOUNDS.maxLng - BOUNDS.minLng);
          const lat = BOUNDS.maxLat - v * (BOUNDS.maxLat - BOUNDS.minLat);

          // Sample elevation
          const elevation = sampleHeight(lng, lat);
          heightValue = MIN_HEIGHT + elevation * (MAX_HEIGHT - MIN_HEIGHT);

          // Create hexagon with gap between them
          geometry = createHexGeometry(HEX_RADIUS * 0.75, heightValue);
          const color = colorFromHeight(elevation);
          material = new THREE.MeshBasicMaterial({
            color,
            transparent: true,
            opacity: 0.9
          });
        }

        const hex = new THREE.Mesh(geometry, material);
        hex.position.set(x, 0, z);
        hex.rotation.x = -Math.PI / 2; // Lay flat

        hexGroup.add(hex);
      }
    }

    scene.add(hexGroup);
  }

  // Setup Three.js scene
  function setupScene() {
    if (!container) return;

    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0a0a0a);

    camera = new THREE.PerspectiveCamera(
      55,
      container.clientWidth / container.clientHeight,
      0.1,
      500
    );
    camera.position.set(0, 80, 100);
    camera.lookAt(0, 0, 0);

    renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    container.appendChild(renderer.domElement);

    controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.minDistance = 50;
    controls.maxDistance = 200;

    const ambient = new THREE.AmbientLight(0xffffff, 1);
    scene.add(ambient);

    buildHexGrid();
  }

  function handleResize() {
    if (!camera || !renderer || !container) return;
    camera.aspect = container.clientWidth / container.clientHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(container.clientWidth, container.clientHeight);
  }

  function animate() {
    animationId = requestAnimationFrame(animate);
    controls?.update();
    renderer?.render(scene, camera);
  }

  onMount(async () => {
    await loadHeightmap();
    ensureMaskData();
    ensureBorderData();
    setupScene();
    window.addEventListener('resize', handleResize);
    animate();
  });

  onDestroy(() => {
    if (animationId) cancelAnimationFrame(animationId);
    window.removeEventListener('resize', handleResize);
    controls?.dispose();
    renderer?.dispose();
    scene?.traverse((object) => {
      if (object instanceof THREE.Mesh) {
        object.geometry?.dispose();
        if (object.material instanceof THREE.Material) {
          object.material.dispose();
        }
      }
    });
    if (renderer?.domElement?.parentNode) {
      renderer.domElement.parentNode.removeChild(renderer.domElement);
    }
  });
</script>

<div class="relative w-full h-full overflow-hidden" bind:this={container}></div>
