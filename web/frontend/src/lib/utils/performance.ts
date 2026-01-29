/**
 * Performance settings helper
 * Returns optimal Three.js configuration based on device capabilities
 */

import type { DeviceProfile, GPUTier } from './device';

export type PerformanceMode = 'high' | 'medium';

export interface PerformanceSettings {
  // Rendering
  pixelRatio: number;
  antialias: boolean;
  shadowMapEnabled: boolean;
  bloomEnabled: boolean;

  // Particles
  maxParticles: number;

  // LOD (Level of Detail)
  lodDistance: number[]; // Camera distance thresholds [high, medium, low]

  // Animation
  targetFPS: number;
  enableAutoRotate: boolean;

  // General
  mode: PerformanceMode;
}

/**
 * Get optimal performance settings based on device profile
 * Aggressive settings - optimized for modern mid-high end devices
 */
export function getOptimalSettings(device: DeviceProfile): PerformanceSettings {
  // Determine performance mode based on GPU tier and memory
  let mode: PerformanceMode = 'high';

  if (device.gpuTier === 'low' || device.hasLowMemory) {
    mode = 'medium';
  }

  // Override to medium on mobile regardless of GPU
  if (device.isMobile) {
    mode = 'medium';
  }

  // Base settings for high performance
  const settings: PerformanceSettings = {
    // Rendering - aggressive: always 2x pixel ratio, antialias on
    pixelRatio: 2,
    antialias: true,
    shadowMapEnabled: false, // Skip shadows for performance
    bloomEnabled: device.gpuTier === 'high', // Bloom only on high-end GPUs

    // Particles - vary by GPU tier
    maxParticles: device.gpuTier === 'high' ? 500 : 200,

    // LOD distances (camera distance in scene units)
    lodDistance: [100, 300, 1000],

    // Animation
    targetFPS: 60,
    enableAutoRotate: !device.prefersReducedMotion,

    // Mode
    mode,
  };

  // Adjust for medium performance mode
  if (mode === 'medium') {
    settings.bloomEnabled = false;
    settings.maxParticles = 200;
  }

  return settings;
}

/**
 * Get a human-readable summary of performance settings
 */
export function getSettingsSummary(settings: PerformanceSettings): string {
  return `Mode: ${settings.mode.toUpperCase()} | ${settings.pixelRatio}x | ${settings.antialias ? 'AA' : 'No AA'} | ${settings.bloomEnabled ? 'Bloom' : 'No Bloom'} | ${settings.maxParticles} particles`;
}

/**
 * Check if bloom should be enabled
 * Helper for conditional bloom rendering
 */
export function shouldEnableBloom(settings: PerformanceSettings): boolean {
  return settings.bloomEnabled;
}

/**
 * Get LOD level based on camera distance
 * Returns 'high', 'medium', or 'low'
 */
export function getLODLevel(distance: number, settings: PerformanceSettings): 'high' | 'medium' | 'low' {
  const [highThreshold, mediumThreshold] = settings.lodDistance;

  if (distance < highThreshold) {
    return 'high';
  } else if (distance < mediumThreshold) {
    return 'medium';
  } else {
    return 'low';
  }
}
