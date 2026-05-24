import { motion } from "framer-motion"
import { Link } from "@tanstack/react-router"

import { toSlug } from "@/utils/slug"

interface AnimeCardProps {
  id: number
  title: string
  posterPath: string
}

export function AnimeCard({ title, posterPath }: AnimeCardProps) {
  return (
    <Link to="/details/$type/$slug" params={{ type: "movie", slug: toSlug(title) }}>
      <motion.div
        whileHover={{ scale: 1.05, y: -10 }}
        transition={{ duration: 0.35 }}
        className="group relative min-w-[180px] overflow-hidden rounded-[24px]"
      >
        <img
          src={posterPath}
          alt={title}
          loading="lazy"
          decoding="async"
          className="h-[270px] w-[180px] object-cover"
        />
        <div
          className="
            absolute inset-0
            bg-gradient-to-t
            from-black/90
            via-transparent
            to-transparent
            opacity-0
            transition-opacity
            duration-300
            group-hover:opacity-100
          "
        />
        <div
          className="
            absolute bottom-0 left-0 right-0
            p-4
            opacity-0
            translate-y-2
            transition-all
            duration-300
            group-hover:opacity-100
            group-hover:translate-y-0
          "
        >
          <h3 className="text-sm font-semibold">{title}</h3>
        </div>
      </motion.div>
    </Link>
  )
}
