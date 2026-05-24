import { ReactNode, useState } from "react"
import { motion } from "framer-motion"

interface TooltipProps {
  children: ReactNode
  content: string
}

export function Tooltip({ children, content }: TooltipProps) {
  const [isVisible, setIsVisible] = useState(false)

  return (
    <div
      className="relative inline-block"
      onMouseEnter={() => setIsVisible(true)}
      onMouseLeave={() => setIsVisible(false)}
    >
      {children}
      {isVisible && (
        <motion.div
          initial={{ opacity: 0, y: 5 }}
          animate={{ opacity: 1, y: 0 }}
          className="
            absolute
            bottom-full
            left-1/2
            -translate-x-1/2
            mb-2
            whitespace-nowrap
            rounded-lg
            bg-white/10
            px-3
            py-1.5
            text-sm
            text-white
            backdrop-blur-xl
          "
        >
          {content}
        </motion.div>
      )}
    </div>
  )
}
