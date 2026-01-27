<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import * as THREE from 'three';
  import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls';

  // Globe settings
  const GLOBE_RADIUS = 50;
  const HEX_HEIGHT = 0.3; // All hexes same height
  const HEX_RADIUS = 0.6;

  // Color palette
  const PALETTE = [
    new THREE.Color(0x1a0728),
    new THREE.Color(0x3b0a5a),
    new THREE.Color(0x7c3aed),
    new THREE.Color(0xec4899),
    new THREE.Color(0xf97316),
    new THREE.Color(0xfbbf24),
  ];

  let container: HTMLDivElement;
  let scene: THREE.Scene;
  let camera: THREE.PerspectiveCamera;
  let renderer: THREE.WebGLRenderer;
  let controls: OrbitControls;
  let animationId: number;

  // Wave animation state
  const BERMUDA_LAT = 25.0;
  const BERMUDA_LNG = -71.0;
  const WAVE_INTERVAL = 45000; // 45 seconds
  const WAVE_DURATION = 8000; // 8 seconds to travel
  const WAVE_SPEED = 180; // degrees per wave duration
  let lastWaveTime = Date.now();
  let waveActive = false;
  let waveStartTime = 0;

  // Store ocean hexes for wave animation
  type OceanHex = {
    mesh: THREE.Mesh;
    material: THREE.MeshBasicMaterial;
    lat: number;
    lng: number;
    baseY: number;
    baseColor: THREE.Color;
  };
  let oceanHexes: OceanHex[] = [];

  let borderData: Uint8ClampedArray | null = null;
  let borderWidth = 0;
  let borderHeight = 0;
  let landData: Uint8ClampedArray | null = null;
  let landWidth = 0;
  let landHeight = 0;

  const OCEAN_COLOR = new THREE.Color(0x001a4d); // Dark deep blue
  const BORDER_COLOR = new THREE.Color(0x505050); // Lighter gray for visibility

  // Convert lat/lng to 3D position on sphere
  function latLngToVector3(lat: number, lng: number, radius: number): THREE.Vector3 {
    const phi = (90 - lat) * (Math.PI / 180);
    const theta = (lng + 180) * (Math.PI / 180);

    const x = -radius * Math.sin(phi) * Math.cos(theta);
    const y = radius * Math.cos(phi);
    const z = radius * Math.sin(phi) * Math.sin(theta);

    return new THREE.Vector3(x, y, z);
  }

  // Calculate angular distance between two lat/lng points (in degrees)
  function angularDistance(lat1: number, lng1: number, lat2: number, lng2: number): number {
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLng = (lng2 - lng1) * Math.PI / 180;
    const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
              Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
              Math.sin(dLng / 2) * Math.sin(dLng / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return c * 180 / Math.PI; // Return in degrees
  }

  // Create hexagon geometry
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

  // Load world GeoJSON and create land/border masks
  async function loadBorders() {
    // Fetch world countries GeoJSON
    const response = await fetch('https://raw.githubusercontent.com/datasets/geo-countries/master/data/countries.geojson');
    const geojson = await response.json();

    const width = 1800;
    const height = 900;

    // Create land mask (white = land, black = ocean)
    const landCanvas = document.createElement('canvas');
    landCanvas.width = width;
    landCanvas.height = height;
    const landCtx = landCanvas.getContext('2d');
    if (!landCtx) return;

    landCtx.fillStyle = 'black'; // Ocean
    landCtx.fillRect(0, 0, width, height);
    landCtx.fillStyle = 'white'; // Land

    // Create border mask (white = interior, black = border)
    const borderCanvas = document.createElement('canvas');
    borderCanvas.width = width;
    borderCanvas.height = height;
    const borderCtx = borderCanvas.getContext('2d');
    if (!borderCtx) return;

    borderCtx.fillStyle = 'white';
    borderCtx.fillRect(0, 0, width, height);
    borderCtx.strokeStyle = 'black';
    borderCtx.lineWidth = 6;

    // Draw each country
    geojson.features.forEach((feature: any) => {
      const drawPolygon = (coords: number[][][]) => {
        coords.forEach((ring: number[][]) => {
          if (ring.length < 2) return;

          // Draw filled polygon for land mask
          landCtx.beginPath();
          ring.forEach(([lng, lat]: number[], i: number) => {
            const x = ((lng + 180) / 360) * width;
            const y = ((90 - lat) / 180) * height;
            if (i === 0) landCtx.moveTo(x, y);
            else landCtx.lineTo(x, y);
          });
          landCtx.closePath();
          landCtx.fill();

          // Draw outline for border mask
          borderCtx.beginPath();
          ring.forEach(([lng, lat]: number[], i: number) => {
            const x = ((lng + 180) / 360) * width;
            const y = ((90 - lat) / 180) * height;
            if (i === 0) borderCtx.moveTo(x, y);
            else borderCtx.lineTo(x, y);
          });
          borderCtx.closePath();
          borderCtx.stroke();
        });
      };

      if (feature.geometry.type === 'Polygon') {
        drawPolygon(feature.geometry.coordinates);
      } else if (feature.geometry.type === 'MultiPolygon') {
        feature.geometry.coordinates.forEach(drawPolygon);
      }
    });

    // Extract land mask data
    const landImgData = landCtx.getImageData(0, 0, width, height);
    landData = landImgData.data;
    landWidth = width;
    landHeight = height;

    // Extract border mask data
    const borderImgData = borderCtx.getImageData(0, 0, width, height);
    borderData = borderImgData.data;
    borderWidth = width;
    borderHeight = height;
  }

  // Check if lat/lng is on land
  function isLand(lat: number, lng: number): boolean {
    if (!landData) return false;
    const x = Math.floor(((lng + 180) / 360) * landWidth);
    const y = Math.floor(((90 - lat) / 180) * landHeight);
    const clampedX = Math.min(landWidth - 1, Math.max(0, x));
    const clampedY = Math.min(landHeight - 1, Math.max(0, y));
    const idx = (clampedY * landWidth + clampedX) * 4;
    const r = landData[idx];
    return r > 128; // White = land
  }

  // Check if lat/lng is on a border
  function isOnBorder(lat: number, lng: number): boolean {
    if (!borderData) return false;
    const x = Math.floor(((lng + 180) / 360) * borderWidth);
    const y = Math.floor(((90 - lat) / 180) * borderHeight);
    const clampedX = Math.min(borderWidth - 1, Math.max(0, x));
    const clampedY = Math.min(borderHeight - 1, Math.max(0, y));
    const idx = (clampedY * borderWidth + clampedX) * 4;
    const r = borderData[idx];
    return r < 128; // Black = border
  }

  // Get color based on latitude (just for variety)
  function colorFromLatitude(lat: number): THREE.Color {
    const normalized = (lat + 90) / 180; // 0 to 1
    const scaled = normalized * (PALETTE.length - 1);
    const idx = Math.floor(scaled);
    const next = Math.min(idx + 1, PALETTE.length - 1);
    const t = scaled - idx;
    return PALETTE[idx].clone().lerp(PALETTE[next], t);
  }

  // Build hexagonal globe with latitude compensation
  function buildHexGlobe() {
    if (!scene || !borderData || !landData) return;

    const hexGroup = new THREE.Group();
    oceanHexes = []; // Reset ocean hexes array

    // Target hex spacing at equator (in degrees)
    const targetSpacing = 1.7;
    const latStep = targetSpacing;

    for (let lat = -90; lat <= 90; lat += latStep) {
      // Calculate circumference at this latitude
      const latRad = (lat * Math.PI) / 180;
      const radius = Math.cos(latRad) * GLOBE_RADIUS;
      const circumference = 2 * Math.PI * radius;

      // Skip if we're too close to poles (radius too small)
      if (Math.abs(lat) > 85) continue;

      // Calculate how many hexes fit around this latitude
      const hexSpacing = (targetSpacing * Math.PI / 180) * GLOBE_RADIUS;
      const numHexes = Math.max(6, Math.round(circumference / hexSpacing));

      // Longitude step for this latitude
      const lngStep = 360 / numHexes;

      // Offset every other row
      const lngOffset = (Math.floor(lat / latStep) % 2) * (lngStep / 2);

      for (let i = 0; i < numHexes; i++) {
        const lng = (i * lngStep + lngOffset) - 180;

        const land = isLand(lat, lng);
        const onBorder = land && isOnBorder(lat, lng);

        let geometry, material;

        if (onBorder) {
          // Border hex - lighter gray for visibility
          geometry = createHexGeometry(HEX_RADIUS * 0.8, HEX_HEIGHT * 0.5);
          material = new THREE.MeshBasicMaterial({
            color: BORDER_COLOR,
            transparent: true,
            opacity: 0.8
          });
        } else if (!land) {
          // Ocean hex - deep neon blue
          geometry = createHexGeometry(HEX_RADIUS * 0.8, HEX_HEIGHT);
          material = new THREE.MeshBasicMaterial({
            color: OCEAN_COLOR.clone(),
            transparent: true,
            opacity: 0.9
          });
        } else {
          // Land hex - colored by latitude
          geometry = createHexGeometry(HEX_RADIUS * 0.8, HEX_HEIGHT);
          const color = colorFromLatitude(lat);
          material = new THREE.MeshBasicMaterial({
            color,
            transparent: true,
            opacity: 0.9
          });
        }

        const hex = new THREE.Mesh(geometry, material);

        // Position on sphere
        const position = latLngToVector3(lat, lng, GLOBE_RADIUS);
        hex.position.copy(position);

        // Orient hex to point outward from sphere center
        hex.lookAt(0, 0, 0);
        hex.rotateX(Math.PI);

        hexGroup.add(hex);

        // Store ocean hexes for wave animation
        if (!land && !onBorder) {
          oceanHexes.push({
            mesh: hex,
            material: material as THREE.MeshBasicMaterial,
            lat,
            lng,
            baseY: position.length(),
            baseColor: OCEAN_COLOR.clone()
          });
        }
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
      45,
      container.clientWidth / container.clientHeight,
      0.1,
      500
    );
    camera.position.set(0, 0, 150);
    camera.lookAt(0, 0, 0);

    renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    container.appendChild(renderer.domElement);

    controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.minDistance = 80;
    controls.maxDistance = 250;
    controls.autoRotate = true;
    controls.autoRotateSpeed = 0.5;

    const ambient = new THREE.AmbientLight(0xffffff, 1);
    scene.add(ambient);

    buildHexGlobe();
  }

  function handleResize() {
    if (!camera || !renderer || !container) return;
    camera.aspect = container.clientWidth / container.clientHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(container.clientWidth, container.clientHeight);
  }

  function updateWave() {
    const now = Date.now();

    // Check if we should start a new wave
    if (!waveActive && now - lastWaveTime >= WAVE_INTERVAL) {
      waveActive = true;
      waveStartTime = now;
      lastWaveTime = now;
    }

    // Animate active wave
    if (waveActive) {
      const elapsed = now - waveStartTime;
      const progress = elapsed / WAVE_DURATION;

      if (progress >= 1.0) {
        // Wave finished, reset all ocean hexes
        waveActive = false;
        oceanHexes.forEach(({ mesh, material, baseY, baseColor }) => {
          const normal = mesh.position.clone().normalize();
          mesh.position.copy(normal.multiplyScalar(baseY));
          material.color.copy(baseColor);
        });
      } else {
        // Wave is active, animate hexes
        const currentDistance = progress * WAVE_SPEED;
        const waveThickness = 5; // degrees - about 3 hexes wide

        oceanHexes.forEach(({ mesh, material, lat, lng, baseY, baseColor }) => {
          const dist = angularDistance(BERMUDA_LAT, BERMUDA_LNG, lat, lng);

          // Check if this hex is in the wave ring
          if (dist >= currentDistance - waveThickness && dist <= currentDistance + waveThickness) {
            // Calculate position within wave ring (0 at edges, 1 at center)
            const ringPos = 1 - Math.abs(dist - currentDistance) / waveThickness;
            const waveHeight = ringPos * 1.0; // Max raise height - subtle
            const brighten = ringPos * 0.2; // Brighten amount - 20%

            // Raise hex
            const normal = mesh.position.clone().normalize();
            mesh.position.copy(normal.multiplyScalar(baseY + waveHeight));

            // Lighten color
            const brighterColor = baseColor.clone();
            brighterColor.r = Math.min(1, brighterColor.r + brighten);
            brighterColor.g = Math.min(1, brighterColor.g + brighten);
            brighterColor.b = Math.min(1, brighterColor.b + brighten);
            material.color.copy(brighterColor);
          } else if (dist < currentDistance - waveThickness) {
            // Wave has passed, reset to base
            const normal = mesh.position.clone().normalize();
            mesh.position.copy(normal.multiplyScalar(baseY));
            material.color.copy(baseColor);
          }
        });
      }
    }
  }

  function animate() {
    animationId = requestAnimationFrame(animate);
    updateWave();
    controls?.update();
    renderer?.render(scene, camera);
  }

  onMount(async () => {
    await loadBorders();
    setupScene();
    window.addEventListener('resize', handleResize);
    // Trigger first wave after 5 seconds
    lastWaveTime = Date.now() - WAVE_INTERVAL + 5000;
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
