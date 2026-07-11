/** @jsxImportSource react */
// src/components/react/Modal.tsx
import { useEffect, useRef, type ReactNode } from "react"
import { motion, AnimatePresence } from "framer-motion"

export interface ModalProps {
  isOpen: boolean
  onClose: () => void
  children: ReactNode
  title?: string
}

export function Modal({ isOpen, onClose, children, title }: ModalProps) {
  const modalRef = useRef<HTMLDivElement>(null)

  // Manage focus handling and keyboard bindings safely
  useEffect(() => {
    if (!isOpen) return

    // 1. Lock document scrolling to prevent underlying layout shifting
    const originalStyle = document.body.style.overflow
    document.body.style.overflow = "hidden"

    // 2. Trap keyboard focus inside the active viewport modal array
    const focusableElementsString = 'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    const currentModal = modalRef.current

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose()
        return
      }

      if (e.key !== "Tab" || !currentModal) return

      const focusableElements = currentModal.querySelectorAll<HTMLElement>(focusableElementsString)
      const firstElement = focusableElements[0]
      const lastElement = focusableElements[focusableElements.length - 1]

      if (e.shiftKey) {
        // Tab backwards link check loop
        if (document.activeElement === firstElement && lastElement) {
          lastElement.focus()
          e.preventDefault()
        }
      } else {
        // Tab forwards link check loop
        if (document.activeElement === lastElement && firstElement) {
          firstElement.focus()
          e.preventDefault()
        }
      }
    }

    // Capture focus instantly on overlay arrival
    const timer = setTimeout(() => {
      const focusable = currentModal?.querySelectorAll<HTMLElement>(focusableElementsString)
      if (focusable && focusable.length > 0) {
        focusable[0].focus()
      }
    }, 50)

    window.addEventListener("keydown", handleKeyDown)

    // Cleanup and restore screen scrolling locks on unmount
    return () => {
      document.body.style.overflow = originalStyle
      window.removeEventListener("keydown", handleKeyDown)
      clearTimeout(timer)
    }
  }, [isOpen, onClose])

  return (
    <AnimatePresence>
      {isOpen && (
        <div 
          className="fixed inset-0 z-[9999] flex items-center justify-center p-4 sm:p-6"
          role="dialog"
          aria-modal="true"
          aria-labelledby={title ? "modal-title" : undefined}
        >
          {/* Hardware Accelerated Backdrop Cover */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.25, ease: "easeOut" }}
            className="absolute inset-0 bg-black/75 backdrop-blur-sm"
            onClick={onClose}
          />

          {/* Dialog Container Window Box */}
          <motion.div
            ref={modalRef}
            initial={{ opacity: 0, scale: 0.96, y: 8 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: 8 }}
            transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }} // Stersh cinematic ease-out curve
            className="
              relative
              z-10
              w-full
              max-w-lg
              rounded-2xl
              border
              border-zinc-800/80
              bg-[#0f1724]
              p-6
              sm:p-8
              shadow-2xl
              shadow-black/80
              outline-none
            "
          >
            {/* Context Close Anchor Switch Button */}
            <button
              onClick={onClose}
              className="absolute top-4 right-4 p-2 text-zinc-500 hover:text-white rounded-xl hover:bg-zinc-800/40 transition-all duration-200 cursor-pointer outline-none focus-visible:ring-2 focus-visible:ring-[#8B5CF6]/50"
              aria-label="Close modal content box"
            >
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2.5" stroke="currentColor" className="w-4 h-4">
                <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
              </svg>
            </button>

            {title && (
              <h2 id="modal-title" className="pr-8 mb-5 text-xl sm:text-2xl font-bold tracking-tight text-white">
                {title}
              </h2>
            )}

            <div className="text-zinc-300 text-sm sm:text-base leading-relaxed">
              {children}
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  )
}