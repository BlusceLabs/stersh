/**
 * Clean hardware-accelerated fade-and-rise entrance effect.
 * Utilizes requestAnimationFrame loops to guarantee layout frame alignment.
 */
export function fadeInUp(element: HTMLElement, delay: number = 0): (() => void) | void {
  if (!element) return;

  // 1. Force GPU acceleration layers using transform primitives
  element.style.opacity = "0";
  element.style.transform = "translateY(24px) translateZ(0)";
  element.style.willChange = "opacity, transform";

  let timeoutId: number | null = null;
  let animationFrameId: number | null = null;

  const triggerAnimation = () => {
    // 2. Align state changes with the browser's next paint pass
    animationFrameId = requestAnimationFrame(() => {
      element.style.transition = "opacity 600ms cubic-bezier(0.16, 1, 0.3, 1), transform 600ms cubic-bezier(0.16, 1, 0.3, 1)";
      element.style.opacity = "1";
      element.style.transform = "translateY(0) translateZ(0)";
      
      // 3. Clean up the style attributes once the transition ends
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

  // Return a cleanup/kill function to protect against SSR memory leaks or page transitions
  return () => {
    if (timeoutId) clearTimeout(timeoutId);
    if (animationFrameId) cancelAnimationFrame(animationFrameId);
  };
}

/**
 * Clean hardware-accelerated fade-and-descend entrance effect.
 */
export function fadeInDown(element: HTMLElement, delay: number = 0): (() => void) | void {
  if (!element) return;

  element.style.opacity = "0";
  element.style.transform = "translateY(-24px) translateZ(0)";
  element.style.willChange = "opacity, transform";

  let timeoutId: number | null = null;
  let animationFrameId: number | null = null;

  const triggerAnimation = () => {
    animationFrameId = requestAnimationFrame(() => {
      element.style.transition = "opacity 600ms cubic-bezier(0.16, 1, 0.3, 1), transform 600ms cubic-bezier(0.16, 1, 0.3, 1)";
      element.style.opacity = "1";
      element.style.transform = "translateY(0) translateZ(0)";
      
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

/**
 * High-End Declarative Class Intersector
 * Perfect for animating movie card lists cleanly as they scroll into view.
 */
export function observeEntranceGrid(container: HTMLElement) {
  if (!container) return;
  
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        const target = entry.target as HTMLElement;
        const delay = parseInt(target.dataset.animationDelay || '0', 10);
        
        fadeInUp(target, delay);
        observer.unobserve(target);
      }
    });
  }, { threshold: 0.05, rootMargin: '0px 0px -50px 0px' });

  // Scan and register matching dynamic element tracks
  const children = container.querySelectorAll('[data-animate]');
  children.forEach(child => observer.observe(child));
  
  return () => observer.disconnect();
}