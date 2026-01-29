<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import * as THREE from 'three';
  import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
  import { EffectComposer } from 'three/examples/jsm/postprocessing/EffectComposer.js';
  import { RenderPass } from 'three/examples/jsm/postprocessing/RenderPass.js';
  import { UnrealBloomPass } from 'three/examples/jsm/postprocessing/UnrealBloomPass.js';
  import type { MapStory } from '$lib/api';
  import MapClusterWindow from '$lib/components/MapClusterWindow.svelte';
  import usStates from '$lib/assets/us-states.json';

  interface Props {
    stories: MapStory[];
    onStoryClick?: (story: MapStory) => void;
  }

  let { stories, onStoryClick }: Props = $props();

  let container: HTMLDivElement;
  let renderer: THREE.WebGLRenderer | null = null;
  let composer: EffectComposer | null = null;
  let scene: THREE.Scene | null = null;
  let camera: THREE.PerspectiveCamera | null = null;
  let controls: OrbitControls | null = null;
  let raycaster: THREE.Raycaster | null = null;
  const mouse = new THREE.Vector2();
  let animationId: number | null = null;
  let hoveredIndex: number | null = null;
  let tooltip: { x: number; y: number; count: number } | null = $state(null);
  let showLegend = $state(false);
  let activeCluster: { stories: MapStory[]; count: number; position: { x: number; y: number } } | null = $state(null);

  const MAP_BOUNDS = {
    minLat: 24.4,
    maxLat: 49.5,
    minLng: -124.9,
    maxLng: -66.8,
  };

  type GeoJSONFeatureCollection = {
    type: 'FeatureCollection';
    features: GeoJSONFeature[];
  };

  type GeoJSONFeature = {
    type: 'Feature';
    properties?: { name?: string };
    geometry: GeoJSONGeometry;
  };

  type GeoJSONGeometry =
    | { type: 'Polygon'; coordinates: number[][][] }
    | { type: 'MultiPolygon'; coordinates: number[][][][] };

  const US_STATES = usStates as GeoJSONFeatureCollection;
  const EXCLUDED_STATES = new Set(['Alaska', 'Hawaii', 'Puerto Rico']);

  const MAP_SIZE = {
    width: 140,
    height: 84,
  };

  const GRID_SIZE = { x: 70, z: 42 };
  const COUNT_COLOR_LOW = '#22d3ee';
  const COUNT_COLOR_HIGH = '#f97316';
  const BASE_PLANE_Y = -2.4;

  let towerMesh: THREE.InstancedMesh | null = null;
  let countLabels: THREE.Group | null = null;
  let labelMaterials: THREE.SpriteMaterial[] = [];
  let stateLines: THREE.LineSegments | null = null;
  let hoverRing: THREE.Mesh | null = null;
  let basePlane: THREE.Mesh | null = null;
  let landMask: THREE.Mesh | null = null;
  let mapFrame: THREE.LineSegments | null = null;
  let gridCenters: { x: number; z: number }[] = [];
  let gridCounts: number[] = [];
  let gridHeights: number[] = [];
  let gridStories: Map<number, MapStory[]> = new Map();
  let towerCellIndices: number[] = [];
  let tileSize = { width: MAP_SIZE.width / GRID_SIZE.x, depth: MAP_SIZE.height / GRID_SIZE.z };
  let mapTexture: THREE.Texture | null = null;
  let landMaskTexture: THREE.Texture | null = null;
  const countTextures = new Map<number, THREE.Texture>();

  const clock = new THREE.Clock();

  function clamp(value: number, min: number, max: number) {
    return Math.min(Math.max(value, min), max);
  }

  function projectLatLng(lng: number, lat: number) {
    const clampedLng = clamp(lng, MAP_BOUNDS.minLng, MAP_BOUNDS.maxLng);
    const clampedLat = clamp(lat, MAP_BOUNDS.minLat, MAP_BOUNDS.maxLat);
    const x = ((clampedLng - MAP_BOUNDS.minLng) / (MAP_BOUNDS.maxLng - MAP_BOUNDS.minLng) - 0.5) * MAP_SIZE.width;
    const z = ((clampedLat - MAP_BOUNDS.minLat) / (MAP_BOUNDS.maxLat - MAP_BOUNDS.minLat) - 0.5) * -MAP_SIZE.height;
    return { x, z };
  }

  function createMapTexture() {
    const canvas = document.createElement('canvas');
    canvas.width = 1024;
    canvas.height = 768;
    const ctx = canvas.getContext('2d');
    if (!ctx) return null;

    const background = ctx.createLinearGradient(0, 0, canvas.width, canvas.height);
    background.addColorStop(0, '#111a33');
    background.addColorStop(0.5, '#182449');
    background.addColorStop(1, '#0f1b36');
    ctx.fillStyle = background;
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    const glow = ctx.createRadialGradient(
      canvas.width * 0.55,
      canvas.height * 0.45,
      120,
      canvas.width * 0.55,
      canvas.height * 0.45,
      480
    );
    glow.addColorStop(0, 'rgba(56, 189, 248, 0.25)');
    glow.addColorStop(1, 'rgba(15, 23, 42, 0)');
    ctx.fillStyle = glow;
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    ctx.strokeStyle = 'rgba(148, 163, 184, 0.16)';
    ctx.lineWidth = 1;
    for (let x = 0; x <= canvas.width; x += 48) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, canvas.height);
      ctx.stroke();
    }
    for (let y = 0; y <= canvas.height; y += 48) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(canvas.width, y);
      ctx.stroke();
    }

    ctx.strokeStyle = 'rgba(56, 189, 248, 0.28)';
    ctx.lineWidth = 1.2;
    for (let i = -canvas.height; i < canvas.width; i += 90) {
      ctx.beginPath();
      ctx.moveTo(i, 0);
      ctx.lineTo(i + canvas.height, canvas.height);
      ctx.stroke();
    }

    const noiseCount = 3200;
    ctx.fillStyle = 'rgba(148, 163, 184, 0.05)';
    for (let i = 0; i < noiseCount; i += 1) {
      const x = Math.random() * canvas.width;
      const y = Math.random() * canvas.height;
      ctx.fillRect(x, y, 1, 1);
    }

    const texture = new THREE.CanvasTexture(canvas);
    texture.wrapS = THREE.ClampToEdgeWrapping;
    texture.wrapT = THREE.ClampToEdgeWrapping;
    texture.anisotropy = 4;
    return texture;
  }

  function forEachRing(geometry: GeoJSONGeometry, handler: (ring: number[][], isHole: boolean) => void) {
    if (geometry.type === 'Polygon') {
      geometry.coordinates.forEach((ring, index) => handler(ring, index > 0));
      return;
    }
    geometry.coordinates.forEach((polygon) => {
      polygon.forEach((ring, index) => handler(ring, index > 0));
    });
  }

  function toCanvasPoint(lng: number, lat: number, width: number, height: number) {
    const clampedLng = clamp(lng, MAP_BOUNDS.minLng, MAP_BOUNDS.maxLng);
    const clampedLat = clamp(lat, MAP_BOUNDS.minLat, MAP_BOUNDS.maxLat);
    const x = ((clampedLng - MAP_BOUNDS.minLng) / (MAP_BOUNDS.maxLng - MAP_BOUNDS.minLng)) * width;
    const y = height - ((clampedLat - MAP_BOUNDS.minLat) / (MAP_BOUNDS.maxLat - MAP_BOUNDS.minLat)) * height;
    return { x, y };
  }

  function createUsMaskTexture() {
    const canvas = document.createElement('canvas');
    canvas.width = 1024;
    canvas.height = 768;
    const ctx = canvas.getContext('2d');
    if (!ctx) return null;

    ctx.fillStyle = 'black';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    for (const feature of US_STATES.features) {
      const name = feature.properties?.name;
      if (name && EXCLUDED_STATES.has(name)) continue;

      forEachRing(feature.geometry, (ring, isHole) => {
        if (ring.length < 2) return;
        ctx.beginPath();
        const start = toCanvasPoint(ring[0][0], ring[0][1], canvas.width, canvas.height);
        ctx.moveTo(start.x, start.y);
        for (let i = 1; i < ring.length; i += 1) {
          const point = toCanvasPoint(ring[i][0], ring[i][1], canvas.width, canvas.height);
          ctx.lineTo(point.x, point.y);
        }
        ctx.closePath();
        ctx.globalCompositeOperation = isHole ? 'destination-out' : 'source-over';
        ctx.fillStyle = 'white';
        ctx.fill();
      });
    }

    ctx.globalCompositeOperation = 'source-over';

    const texture = new THREE.CanvasTexture(canvas);
    texture.wrapS = THREE.ClampToEdgeWrapping;
    texture.wrapT = THREE.ClampToEdgeWrapping;
    return texture;
  }

  function buildLandMask() {
    if (!scene) return;

    if (landMask) {
      scene.remove(landMask);
      landMask.geometry.dispose();
      (landMask.material as THREE.Material).dispose();
      landMask = null;
    }
    if (landMaskTexture) {
      landMaskTexture.dispose();
    }

    landMaskTexture = createUsMaskTexture();
    if (!landMaskTexture) return;

    const geometry = new THREE.PlaneGeometry(MAP_SIZE.width, MAP_SIZE.height, 1, 1);
    const material = new THREE.MeshBasicMaterial({
      color: new THREE.Color('#2563eb'),
      transparent: true,
      opacity: 0.35,
      alphaMap: landMaskTexture,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
      fog: false,
    });

    landMask = new THREE.Mesh(geometry, material);
    landMask.rotation.x = -Math.PI / 2;
    landMask.position.y = BASE_PLANE_Y + 0.2;
    landMask.renderOrder = 1;
    scene.add(landMask);
  }

  function buildStateOutlines() {
    if (!scene) return;

    if (stateLines) {
      scene.remove(stateLines);
      stateLines.geometry.dispose();
      (stateLines.material as THREE.Material).dispose();
      stateLines = null;
    }

    const positions: number[] = [];
    const lineY = BASE_PLANE_Y + 0.35;

    const addRing = (ring: number[][]) => {
      if (ring.length < 2) return;
      for (let i = 0; i < ring.length - 1; i += 1) {
        const a = projectLatLng(ring[i][0], ring[i][1]);
        const b = projectLatLng(ring[i + 1][0], ring[i + 1][1]);
        positions.push(a.x, lineY, a.z, b.x, lineY, b.z);
      }
    };

    for (const feature of US_STATES.features) {
      const name = feature.properties?.name;
      if (name && EXCLUDED_STATES.has(name)) continue;

      forEachRing(feature.geometry, (ring) => {
        addRing(ring);
      });
    }

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
    const material = new THREE.LineBasicMaterial({
      color: 0x93c5fd,
      transparent: true,
      opacity: 0.5,
      depthWrite: false,
      fog: false,
    });

    stateLines = new THREE.LineSegments(geometry, material);
    stateLines.renderOrder = 2;
    scene.add(stateLines);
  }

  function buildBaseMap() {
    if (!scene) return;

    const geometry = new THREE.PlaneGeometry(MAP_SIZE.width, MAP_SIZE.height, 90, 60);
    const position = geometry.attributes.position as THREE.BufferAttribute;
    for (let i = 0; i < position.count; i += 1) {
      const x = position.getX(i);
      const y = position.getY(i);
      const wave = Math.sin((x + 40) * 0.08) * Math.cos((y + 20) * 0.06) * 0.25;
      position.setZ(i, wave);
    }
    geometry.computeVertexNormals();

    if (mapTexture) {
      mapTexture.dispose();
    }
    mapTexture = createMapTexture();
    const material = new THREE.MeshBasicMaterial({
      color: new THREE.Color('#0f172a'),
      map: mapTexture || undefined,
      fog: false,
    });

    basePlane = new THREE.Mesh(geometry, material);
    basePlane.rotation.x = -Math.PI / 2;
    basePlane.position.y = BASE_PLANE_Y;
    basePlane.receiveShadow = true;
    scene.add(basePlane);

    const frameGeometry = new THREE.EdgesGeometry(new THREE.PlaneGeometry(MAP_SIZE.width * 1.01, MAP_SIZE.height * 1.01));
    const frameMaterial = new THREE.LineBasicMaterial({
      color: 0x38bdf8,
      transparent: true,
      opacity: 0.35,
    });
    mapFrame = new THREE.LineSegments(frameGeometry, frameMaterial);
    mapFrame.rotation.x = -Math.PI / 2;
    mapFrame.position.y = BASE_PLANE_Y + 0.05;
    scene.add(mapFrame);
  }

  function buildDensityTowers() {
    if (!scene) return;

    if (towerMesh) {
      scene.remove(towerMesh);
      towerMesh.geometry.dispose();
      (towerMesh.material as THREE.Material).dispose();
      towerMesh = null;
    }
    if (countLabels) {
      scene.remove(countLabels);
      countLabels.traverse((child) => {
        if (child instanceof THREE.Sprite) {
          child.material.dispose();
        }
      });
      countLabels = null;
      labelMaterials = [];
    }

    tileSize = {
      width: MAP_SIZE.width / GRID_SIZE.x,
      depth: MAP_SIZE.height / GRID_SIZE.z,
    };

    gridCounts = new Array(GRID_SIZE.x * GRID_SIZE.z).fill(0);
    gridCenters = new Array(GRID_SIZE.x * GRID_SIZE.z);
    gridHeights = new Array(GRID_SIZE.x * GRID_SIZE.z).fill(0);
    gridStories = new Map();

    for (const story of stories) {
      const { x, z } = projectLatLng(story.lng, story.lat);
      const gridX = clamp(Math.floor(((x + MAP_SIZE.width / 2) / MAP_SIZE.width) * GRID_SIZE.x), 0, GRID_SIZE.x - 1);
      const gridZ = clamp(Math.floor(((z + MAP_SIZE.height / 2) / MAP_SIZE.height) * GRID_SIZE.z), 0, GRID_SIZE.z - 1);
      const index = gridZ * GRID_SIZE.x + gridX;
      gridCounts[index] += 1;
      if (!gridStories.has(index)) {
        gridStories.set(index, []);
      }
      gridStories.get(index)?.push(story);
    }

    const maxCount = Math.max(...gridCounts, 1);
    const geometry = new THREE.BoxGeometry(tileSize.width * 0.86, 1, tileSize.depth * 0.86);
    const material = new THREE.MeshBasicMaterial({
      color: new THREE.Color('#ffffff'),
      vertexColors: true,
      transparent: true,
      opacity: 0.95,
      fog: false,
    });

    const lowColor = new THREE.Color(COUNT_COLOR_LOW);
    const highColor = new THREE.Color(COUNT_COLOR_HIGH);
    const matrix = new THREE.Matrix4();
    const scale = new THREE.Vector3();
    const position = new THREE.Vector3();
    const color = new THREE.Color();

    const filledCells: { cellIndex: number; count: number; height: number }[] = [];
    for (let z = 0; z < GRID_SIZE.z; z += 1) {
      for (let x = 0; x < GRID_SIZE.x; x += 1) {
        const index = z * GRID_SIZE.x + x;
        const count = gridCounts[index];
        const centerX = -MAP_SIZE.width / 2 + tileSize.width / 2 + x * tileSize.width;
        const centerZ = -MAP_SIZE.height / 2 + tileSize.depth / 2 + z * tileSize.depth;
        gridCenters[index] = { x: centerX, z: centerZ };

        if (count === 0) {
          gridHeights[index] = 0;
          continue;
        }

        const height = 0.6 + Math.log(count + 1) * 2.8;
        gridHeights[index] = height;
        filledCells.push({ cellIndex: index, count, height });
      }
    }

    if (filledCells.length === 0) {
      towerCellIndices = [];
      return;
    }

    towerMesh = new THREE.InstancedMesh(geometry, material, filledCells.length);
    towerMesh.instanceColor = new THREE.InstancedBufferAttribute(new Float32Array(filledCells.length * 3), 3);
    towerCellIndices = [];

    filledCells.forEach((cell, instanceIndex) => {
      const center = gridCenters[cell.cellIndex];
      const normalized = clamp(cell.height / (Math.log(maxCount + 1) * 2.8 + 0.6), 0, 1);
      position.set(center.x, BASE_PLANE_Y + 0.1 + cell.height / 2, center.z);
      scale.set(1, cell.height, 1);
      matrix.compose(position, new THREE.Quaternion(), scale);
      towerMesh?.setMatrixAt(instanceIndex, matrix);
      color.copy(lowColor).lerp(highColor, normalized);
      towerMesh?.setColorAt(instanceIndex, color);
      towerCellIndices.push(cell.cellIndex);
    });

    towerMesh.instanceMatrix.needsUpdate = true;
    if (towerMesh.instanceColor) towerMesh.instanceColor.needsUpdate = true;
    scene.add(towerMesh);

    buildCountLabels(filledCells, maxCount);
  }

  function getCountTexture(count: number) {
    const existing = countTextures.get(count);
    if (existing) return existing;

    const canvas = document.createElement('canvas');
    canvas.width = 128;
    canvas.height = 128;
    const ctx = canvas.getContext('2d');
    if (!ctx) return null;

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = 'rgba(2, 6, 23, 0.65)';
    ctx.beginPath();
    ctx.arc(64, 64, 44, 0, Math.PI * 2);
    ctx.fill();

    ctx.fillStyle = '#e2e8f0';
    ctx.font = 'bold 44px \"Space Grotesk\", sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(String(count), 64, 66);

    const texture = new THREE.CanvasTexture(canvas);
    texture.minFilter = THREE.LinearFilter;
    texture.magFilter = THREE.LinearFilter;
    countTextures.set(count, texture);
    return texture;
  }

  function buildCountLabels(
    cells: { cellIndex: number; count: number; height: number }[],
    maxCount: number
  ) {
    if (!scene) return;
    if (cells.length === 0) return;

    countLabels = new THREE.Group();
    const lowColor = new THREE.Color(COUNT_COLOR_LOW);
    const highColor = new THREE.Color(COUNT_COLOR_HIGH);

    cells.forEach((cell) => {
      const texture = getCountTexture(cell.count);
      if (!texture) return;

      const normalized = clamp(cell.height / (Math.log(maxCount + 1) * 2.8 + 0.6), 0, 1);
      const color = lowColor.clone().lerp(highColor, normalized);
    const material = new THREE.SpriteMaterial({
      map: texture,
      color,
      transparent: true,
      opacity: 0.9,
      depthWrite: false,
      fog: false,
    });
      labelMaterials.push(material);

      const sprite = new THREE.Sprite(material);
      const center = gridCenters[cell.cellIndex];
      sprite.position.set(center.x, BASE_PLANE_Y + cell.height + 2.2, center.z);
      sprite.scale.set(tileSize.width * 0.8, tileSize.width * 0.8, 1);
      sprite.renderOrder = 3;
      countLabels?.add(sprite);
    });

    scene.add(countLabels);
  }

  function buildHoverRing() {
    if (!scene) return;
    if (hoverRing) {
      scene.remove(hoverRing);
      hoverRing.geometry.dispose();
      (hoverRing.material as THREE.Material).dispose();
    }
    const ringGeometry = new THREE.RingGeometry(tileSize.width * 0.2, tileSize.width * 0.32, 32);
    const ringMaterial = new THREE.MeshBasicMaterial({
      color: 0xffffff,
      transparent: true,
      opacity: 0.0,
      blending: THREE.AdditiveBlending,
      side: THREE.DoubleSide,
    });
    hoverRing = new THREE.Mesh(ringGeometry, ringMaterial);
    hoverRing.rotation.x = -Math.PI / 2;
    hoverRing.visible = false;
    scene.add(hoverRing);
  }

  function initScene() {
    if (!container) return;

    scene = new THREE.Scene();
    scene.background = new THREE.Color('#050b18');
    scene.fog = new THREE.FogExp2(0x050b18, 0.009);

    camera = new THREE.PerspectiveCamera(55, container.clientWidth / container.clientHeight, 0.1, 500);
    camera.position.set(0, 60, 110);

    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'high-performance' });
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.15;
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    container.appendChild(renderer.domElement);

    composer = new EffectComposer(renderer);
    composer.addPass(new RenderPass(scene, camera));
    const bloomPass = new UnrealBloomPass(
      new THREE.Vector2(container.clientWidth, container.clientHeight),
      1.1,
      0.6,
      0.2
    );
    composer.addPass(bloomPass);

    controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.minDistance = 70;
    controls.maxDistance = 170;
    controls.minPolarAngle = 0.45;
    controls.maxPolarAngle = 1.35;
    controls.enablePan = true;

    raycaster = new THREE.Raycaster();

    const ambient = new THREE.AmbientLight(0xbfe8ff, 0.6);
    scene.add(ambient);

    const hemi = new THREE.HemisphereLight(0x7dd3fc, 0x0b1020, 0.45);
    scene.add(hemi);

    const keyLight = new THREE.DirectionalLight(0xffffff, 0.9);
    keyLight.position.set(30, 90, 60);
    scene.add(keyLight);

    const rimLight = new THREE.PointLight(0x22d3ee, 1.7, 200, 2);
    rimLight.position.set(-60, 40, -40);
    scene.add(rimLight);

    buildBaseMap();
    buildLandMask();
    buildStateOutlines();
    buildDensityTowers();
    buildHoverRing();
  }

  function updateStoryData() {
    if (!scene) return;
    buildDensityTowers();
    buildHoverRing();
    activeCluster = null;
    tooltip = null;
    hoveredIndex = null;
  }

  function onResize() {
    if (!renderer || !camera || !composer) return;
    camera.aspect = container.clientWidth / container.clientHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(container.clientWidth, container.clientHeight);
    composer.setSize(container.clientWidth, container.clientHeight);
  }

  function updateHover(event: MouseEvent) {
    if (!raycaster || !camera || !towerMesh || !hoverRing) return;
    const rect = container.getBoundingClientRect();
    mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
    raycaster.setFromCamera(mouse, camera);

    const hits = raycaster.intersectObject(towerMesh);
    if (hits.length > 0 && hits[0].instanceId !== undefined) {
      const towerIndex = hits[0].instanceId;
      const cellIndex = towerCellIndices[towerIndex];
      const count = gridCounts[cellIndex] || 0;
      if (count === 0) {
        hoveredIndex = null;
        tooltip = null;
        hoverRing.visible = false;
        return;
      }

      hoveredIndex = cellIndex;
      tooltip = {
        x: event.clientX - rect.left,
        y: event.clientY - rect.top,
        count,
      };
      container.style.cursor = 'pointer';

      const pos = gridCenters[cellIndex];
      const height = gridHeights[cellIndex] || 0.6;
      hoverRing.visible = true;
      hoverRing.position.set(pos.x, BASE_PLANE_Y + height + 0.25, pos.z);
      (hoverRing.material as THREE.MeshBasicMaterial).opacity = 0.9;
    } else {
      hoveredIndex = null;
      tooltip = null;
      container.style.cursor = 'grab';
      hoverRing.visible = false;
    }
  }

  function handleMouseLeave() {
    tooltip = null;
    hoveredIndex = null;
    if (hoverRing) hoverRing.visible = false;
    container.style.cursor = 'grab';
  }

  function handleClick(event: MouseEvent) {
    if (hoveredIndex === null) return;
    const count = gridCounts[hoveredIndex] || 0;
    if (count === 0) return;
    const cellStories = gridStories.get(hoveredIndex) || [];
    activeCluster = {
      stories: cellStories,
      count,
      position: { x: event.clientX + 16, y: event.clientY + 16 },
    };
  }

  function animate() {
    animationId = requestAnimationFrame(animate);
    if (!scene || !camera || !renderer || !composer) return;

    const elapsed = clock.getElapsedTime();
    if (controls) controls.update();

    if (hoverRing && hoverRing.visible) {
      const pulse = 1 + Math.sin(elapsed * 5) * 0.2;
      hoverRing.scale.set(pulse, pulse, pulse);
    }

    composer.render();
  }

  onMount(() => {
    initScene();
    window.addEventListener('resize', onResize);
    container.addEventListener('mousemove', updateHover);
    container.addEventListener('mouseleave', handleMouseLeave);
    container.addEventListener('click', handleClick);
    animate();
  });

  onDestroy(() => {
    if (animationId !== null) cancelAnimationFrame(animationId);
    window.removeEventListener('resize', onResize);
    container?.removeEventListener('mousemove', updateHover);
    container?.removeEventListener('mouseleave', handleMouseLeave);
    container?.removeEventListener('click', handleClick);

    controls?.dispose();
    renderer?.dispose();
    composer?.dispose();

    if (towerMesh) {
      towerMesh.geometry.dispose();
      (towerMesh.material as THREE.Material).dispose();
    }
    if (countLabels) {
      scene?.remove(countLabels);
      countLabels.traverse((child) => {
        if (child instanceof THREE.Sprite) {
          child.material.dispose();
        }
      });
    }
    labelMaterials.forEach((material) => material.dispose());
    labelMaterials = [];
    if (stateLines) {
      stateLines.geometry.dispose();
      (stateLines.material as THREE.Material).dispose();
    }
    if (hoverRing) {
      hoverRing.geometry.dispose();
      (hoverRing.material as THREE.Material).dispose();
    }
    if (basePlane) {
      basePlane.geometry.dispose();
      (basePlane.material as THREE.Material).dispose();
    }
    if (landMask) {
      landMask.geometry.dispose();
      (landMask.material as THREE.Material).dispose();
    }
    if (mapFrame) {
      mapFrame.geometry.dispose();
      (mapFrame.material as THREE.Material).dispose();
    }

    mapTexture?.dispose();
    landMaskTexture?.dispose();
    for (const texture of countTextures.values()) {
      texture.dispose();
    }
    countTextures.clear();

    if (renderer && renderer.domElement && renderer.domElement.parentNode) {
      renderer.domElement.parentNode.removeChild(renderer.domElement);
    }
  });

  $effect(() => {
    if (scene) updateStoryData();
  });
