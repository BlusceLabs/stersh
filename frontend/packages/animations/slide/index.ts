// src/lib/animations.ts

/**
 * Premium hardware-accelerated horizontal slide-in from the left.
 * Optimizes mobile rendering performance using GPU compositing layers.
 */
export function slideInLeft(element: HTMLElement, delay: number = 0): (() => void) | void {
  if (!element) return;

  // 1. Force the layout onto its own hardware GPU layer
  element.style.opacity = "0";
  element.style.transform = "translate3d(-32px, 0, 0)";
  element.style.willChange = "opacity, transform";

  let timeoutId: number | null = null;
  let animationFrameId: number | null = null;

  const triggerAnimation = () => {
    // 2. Sync style updates with the browser's next paint pass
    animationFrameId = requestAnimationFrame(() => {
      element.style.transition = "opacity 600ms cubic-bezier(0.16, 1, 0.3, 1), transform 600ms cubic-bezier(0.16, 1, 0.3, 1)";
      element.style.opacity = "1";
      element.style.transform = "translate3d(0, 0, 0)";
      
      // 3. Clean up performance tracking properties on completion
      element.addEventListener('transitionend', function handleEnd() {
        element.style.willChange = "";
        element.removeEventListener('transitionend', handleEnd);
      }, { passive: true });
    });
  };

  if (delay > 0) {
    timeoutId = window.setTimeout(triggerAnimation, delay);
  } else {
    triggerAnimation();
  }

  // Active disposal function to prevent memory leaks during rapid page changes
  return () => {
    if (timeoutId) clearTimeout(timeoutId);
    if (animationFrameId) cancelAnimationFrame(animationFrameId);
  };
}

/**
 * Premium hardware-accelerated horizontal slide-in from the right.
 * Perfect for revealing detailed contextual trays or secondary feature slides.
 */
export function slideInRight(element: HTMLElement, delay: number = 0): (() => void) | void {
  if (!element) return;

  element.style.opacity = "0";
  element.style.transform = "translate3d(32px, 0, 0)";
  element.style.willChange = "opacity, transform";

  let timeoutId: number | null = null;
  let animationFrameId: number | null = null;

  const triggerAnimation = () => {
    animationFrameId = requestAnimationFrame(() => {
      element.style.transition = "opacity 600ms cubic-bezier(0.16, 1, 0.3, 1), transform 600ms cubic-bezier(0.16, 1, 0.3, 1)";
      element.style.opacity = "1";
      element.style.transform = "translate3d(0, 0, 0)";
      
      element.addEventListener('transitionend', function handleEnd() {
        element.style.willChange = "";
        element.removeEventListener('transitionend', handleEnd);
      }, { passive: true });
    });
  };

  if (delay > 0) {
    timeoutId = window.setTimeout(triggerAnimation, delay);
  } else {
    triggerAnimation();
  }

  return () => {
    if (timeoutId) clearTimeout(timeoutId);
    if (animationFrameId) cancelAnimationFrame(animationFrameId);
  };
}