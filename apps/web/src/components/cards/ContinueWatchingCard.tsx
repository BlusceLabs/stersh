import { motion } from "framer-motion"
import { Link } from "@tanstack/react-router"

import { toSlug } from "@/utils/slug"

interface ContinueWatchingCardProps {
  id: number
  title: string
  posterPath: string
  progress: number
  mediaType?: string
}

export function ContinueWatchingCard({
  title,
  posterPath,
  progress,
  mediaType,
}: ContinueWatchingCardProps) {
  return (
    <Link to="/watch/$type/$slug" params={{ type: mediaType || "movie", slug: toSlug(title) }}>
      <motion.div
        whileHover={{ scale: 1.05 }}
        transition={{ duration: 0.35 }}
        className="group relative min-w-[280px] overflow-hidden rounded-[20px]"
      >
        <img
          src={posterPath}
          alt={title}
          loading="lazy"
          decoding="async"
          className="h-[160px] w-[280px] object-cover"
        />
        <div
          className="
            absolute inset-0
            bg-gradient-to-t
            from-black/80
            to-transparent
          "
        />
        <div className="absolute bottom-3 left-3 right-3">
          <h3 className="text-sm font-semibold">{title}</h3>
          {/* Progress bar */}
          <div className="mt-2 h-1 overflow-hidden rounded-full bg-white/20">
            <div
              className="h-full rounded-full bg-[#8B5CF6]"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      </motion.div>
    </Link>
  )
}
