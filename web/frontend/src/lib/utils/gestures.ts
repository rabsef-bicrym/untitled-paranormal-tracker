/**
 * Touch gesture detection utility
 * Detects swipes, pinches, long-press, and double-tap
 */

export interface Point {
  x: number;
  y: number;
}

export interface GestureCallbacks {
  onSwipeLeft?: () => void;
  onSwipeRight?: () => void;
  onSwipeUp?: () => void;
  onSwipeDown?: () => void;
  onPinch?: (scale: number, center: Point) => void;
  onLongPress?: (point: Point) => void;
  onDoubleTap?: (point: Point) => void;
}

interface TouchData {
  startX: number;
  startY: number;
  startTime: number;
  lastTap: number;
  tapCount: number;
  longPressTimer?: ReturnType<typeof setTimeout>;
  initialDistance?: number;
}

const SWIPE_THRESHOLD = 50; // pixels
const SWIPE_VELOCITY_THRESHOLD = 0.5; // pixels per ms
const LONG_PRESS_DURATION = 500; // ms
const DOUBLE_TAP_DELAY = 300; // ms

/**
 * Creates a gesture handler for a DOM element
 * Returns cleanup function to remove listeners
 */
export function createGestureHandler(
  element: HTMLElement,
  callbacks: GestureCallbacks
): () => void {
  const touchData: TouchData = {
    startX: 0,
    startY: 0,
    startTime: 0,
    lastTap: 0,
    tapCount: 0,
  };

  function getTouchPoint(touch: Touch): Point {
    return {
      x: touch.clientX,
      y: touch.clientY,
    };
  }

  function getTouchDistance(touch1: Touch, touch2: Touch): number {
    const dx = touch2.clientX - touch1.clientX;
    const dy = touch2.clientY - touch1.clientY;
    return Math.sqrt(dx * dx + dy * dy);
  }

  function getTouchCenter(touch1: Touch, touch2: Touch): Point {
    return {
      x: (touch1.clientX + touch2.clientX) / 2,
      y: (touch1.clientY + touch2.clientY) / 2,
    };
  }

  function handleTouchStart(e: TouchEvent) {
    const touches = e.touches;

    if (touches.length === 1) {
      // Single touch - potential swipe, long-press, or tap
      const touch = touches[0];
      touchData.startX = touch.clientX;
      touchData.startY = touch.clientY;
      touchData.startTime = Date.now();

      // Start long-press timer
      touchData.longPressTimer = setTimeout(() => {
        if (callbacks.onLongPress) {
          callbacks.onLongPress(getTouchPoint(touch));
        }
      }, LONG_PRESS_DURATION);
    } else if (touches.length === 2) {
      // Two-finger touch - potential pinch
      touchData.initialDistance = getTouchDistance(touches[0], touches[1]);

      // Cancel long-press on multi-touch
      if (touchData.longPressTimer) {
        clearTimeout(touchData.longPressTimer);
        touchData.longPressTimer = undefined;
      }
    }
  }

  function handleTouchMove(e: TouchEvent) {
    const touches = e.touches;

    // Cancel long-press if finger moves
    if (touchData.longPressTimer) {
      clearTimeout(touchData.longPressTimer);
      touchData.longPressTimer = undefined;
    }

    if (touches.length === 2 && touchData.initialDistance !== undefined) {
      // Pinch gesture
      const currentDistance = getTouchDistance(touches[0], touches[1]);
      const scale = currentDistance / touchData.initialDistance;
      const center = getTouchCenter(touches[0], touches[1]);

      if (callbacks.onPinch) {
        callbacks.onPinch(scale, center);
        // Prevent default zoom
        e.preventDefault();
      }

      touchData.initialDistance = currentDistance;
    }
  }

  function handleTouchEnd(e: TouchEvent) {
    // Cancel long-press timer
    if (touchData.longPressTimer) {
      clearTimeout(touchData.longPressTimer);
      touchData.longPressTimer = undefined;
    }

    const touch = e.changedTouches[0];
    if (!touch) return;

    const endX = touch.clientX;
    const endY = touch.clientY;
    const endTime = Date.now();

    const deltaX = endX - touchData.startX;
    const deltaY = endY - touchData.startY;
    const deltaTime = endTime - touchData.startTime;
    const distance = Math.sqrt(deltaX * deltaX + deltaY * deltaY);

    // Check for swipe
    if (distance > SWIPE_THRESHOLD && deltaTime > 0) {
      const velocity = distance / deltaTime;

      if (velocity > SWIPE_VELOCITY_THRESHOLD) {
        const angle = Math.atan2(deltaY, deltaX) * (180 / Math.PI);

        // Determine swipe direction (8 directions collapsed to 4)
        if (angle >= -45 && angle < 45) {
          // Right
          if (callbacks.onSwipeRight) callbacks.onSwipeRight();
        } else if (angle >= 45 && angle < 135) {
          // Down
          if (callbacks.onSwipeDown) callbacks.onSwipeDown();
        } else if (angle >= -135 && angle < -45) {
          // Up
          if (callbacks.onSwipeUp) callbacks.onSwipeUp();
        } else {
          // Left (angle < -135 or angle >= 135)
          if (callbacks.onSwipeLeft) callbacks.onSwipeLeft();
        }
      }
    } else if (distance < 10 && deltaTime < 300) {
      // Tap (short touch with minimal movement)
      const now = Date.now();

      if (now - touchData.lastTap < DOUBLE_TAP_DELAY) {
        // Double tap
        if (callbacks.onDoubleTap) {
          callbacks.onDoubleTap(getTouchPoint(touch));
        }
        touchData.tapCount = 0;
      } else {
        touchData.tapCount = 1;
        touchData.lastTap = now;
      }
    }

    // Reset pinch data
    touchData.initialDistance = undefined;
  }

  function handleTouchCancel() {
    // Clean up on touch cancel
    if (touchData.longPressTimer) {
      clearTimeout(touchData.longPressTimer);
      touchData.longPressTimer = undefined;
    }
    touchData.initialDistance = undefined;
  }

  // Prevent default behaviors
  function preventDefault(e: Event) {
    // Prevent pull-to-refresh
    if ((e.target as HTMLElement).classList.contains('prevent-pull-refresh')) {
      e.preventDefault();
    }
  }

  // Add event listeners
  element.addEventListener('touchstart', handleTouchStart, { passive: false });
  element.addEventListener('touchmove', handleTouchMove, { passive: false });
  element.addEventListener('touchend', handleTouchEnd, { passive: true });
  element.addEventListener('touchcancel', handleTouchCancel, { passive: true });

  // Cleanup function
  return () => {
    element.removeEventListener('touchstart', handleTouchStart);
    element.removeEventListener('touchmove', handleTouchMove);
    element.removeEventListener('touchend', handleTouchEnd);
    element.removeEventListener('touchcancel', handleTouchCancel);

    if (touchData.longPressTimer) {
      clearTimeout(touchData.longPressTimer);
    }
  };
}

/**
 * Svelte action for gesture handling
 * Usage: <div use:gesture={{ onSwipeLeft: () => console.log('swiped left') }} />
 */
export function gesture(node: HTMLElement, callbacks: GestureCallbacks) {
  const cleanup = createGestureHandler(node, callbacks);

  return {
    destroy: cleanup,
  };
}
