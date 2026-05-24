export function slideInLeft(element: HTMLElement, delay: number = 0) {
  element.style.opacity = "0"
  element.style.transform = "translateX(-30px)"
  setTimeout(() => {
    element.style.transition = "opacity 0.5s ease, transform 0.5s ease"
    element.style.opacity = "1"
    element.style.transform = "translateX(0)"
  }, delay)
}

export function slideInRight(element: HTMLElement, delay: number = 0) {
  element.style.opacity = "0"
  element.style.transform = "translateX(30px)"
  setTimeout(() => {
    element.style.transition = "opacity 0.5s ease, transform 0.5s ease"
    element.style.opacity = "1"
    element.style.transform = "translateX(0)"
  }, delay)
}
