/**
 * Device detection utility
 * Detects device capabilities for performance optimization
 */

export type GPUTier = 'low' | 'medium' | 'high';

export interface DeviceProfile {
  isMobile: boolean;
  isTablet: boolean;
  gpuTier: GPUTier;
  hasLowMemory: boolean;
  prefersReducedMotion: boolean;
  screenWidth: number;
  screenHeight: number;
  pixelRatio: number;
}

let cachedProfile: DeviceProfile | null = null;

/**
 * Detect GPU tier based on WebGL capabilities
 */
function detectGPUTier(): GPUTier {
  const canvas = document.createElement('canvas');
  const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');

  if (!gl) {
    return 'low'; // No WebGL support
  }

  try {
    const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
    if (debugInfo) {
      const renderer = gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL);

      // Check for high-end GPUs
      if (
        renderer.includes('NVIDIA') ||
        renderer.includes('AMD') ||
        renderer.includes('Apple M') ||
        renderer.includes('Apple GPU')
      ) {
        return 'high';
      }

      // Check for integrated/low-end GPUs
      if (
        renderer.includes('Intel') ||
        renderer.includes('Mali') ||
        renderer.includes('Adreno 5') ||
        renderer.includes('PowerVR')
      ) {
        return 'low';
      }
    }

    // Fallback: Check MAX_TEXTURE_SIZE
    const maxTextureSize = gl.getParameter(gl.MAX_TEXTURE_SIZE);

    if (maxTextureSize >= 16384) {
      return 'high';
    } else if (maxTextureSize >= 8192) {
      return 'medium';
    } else {
      return 'low';
    }
  } catch (err) {
    console.warn('GPU tier detection failed:', err);
    return 'medium'; // Safe default
  }
}

/**
 * Check if device has low memory (<4GB)
 */
function hasLowMemory(): boolean {
  // @ts-ignore - deviceMemory is not in TypeScript types yet
  const deviceMemory = navigator.deviceMemory;

  if (deviceMemory !== undefined) {
    return deviceMemory < 4;
  }

  // Fallback: Assume mobile devices have lower memory
  return /Android|iPhone|iPad|iPod/.test(navigator.userAgent);
}

/**
 * Check if user prefers reduced motion
 */
function prefersReducedMotion(): boolean {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

/**
 * Detect if device is mobile based on screen width
 */
function isMobile(): boolean {
  return window.innerWidth < 1024;
}

/**
 * Detect if device is tablet based on screen width
 */
function isTablet(): boolean {
  const width = window.innerWidth;
  return width >= 768 && width < 1024;
}

/**
 * Detect device capabilities
 * Returns cached result on subsequent calls
 */
export function detectDevice(): DeviceProfile {
  if (cachedProfile) {
    return cachedProfile;
  }

  const profile: DeviceProfile = {
    isMobile: isMobile(),
    isTablet: isTablet(),
    gpuTier: detectGPUTier(),
    hasLowMemory: hasLowMemory(),
    prefersReducedMotion: prefersReducedMotion(),
    screenWidth: window.innerWidth,
    screenHeight: window.innerHeight,
    pixelRatio: window.devicePixelRatio || 1,
  };

  cachedProfile = profile;
  return profile;
}

/**
 * Clear cached device profile (useful for testing or window resize)
 */
export function clearDeviceCache() {
  cachedProfile = null;
}

/**
 * Get a human-readable summary of the device profile
 */
export function getDeviceSummary(profile: DeviceProfile): string {
  const deviceType = profile.isMobile ? 'Mobile' : profile.isTablet ? 'Tablet' : 'Desktop';
  const gpuTier = profile.gpuTier.charAt(0).toUpperCase() + profile.gpuTier.slice(1);
  const memory = profile.hasLowMemory ? 'Low Memory' : 'Sufficient Memory';

  return `${deviceType} | GPU: ${gpuTier} | ${memory} | ${profile.screenWidth}x${profile.screenHeight} @${profile.pixelRatio}x`;
}
