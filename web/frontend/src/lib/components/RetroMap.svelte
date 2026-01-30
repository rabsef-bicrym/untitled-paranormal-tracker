<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { browser } from '$app/environment';
  import * as THREE from 'three';
  import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls';
  import type { MapStory } from '$lib/api';
  import MapClusterWindow from '$lib/components/MapClusterWindow.svelte';
  import * as haptics from '$lib/utils/haptics';
  import { getLODLevel } from '$lib/utils/performance';

  interface Props {
    stories?: MapStory[];
    onStoryClick?: (story: MapStory) => void;
  }

  let { stories = [], onStoryClick }: Props = $props();

  // Globe settings
  const GLOBE_RADIUS = 50;
  const BASE_HEX_HEIGHT = 0.3;
  const HEX_RADIUS = 0.6;
  const TOWER_HEIGHT_BASE = 2;
  const TOWER_HEIGHT_SCALE = 4;
  const FALLOFF_RADIUS = 5; // degrees
  const FALLOFF_SHARPNESS = 2; // Higher = steeper falloff

  // Muted base land colors (dark like ocean)
  const BASE_LAND_COLOR = new THREE.Color(0x1a1a2e);

  // Vibrant tower palette (purple → pink → orange → yellow)
  const TOWER_PALETTE = [
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
  let raycaster: THREE.Raycaster | null = null;
  const mouse = new THREE.Vector2();

  // UI state
  let hoveredTower: number | null = $state(null);
  let activeCluster: { stories: MapStory[]; count: number; position: { x: number; y: number } } | null = $state(null);
  let tooltip: { x: number; y: number; count: number } | null = $state(null);

  // Camera starting position
  const CAMERA_LAT = 43.0;
  const CAMERA_LNG = -55.0;
  const CAMERA_DISTANCE = 100;
  const CAMERA_OFFSET_X = 70;
  const CAMERA_OFFSET_Y = -140;

  // Dynamic offset for panning
  let currentOffsetX = $state(CAMERA_OFFSET_X);
  let currentOffsetY = $state(CAMERA_OFFSET_Y);

  // Story tower data
  type StoryTower = {
    lat: number;
    lng: number;
    count: number;
    height: number;
    stories: MapStory[];
  };
  let storyTowers: StoryTower[] = [];

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

  // Store land hexes for tower influence
  type LandHex = {
    mesh: THREE.Mesh;
    material: THREE.MeshBasicMaterial;
    lat: number;
    lng: number;
    baseY: number;
    baseHeight: number;
  };
  let landHexes: LandHex[] = [];

  // Store tower meshes for raycasting
  let towerMeshes: THREE.Mesh[] = [];
  let towerGroup: THREE.Group | null = null;

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

  // Cluster stories by proximity
  function clusterStories(stories: MapStory[]): StoryTower[] {
    if (!stories || stories.length === 0) return [];

    const clusters: StoryTower[] = [];
    const CLUSTER_RADIUS = 3; // degrees

    for (const story of stories) {
      // Find existing cluster within radius
      let foundCluster = false;
      for (const cluster of clusters) {
        const dist = angularDistance(cluster.lat, cluster.lng, story.lat, story.lng);
        if (dist < CLUSTER_RADIUS) {
          cluster.stories.push(story);
          cluster.count++;
          // Update cluster center (weighted average)
          cluster.lat = (cluster.lat * (cluster.count - 1) + story.lat) / cluster.count;
          cluster.lng = (cluster.lng * (cluster.count - 1) + story.lng) / cluster.count;
          foundCluster = true;
          break;
        }
      }

      // Create new cluster if no match
      if (!foundCluster) {
        clusters.push({
          lat: story.lat,
          lng: story.lng,
          count: 1,
          height: 0, // Will calculate after
          stories: [story]
        });
      }
    }

    // Calculate tower heights
    const maxCount = Math.max(...clusters.map(c => c.count), 1);
    clusters.forEach(cluster => {
      cluster.height = TOWER_HEIGHT_BASE + (cluster.count / maxCount) * TOWER_HEIGHT_SCALE;
    });

    return clusters;
  }

  // Get color from tower height (0 to max)
  function colorFromTowerHeight(height: number, maxHeight: number): THREE.Color {
    const normalized = Math.min(1, height / maxHeight);
    const scaled = normalized * (TOWER_PALETTE.length - 1);
    const idx = Math.floor(scaled);
    const next = Math.min(idx + 1, TOWER_PALETTE.length - 1);
    const t = scaled - idx;
    return TOWER_PALETTE[idx].clone().lerp(TOWER_PALETTE[next], t);
  }

  // Calculate influence of nearest tower on a hex
  function calculateTowerInfluence(hexLat: number, hexLng: number): { height: number; color: THREE.Color } | null {
    if (storyTowers.length === 0) return null;

    // Find nearest tower
    let minDist = Infinity;
    let nearestTower: StoryTower | null = null;

    for (const tower of storyTowers) {
      const dist = angularDistance(hexLat, hexLng, tower.lat, tower.lng);
      if (dist < minDist) {
        minDist = dist;
        nearestTower = tower;
      }
    }

    if (!nearestTower || minDist > FALLOFF_RADIUS) return null;

    // Calculate falloff (0 at FALLOFF_RADIUS, 1 at tower center)
    const falloff = Math.pow(1 - (minDist / FALLOFF_RADIUS), FALLOFF_SHARPNESS);

    const maxTowerHeight = Math.max(...storyTowers.map(t => t.height));
    const towerColor = colorFromTowerHeight(nearestTower.height, maxTowerHeight);

    return {
      height: nearestTower.height * falloff,
      color: BASE_LAND_COLOR.clone().lerp(towerColor, falloff)
    };
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


  // Build hexagonal globe with latitude compensation
  function buildHexGlobe() {
    if (!scene || !borderData || !landData) return;

    // Cluster stories into towers (stories might be empty initially)
    storyTowers = clusterStories(stories || []);

    const hexGroup = new THREE.Group();
    oceanHexes = [];
    landHexes = [];

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

        let geometry, material, hexHeight;

        if (onBorder) {
          // Border hex - lighter gray for visibility
          hexHeight = BASE_HEX_HEIGHT * 0.5;
          geometry = createHexGeometry(HEX_RADIUS * 0.8, hexHeight);
          material = new THREE.MeshBasicMaterial({
            color: BORDER_COLOR,
            transparent: true,
            opacity: 0.8
          });
        } else if (!land) {
          // Ocean hex - dark blue
          hexHeight = BASE_HEX_HEIGHT;
          geometry = createHexGeometry(HEX_RADIUS * 0.8, hexHeight);
          material = new THREE.MeshBasicMaterial({
            color: OCEAN_COLOR.clone(),
            transparent: true,
            opacity: 0.9
          });
        } else {
          // Land hex - check for tower influence
          const influence = calculateTowerInfluence(lat, lng);

          if (influence) {
            // Near tower - apply falloff
            hexHeight = BASE_HEX_HEIGHT + influence.height;
            geometry = createHexGeometry(HEX_RADIUS * 0.8, hexHeight);
            material = new THREE.MeshBasicMaterial({
              color: influence.color,
              transparent: true,
              opacity: 0.9
            });
          } else {
            // Base land - muted dark color
            hexHeight = BASE_HEX_HEIGHT;
            geometry = createHexGeometry(HEX_RADIUS * 0.8, hexHeight);
            material = new THREE.MeshBasicMaterial({
              color: BASE_LAND_COLOR,
              transparent: true,
              opacity: 0.9
            });
          }
        }

        const hex = new THREE.Mesh(geometry, material);

        // Position on sphere
        const position = latLngToVector3(lat, lng, GLOBE_RADIUS);
        hex.position.copy(position);

        // Orient hex to point outward from sphere center
        hex.lookAt(0, 0, 0);
        hex.rotateX(Math.PI);

        hexGroup.add(hex);

        // Store hexes for animation/updates
        if (!land && !onBorder) {
          oceanHexes.push({
            mesh: hex,
            material: material as THREE.MeshBasicMaterial,
            lat,
            lng,
            baseY: position.length(),
            baseColor: OCEAN_COLOR.clone()
          });
        } else if (land && !onBorder) {
          landHexes.push({
            mesh: hex,
            material: material as THREE.MeshBasicMaterial,
            lat,
            lng,
            baseY: position.length(),
            baseHeight: hexHeight
          });
        }
      }
    }

    scene.add(hexGroup);

    // Build story towers
    buildStoryTowers();
  }

  // Build tall tower spikes at story locations
  function buildStoryTowers() {
    if (!scene) return;

    // Remove existing towers
    if (towerGroup) {
      scene.remove(towerGroup);
      towerGroup.traverse((child) => {
        if (child instanceof THREE.Mesh) {
          child.geometry.dispose();
          (child.material as THREE.Material).dispose();
        }
      });
      towerGroup = null;
    }
    towerMeshes = [];

    if (storyTowers.length === 0) return;

    towerGroup = new THREE.Group();
    const maxTowerHeight = Math.max(...storyTowers.map(t => t.height));

    storyTowers.forEach((tower) => {
      const geometry = createHexGeometry(HEX_RADIUS * 1.2, tower.height);
      const color = colorFromTowerHeight(tower.height, maxTowerHeight);
      const material = new THREE.MeshBasicMaterial({
        color,
        transparent: true,
        opacity: 0.95
      });

      const mesh = new THREE.Mesh(geometry, material);
      const position = latLngToVector3(tower.lat, tower.lng, GLOBE_RADIUS);
      mesh.position.copy(position);
      mesh.lookAt(0, 0, 0);
      mesh.rotateX(Math.PI);

      towerGroup?.add(mesh);
      towerMeshes.push(mesh);
    });

    scene.add(towerGroup);
  }

  // Update camera position
  function updateCameraPosition() {
    if (!camera || !container || !scene) return;
    const viewPos = latLngToVector3(CAMERA_LAT, CAMERA_LNG, CAMERA_DISTANCE);
    camera.position.copy(viewPos);
    camera.lookAt(0, 0, 0);

    applyViewOffset();
  }

  // Apply viewport offset to shift where globe appears on screen
  function applyViewOffset() {
    if (!camera || !container) return;
    const width = container.clientWidth;
    const height = container.clientHeight;
    if (currentOffsetX !== 0 || currentOffsetY !== 0) {
      camera.setViewOffset(
        width, height,
        currentOffsetX, currentOffsetY,
        width, height
      );
    } else {
      camera.clearViewOffset();
    }
    camera.updateProjectionMatrix();
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

    updateCameraPosition();
    camera.lookAt(0, 0, 0);

    renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    container.appendChild(renderer.domElement);

    controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.15; // Smoother damping for touch
    controls.minDistance = 80;
    controls.maxDistance = 250;
    controls.autoRotate = true;
    controls.autoRotateSpeed = 0.3; // Slower
    controls.enablePan = false; // No built-in panning
    controls.target.set(0, 0, 0); // Always orbit around globe center

    // Keep right-click for custom panning via view offset
    controls.mouseButtons = {
      LEFT: THREE.MOUSE.ROTATE,
      MIDDLE: THREE.MOUSE.DOLLY,
      RIGHT: -1  // Disable OrbitControls right-click
    };

    // Touch controls (two-finger rotation and pinch work automatically)
    controls.touches = {
      ONE: THREE.TOUCH.ROTATE,
      TWO: THREE.TOUCH.DOLLY_PAN
    };

    raycaster = new THREE.Raycaster();

    const ambient = new THREE.AmbientLight(0xffffff, 1);
    scene.add(ambient);

    buildHexGlobe();
  }

  // Mouse move handler for hover and panning
  function handleMouseMove(event: MouseEvent) {
    // Handle panning first
    if (isPanning) {
      handlePanMove(event);
      return;
    }

    if (!raycaster || !camera || !container) return;

    const rect = container.getBoundingClientRect();
    mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

    raycaster.setFromCamera(mouse, camera);

    const hits = raycaster.intersectObjects(towerMeshes);
    if (hits.length > 0) {
      const towerIndex = towerMeshes.indexOf(hits[0].object as THREE.Mesh);
      if (towerIndex !== -1) {
        hoveredTower = towerIndex;
        const tower = storyTowers[towerIndex];
        tooltip = {
          x: event.clientX - rect.left,
          y: event.clientY - rect.top,
          count: tower.count
        };
        container.style.cursor = 'pointer';
        return;
      }
    }

    hoveredTower = null;
    tooltip = null;
    container.style.cursor = 'grab';
  }

  // Mouse click handler
  function handleClick(event: MouseEvent) {
    if (hoveredTower === null) return;

    const tower = storyTowers[hoveredTower];
    activeCluster = {
      stories: tower.stories,
      count: tower.count,
      position: { x: event.clientX + 16, y: event.clientY + 16 }
    };
  }

  // Mouse leave handler
  function handleMouseLeave() {
    hoveredTower = null;
    tooltip = null;
    isPanning = false;
    if (container) container.style.cursor = 'grab';
  }

  // Custom panning with right-click
  let isPanning = false;
  let panStartX = 0;
  let panStartY = 0;
  let panStartOffsetX = 0;
  let panStartOffsetY = 0;

  function handleMouseDown(event: MouseEvent) {
    if (event.button === 2) { // Right-click
      event.preventDefault();
      isPanning = true;
      panStartX = event.clientX;
      panStartY = event.clientY;
      panStartOffsetX = currentOffsetX;
      panStartOffsetY = currentOffsetY;
      if (container) container.style.cursor = 'move';
    }
  }

  function handleMouseUp(event: MouseEvent) {
    if (event.button === 2) {
      isPanning = false;
      if (container) container.style.cursor = 'grab';
    }
  }

  function handlePanMove(event: MouseEvent) {
    if (!isPanning) return;

    const deltaX = event.clientX - panStartX;
    const deltaY = event.clientY - panStartY;

    currentOffsetX = panStartOffsetX - deltaX;
    currentOffsetY = panStartOffsetY - deltaY;

    applyViewOffset();
  }

  function handleResize() {
    if (!camera || !renderer || !container) return;
    camera.aspect = container.clientWidth / container.clientHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(container.clientWidth, container.clientHeight);
    updateCameraPosition(); // Reapply offset with new dimensions
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

  // LOD state
  let currentLOD: 'high' | 'medium' | 'low' = 'high';

  function updateLOD() {
    if (!camera) return;

    const distance = camera.position.length();
    const lodLevel = getLODLevel(distance, {
      lodDistance: [100, 300, 1000],
      pixelRatio: 2,
      antialias: true,
      shadowMapEnabled: false,
      bloomEnabled: false,
      maxParticles: 0,
      targetFPS: 60,
      enableAutoRotate: true,
      mode: 'high'
    });

    if (lodLevel === currentLOD) return;

    currentLOD = lodLevel;

    // Update hexagon visibility based on LOD
    if (lodLevel === 'high') {
      // Show all hexagons, full detail
      oceanHexes.forEach(({ mesh }) => { mesh.visible = true; });
      landHexes.forEach(({ mesh }) => { mesh.visible = true; });
    } else if (lodLevel === 'medium') {
      // Show every other hexagon, reduce density by ~50%
      oceanHexes.forEach(({ mesh }, i) => { mesh.visible = i % 2 === 0; });
      landHexes.forEach(({ mesh }, i) => { mesh.visible = i % 2 === 0; });

      // Disable wave animation at medium LOD (performance)
      waveActive = false;
    } else {
      // Low LOD: Show even fewer hexagons
      oceanHexes.forEach(({ mesh }, i) => { mesh.visible = i % 3 === 0; });
      landHexes.forEach(({ mesh }, i) => { mesh.visible = i % 3 === 0; });
      waveActive = false;
    }
  }

  function animate() {
    animationId = requestAnimationFrame(animate);
    // updateLOD(); // DISABLED: LOD system hides hexagons, making tiling less dense
    updateWave();
    controls?.update();
    renderer?.render(scene, camera);
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
      // Single touch - potential long-press or tap
      const touch = touches[0];
      touchData.touchStartPos = { x: touch.clientX, y: touch.clientY };

      // Start long-press timer (500ms)
      touchData.longPressTimer = setTimeout(() => {
        handleLongPress(touch);
      }, 500);
    } else if (touches.length === 2) {
      // Two-finger touch - pinch-to-zoom is handled by OrbitControls
      // Just store initial distance for smooth damping
      const dx = touches[1].clientX - touches[0].clientX;
      const dy = touches[1].clientY - touches[0].clientY;
      touchData.initialDistance = Math.sqrt(dx * dx + dy * dy);

      // Cancel long-press on multi-touch
      if (touchData.longPressTimer) {
        clearTimeout(touchData.longPressTimer);
        touchData.longPressTimer = null;
      }
    }
  }

  function handleTouchMove(event: TouchEvent) {
    // Cancel long-press if finger moves
    if (touchData.longPressTimer) {
      clearTimeout(touchData.longPressTimer);
      touchData.longPressTimer = null;
    }

    // OrbitControls handles two-finger rotation and pinch-to-zoom automatically
  }

  function handleTouchEnd(event: TouchEvent) {
    // Cancel long-press timer
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

    // Check for tap (minimal movement)
    if (distance < 10) {
      const now = Date.now();
      const timeSinceLast = now - touchData.lastTapTime;

      if (timeSinceLast < 300) {
        // Double-tap detected - reset camera
        handleDoubleTap();
        touchData.lastTapTime = 0;
      } else {
        // Single tap - check for tower click
        touchData.lastTapTime = now;
        handleTouchTap(touch);
      }
    }

    touchData.initialDistance = 0;
  }

  function handleLongPress(touch: Touch) {
    // Long-press on tower - show story detail
    if (!raycaster || !camera || !container) return;

    const rect = container.getBoundingClientRect();
    mouse.x = ((touch.clientX - rect.left) / rect.width) * 2 - 1;
    mouse.y = -((touch.clientY - rect.top) / rect.height) * 2 + 1;

    raycaster.setFromCamera(mouse, camera);
    const hits = raycaster.intersectObjects(towerMeshes);

    if (hits.length > 0) {
      const towerIndex = towerMeshes.indexOf(hits[0].object as THREE.Mesh);
      if (towerIndex !== -1) {
        const tower = storyTowers[towerIndex];
        haptics.medium();

        // Open cluster window
        activeCluster = {
          stories: tower.stories,
          count: tower.count,
          position: { x: touch.clientX + 16, y: touch.clientY + 16 }
        };
      }
    }
  }

  function handleDoubleTap() {
    // Reset camera to default position
    if (!camera || !controls) return;

    haptics.light();

    // Animate camera back to starting position
    const startPos = camera.position.clone();
    const targetPos = new THREE.Vector3();

    // Calculate default camera position
    const lat = CAMERA_LAT;
    const lng = CAMERA_LNG;
    const phi = (90 - lat) * (Math.PI / 180);
    const theta = (lng + 180) * (Math.PI / 180);
    const distance = CAMERA_DISTANCE;

    targetPos.x = distance * Math.sin(phi) * Math.cos(theta);
    targetPos.y = distance * Math.cos(phi);
    targetPos.z = distance * Math.sin(phi) * Math.sin(theta);

    // Reset offset
    currentOffsetX = CAMERA_OFFSET_X;
    currentOffsetY = CAMERA_OFFSET_Y;

    // Simple animation over 800ms
    const duration = 800;
    const startTime = Date.now();

    function animateReset() {
      const now = Date.now();
      const progress = Math.min((now - startTime) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3); // ease-out cubic

      camera.position.lerpVectors(startPos, targetPos, eased);
      updateCameraPosition();

      if (progress < 1) {
        requestAnimationFrame(animateReset);
      }
    }

    animateReset();
  }

  function handleTouchTap(touch: Touch) {
    // Handle tower click on tap
    if (!raycaster || !camera || !container) return;

    const rect = container.getBoundingClientRect();
    mouse.x = ((touch.clientX - rect.left) / rect.width) * 2 - 1;
    mouse.y = -((touch.clientY - rect.top) / rect.height) * 2 + 1;

    raycaster.setFromCamera(mouse, camera);
    const hits = raycaster.intersectObjects(towerMeshes);

    if (hits.length > 0) {
      const towerIndex = towerMeshes.indexOf(hits[0].object as THREE.Mesh);
      if (towerIndex !== -1) {
        const tower = storyTowers[towerIndex];
        haptics.light();

        activeCluster = {
          stories: tower.stories,
          count: tower.count,
          position: { x: touch.clientX + 16, y: touch.clientY + 16 }
        };
      }
    }
  }

  onMount(async () => {
    if (!browser) return;

    await loadBorders();
    setupScene();
    window.addEventListener('resize', handleResize);
    window.addEventListener('mouseup', handleMouseUp); // Catch mouseup anywhere
    window.addEventListener('mousemove', handlePanMove); // Track panning anywhere
    container?.addEventListener('mousemove', handleMouseMove);
    container?.addEventListener('mousedown', handleMouseDown);
    container?.addEventListener('click', handleClick);
    container?.addEventListener('mouseleave', handleMouseLeave);
    container?.addEventListener('contextmenu', (e) => e.preventDefault()); // Prevent right-click menu

    // Touch event listeners
    container?.addEventListener('touchstart', handleTouchStart, { passive: false });
    container?.addEventListener('touchmove', handleTouchMove, { passive: false });
    container?.addEventListener('touchend', handleTouchEnd, { passive: true });

    // Trigger first wave after 5 seconds
    lastWaveTime = Date.now() - WAVE_INTERVAL + 5000;
    animate();
  });

  onDestroy(() => {
    if (animationId) cancelAnimationFrame(animationId);

    // Clean up long-press timer
    if (touchData.longPressTimer) {
      clearTimeout(touchData.longPressTimer);
    }

    window.removeEventListener('resize', handleResize);
    window.removeEventListener('mouseup', handleMouseUp);
    window.removeEventListener('mousemove', handlePanMove);
    container?.removeEventListener('mousemove', handleMouseMove);
    container?.removeEventListener('mousedown', handleMouseDown);
    container?.removeEventListener('click', handleClick);
    container?.removeEventListener('mouseleave', handleMouseLeave);

    // Remove touch listeners
    container?.removeEventListener('touchstart', handleTouchStart);
    container?.removeEventListener('touchmove', handleTouchMove);
    container?.removeEventListener('touchend', handleTouchEnd);

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

  // Rebuild towers when stories change (don't rebuild entire globe)
  $effect(() => {
    // Access stories first to ensure dependency tracking
    const currentStories = stories || [];
    console.log('[RetroMap] Effect triggered. Stories count:', currentStories.length, 'Scene ready:', !!scene);

    if (!browser || !scene) return;

    console.log('[RetroMap] Rebuilding towers...');
    storyTowers = clusterStories(currentStories);
    buildStoryTowers();

    // Update land hex colors based on new tower positions
    landHexes.forEach(({ mesh, material, lat, lng, baseY, baseHeight }) => {
      const influence = calculateTowerInfluence(lat, lng);
      if (influence) {
        material.color.copy(influence.color);
        const normal = mesh.position.clone().normalize();
        mesh.position.copy(normal.multiplyScalar(baseY + influence.height));
      } else {
        material.color.copy(BASE_LAND_COLOR);
        const normal = mesh.position.clone().normalize();
        mesh.position.copy(normal.multiplyScalar(baseY + baseHeight));
      }
    });
  });
</script>

{#if browser}
<div class="relative w-full h-full overflow-hidden" bind:this={container}>
  {#if tooltip}
    <div
      class="absolute z-20 px-3 py-2 bg-slate-950/90 backdrop-blur-md border border-cyan-400/30 rounded-lg shadow-[0_0_24px_rgba(56,189,248,0.25)] pointer-events-none"
      style="left: {tooltip.x + 12}px; top: {tooltip.y + 12}px;"
    >
      <div class="font-semibold text-sm text-white">{tooltip.count} {tooltip.count === 1 ? 'story' : 'stories'}</div>
      <div class="text-xs text-cyan-100 mt-1">Click to view</div>
    </div>
  {/if}

  {#if activeCluster}
    <MapClusterWindow
      stories={activeCluster.stories}
      count={activeCluster.count}
      position={activeCluster.position}
      onClose={() => activeCluster = null}
      onOpenStory={onStoryClick}
    />
  {/if}
</div>
{:else}
<div class="relative w-full h-full flex items-center justify-center bg-black">
  <div class="text-cyan-200/70 text-xs uppercase tracking-[0.4em]">Loading globe...</div>
</div>
{/if}
