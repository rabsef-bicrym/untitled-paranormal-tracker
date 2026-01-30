/**
 * Haptic feedback utility using Web Vibration API
 * Gracefully falls back if vibration is not supported
 */

/**
 * Check if vibration is supported
 */
function isVibrationSupported(): boolean {
  return 'vibrate' in navigator;
}

/**
 * Vibrate with pattern, returns false if not supported
 */
function vibrate(pattern: number | number[]): boolean {
  if (!isVibrationSupported()) {
    return false;
  }

  try {
    return navigator.vibrate(pattern);
  } catch (err) {
    console.warn('Vibration failed:', err);
    return false;
  }
}

/**
 * Light haptic feedback (button tap)
 * Duration: 10ms
 */
export function light(): void {
  vibrate(10);
}

/**
 * Medium haptic feedback (mode switch, selection)
 * Duration: 20ms
 */
export function medium(): void {
  vibrate(20);
}

/**
 * Success haptic feedback (story select, action complete)
 * Pattern: short-pause-long-pause-short
 */
export function success(): void {
  vibrate([10, 50, 10]);
}

/**
 * Error haptic feedback (failed action, validation error)
 * Pattern: long-pause-long
 */
export function error(): void {
  vibrate([20, 100, 20]);
}

/**
 * Stop all vibrations
 */
export function stop(): void {
  if (isVibrationSupported()) {
    navigator.vibrate(0);
  }
}

/**
 * Custom vibration pattern
 * @param pattern Single duration (ms) or array of durations [vibrate, pause, vibrate, ...]
 */
export function custom(pattern: number | number[]): void {
  vibrate(pattern);
}

// Export check for conditional behavior
export { isVibrationSupported };
