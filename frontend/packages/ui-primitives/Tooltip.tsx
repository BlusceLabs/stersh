/** @jsxImportSource react */
// src/components/react/Tooltip.tsx
import { useState, useRef, type ReactNode } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { useFloating, autoUpdate, offset, flip, shift, arrow } from "@floating-ui/react"

export interface TooltipProps {
  children: ReactNode
  content: string
  /** Supports positioning overrides if a screen layout demands specific direction mapping */
  placement?: "top" | "bottom" | "left" | "right"
}

export function Tooltip({ children, content, placement = "top" }: TooltipProps) {
  const [isOpen, setIsOpen] = useState(false)
  const arrowRef = useRef<HTMLDivElement>(null)

  // Floating UI positioning controller
  const { refs, floatingStyles, placement: finalPlacement } = useFloating({
    open: isOpen,
    onOpenChange: setIsOpen,
    placement,
    whileElementsMounted: autoUpdate, // Continuous viewport shift tracking flag
    middleware: [
      offset(8), // Explicit spacing cushion from target anchor element
      flip({ fallbackAxisSideDirection: "start" }), // Automatically flips down if top blocks edge
      shift({ padding: 12 }), // Shifts along the viewport edge to prevent boundary clipping
      arrow({ element: arrowRef }) // Dynamically locks your caret indicator pin
    ]
  })

  // Safe interaction hooks to handle touch profiles
  const showTooltip = () => setIsOpen(true)
  const hideTooltip = () => setIsOpen(false)

  return (
    <>
      {/* Anchor Target Layer */}
      <div
        ref={refs.setReference}
        className="inline-block"
        onMouseEnter={showTooltip}
        onMouseLeave={hideTooltip}
        onFocus={showTooltip}
        onBlur={hideTooltip}
        onTouchStart={(e) => {
          e.preventDefault() // Prevents sticky link double-taps on mobile
          showTooltip()
        }}
        onTouchEnd={hideTooltip}
        aria-describedby="watchfy-tooltip-overlay"
      >
        {children}
      </div>

      {/* Floating Animated Card Overlay Window */}
      <AnimatePresence>
        {isOpen && (
          <div
            ref={refs.setFloating}
            style={floatingStyles}
            className="z-[9999] pointer-events-none"
            id="watchfy-tooltip-overlay"
            role="tooltip"
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.94 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.94 }}
              transition={{ duration: 0.18, ease: [0.16, 1, 0.3, 1] }} // Watchfy ease-exo-out
              className="
                relative
                rounded-xl
                border
                border-zinc-800/80
                bg-[#1a2332]
                px-3
                py-1.5
                text-xs
                font-semibold
                tracking-wide
                text-zinc-200
                shadow-xl
                shadow-black/40
                backdrop-blur-md
                whitespace-nowrap
              "
            >
              {content}

              {/* Dynamic Placement Pointer Arrow Caret Pin */}
              <div
                ref={arrowRef}
                className="absolute w-2 h-2 bg-[#1a2332] border-zinc-800/80 rotate-45"
                style={{
                  left: "0px",
                  top: "0px",
                  // Dynamically invert caret borders depending on where the bubble flips
                  borderBottomWidth: finalPlacement.startsWith("top") ? "1px" : "0px",
                  borderRightWidth: finalPlacement.startsWith("top") ? "1px" : "0px",
                  borderTopWidth: finalPlacement.startsWith("bottom") ? "1px" : "0px",
                  borderLeftWidth: finalPlacement.startsWith("bottom") ? "1px" : "0px",
                }}
              />
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </>
  )
}