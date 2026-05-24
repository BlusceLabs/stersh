export function scaleIn(element: HTMLElement, delay: number = 0) {
  element.style.opacity = "0"
  element.style.transform = "scale(0.9)"
  setTimeout(() => {
    element.style.transition = "opacity 0.4s ease, transform 0.4s ease"
    element.style.opacity = "1"
    element.style.transform = "scale(1)"
  }, delay)
}