</script>

<div class="relative w-full h-full" bind:this={container}>
  <div class="absolute top-3 left-3 z-10">
    <div class="px-3 py-1.5 bg-slate-900/80 backdrop-blur-md rounded-full border border-cyan-400/30 shadow-[0_0_18px_rgba(56,189,248,0.25)]">
      <span class="text-xs font-semibold uppercase tracking-wide text-cyan-100">{stories.length} signals</span>
    </div>
  </div>

  <button
    onclick={() => (showLegend = !showLegend)}
    class="absolute top-3 right-3 z-10 w-10 h-10 flex items-center justify-center bg-slate-900/80 backdrop-blur-md rounded-xl border border-cyan-500/30 text-cyan-200 hover:text-white shadow-[0_0_18px_rgba(56,189,248,0.3)]"
    aria-label="Toggle legend"
  >
    <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" d="M11.25 6.75h.008v.008h-.008V6.75zm0 3.75h.008v.008h-.008V10.5zm0 3.75h.008v.008h-.008V14.25zm9-2.25a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  </button>

  {#if showLegend}
    <div class="absolute top-14 right-3 z-10 w-48 bg-slate-950/90 backdrop-blur-md rounded-xl border border-cyan-500/30 p-3 shadow-[0_0_24px_rgba(56,189,248,0.25)]">
      <div class="text-[10px] font-semibold text-cyan-200 uppercase tracking-[0.3em] mb-2">Density</div>
      <div
        class="h-2 w-full rounded-full"
        style="background: linear-gradient(90deg, {COUNT_COLOR_LOW}, {COUNT_COLOR_HIGH});"
      ></div>
      <div class="mt-2 flex justify-between text-[10px] text-slate-300">
        <span>Low</span>
        <span>High</span>
      </div>
    </div>
  {/if}

  {#if tooltip}
    <div
      class="absolute z-20 px-3 py-2 bg-slate-950/90 backdrop-blur-md border border-cyan-400/30 rounded-lg shadow-[0_0_24px_rgba(56,189,248,0.25)] pointer-events-none max-w-[240px]"
      style="left: {Math.min(tooltip.x + 12, container?.clientWidth - 200 || 200)}px; top: {tooltip.y + 12}px;"
    >
      <div class="font-semibold text-sm text-white leading-tight">{tooltip.count} stories</div>
      <div class="text-xs text-cyan-100 mt-1">Click to open area window</div>
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

  <div class="absolute bottom-4 left-4 z-10 text-[11px] text-cyan-200/80 px-3 py-2 rounded-lg bg-slate-950/70 border border-cyan-500/20 backdrop-blur">
    Drag to orbit - Scroll to zoom - Click columns to open
  </div>
</div>
