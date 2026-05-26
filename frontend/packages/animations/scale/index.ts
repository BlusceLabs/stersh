/**
 * Premium hardware-accelerated focal scaling entrance effect.
 * Syncs perfectly with the Watchfy ease-exo-out motion design profiles.
 */
export function scaleIn(element: HTMLElement, delay: number = 0): (() => void) | void {
  if (!element) return;

  // 1. Initialize composite GPU matrix layers
  element.style.opacity = "0";
  element.style.transform = "scale3d(0.92, 0.92, 1)";
  element.style.willChange = "opacity, transform";

  let timeoutId: number | null = null;
  let animationFrameId: number | null = null;

  const triggerAnimation = () => {
    // 2. Schedule state mutation with the browser's native compositing step
    animationFrameId = requestAnimationFrame(() => {
      element.style.transition = "opacity 500ms cubic-bezier(0.34, 1.56, 0.64, 1), transform 500ms cubic-bezier(0.34, 1.56, 0.64, 1)";
      element.style.opacity = "1";
      element.style.transform = "scale3d(1, 1, 1)";
      
      // 3. Clean up the style attributes on transition complete
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

  // Active disposal function to clear memory during fast view changes
  return () => {
    if (timeoutId) clearTimeout(timeoutId);
    if (animationFrameId) cancelAnimationFrame(animationFrameId);
  };
}