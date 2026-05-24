export function fadeInUp(element: HTMLElement, delay: number = 0) {
  element.style.opacity = "0"
  element.style.transform = "translateY(20px)"
  setTimeout(() => {
    element.style.transition = "opacity 0.5s ease, transform 0.5s ease"
    element.style.opacity = "1"
    element.style.transform = "translateY(0)"
  }, delay)
}

export function fadeInDown(element: HTMLElement, delay: number = 0) {
  element.style.opacity = "0"
  element.style.transform = "translateY(-20px)"
  setTimeout(() => {
    element.style.transition = "opacity 0.5s ease, transform 0.5s ease"
    element.style.opacity = "1"
    element.style.transform = "translateY(0)"
  }, delay)
}
