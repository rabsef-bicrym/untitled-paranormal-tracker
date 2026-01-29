/**
 * Camera animation utility for smooth Three.js camera transitions
 */

import * as THREE from 'three';
import type { OrbitControls } from 'three/examples/jsm/controls/OrbitControls';

export type EasingFunction = (t: number) => number;

/**
 * Easing functions for camera animations
 */
export const Easing = {
  linear: (t: number) => t,
  easeInQuad: (t: number) => t * t,
  easeOutQuad: (t: number) => t * (2 - t),
  easeInOutQuad: (t: number) => (t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t),
  easeInCubic: (t: number) => t * t * t,
  easeOutCubic: (t: number) => --t * t * t + 1,
  easeInOutCubic: (t: number) =>
    t < 0.5 ? 4 * t * t * t : (t - 1) * (2 * t - 2) * (2 * t - 2) + 1,
};

export interface AnimationOptions {
  duration?: number; // milliseconds
  easing?: EasingFunction;
  onUpdate?: (progress: number) => void;
  onComplete?: () => void;
}

/**
 * Camera animator class for managing camera transitions
 */
export class CameraAnimator {
  private animationId: number | null = null;

  /**
   * Animate camera position to target
   */
  animateToPosition(
    camera: THREE.PerspectiveCamera,
    targetPos: THREE.Vector3,
    options: AnimationOptions = {}
  ): Promise<void> {
    const {
      duration = 1000,
      easing = Easing.easeOutCubic,
      onUpdate,
      onComplete,
    } = options;

    return new Promise((resolve) => {
      // Cancel any existing animation
      this.cancel();

      const startPos = camera.position.clone();
      const startTime = Date.now();

      const animate = () => {
        const now = Date.now();
        const elapsed = now - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const eased = easing(progress);

        camera.position.lerpVectors(startPos, targetPos, eased);

        if (onUpdate) {
          onUpdate(progress);
        }

        if (progress < 1) {
          this.animationId = requestAnimationFrame(animate);
        } else {
          this.animationId = null;
          if (onComplete) onComplete();
          resolve();
        }
      };

      animate();
    });
  }

  /**
   * Animate camera to look at target
   */
  animateToLookAt(
    camera: THREE.PerspectiveCamera,
    targetLookAt: THREE.Vector3,
    options: AnimationOptions = {}
  ): Promise<void> {
    const {
      duration = 1000,
      easing = Easing.easeOutCubic,
      onUpdate,
      onComplete,
    } = options;

    return new Promise((resolve) => {
      this.cancel();

      // Get current look-at direction
      const currentTarget = new THREE.Vector3();
      camera.getWorldDirection(currentTarget);
      currentTarget.multiplyScalar(10).add(camera.position);

      const startTime = Date.now();

      const animate = () => {
        const now = Date.now();
        const elapsed = now - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const eased = easing(progress);

        const tempTarget = new THREE.Vector3();
        tempTarget.lerpVectors(currentTarget, targetLookAt, eased);
        camera.lookAt(tempTarget);

        if (onUpdate) {
          onUpdate(progress);
        }

        if (progress < 1) {
          this.animationId = requestAnimationFrame(animate);
        } else {
          this.animationId = null;
          if (onComplete) onComplete();
          resolve();
        }
      };

      animate();
    });
  }

  /**
   * Reset camera to default position and look-at
   */
  resetCamera(
    camera: THREE.PerspectiveCamera,
    defaultPos: THREE.Vector3,
    defaultLookAt: THREE.Vector3 = new THREE.Vector3(0, 0, 0),
    options: AnimationOptions = {}
  ): Promise<void> {
    const { duration = 800, easing = Easing.easeInOutCubic } = options;

    return Promise.all([
      this.animateToPosition(camera, defaultPos, { duration, easing }),
      this.animateToLookAt(camera, defaultLookAt, { duration, easing }),
    ]).then(() => {});
  }

  /**
   * Animate camera and OrbitControls target together
   */
  animateWithControls(
    camera: THREE.PerspectiveCamera,
    controls: OrbitControls,
    targetPos: THREE.Vector3,
    targetLookAt: THREE.Vector3,
    options: AnimationOptions = {}
  ): Promise<void> {
    const {
      duration = 1000,
      easing = Easing.easeOutCubic,
      onUpdate,
      onComplete,
    } = options;

    return new Promise((resolve) => {
      this.cancel();

      const startPos = camera.position.clone();
      const startTarget = controls.target.clone();
      const startTime = Date.now();

      // Disable controls during animation
      controls.enabled = false;

      const animate = () => {
        const now = Date.now();
        const elapsed = now - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const eased = easing(progress);

        camera.position.lerpVectors(startPos, targetPos, eased);
        controls.target.lerpVectors(startTarget, targetLookAt, eased);
        controls.update();

        if (onUpdate) {
          onUpdate(progress);
        }

        if (progress < 1) {
          this.animationId = requestAnimationFrame(animate);
        } else {
          this.animationId = null;
          controls.enabled = true;
          if (onComplete) onComplete();
          resolve();
        }
      };

      animate();
    });
  }

  /**
   * Cancel current animation
   */
  cancel() {
    if (this.animationId !== null) {
      cancelAnimationFrame(this.animationId);
      this.animationId = null;
    }
  }
}

/**
 * Helper function to create a quick camera animation
 */
export function animateCamera(
  camera: THREE.PerspectiveCamera,
  targetPos: THREE.Vector3,
  duration: number = 1000
): Promise<void> {
  const animator = new CameraAnimator();
  return animator.animateToPosition(camera, targetPos, { duration });
}
