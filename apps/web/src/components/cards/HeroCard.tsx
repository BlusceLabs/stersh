import { motion } from "framer-motion"
import { Link } from "@tanstack/react-router"

import { toSlug } from "@/utils/slug"

interface HeroCardProps {
  id: number
  title: string
  backdropPath: string
  logoPath?: string
}

export function HeroCard({
  title,
  backdropPath,
  logoPath,
}: HeroCardProps) {
  return (
    <Link to="/details/$type/$slug" params={{ type: "movie", slug: toSlug(title) }}>
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.8 }}
        className="relative h-[70vh] min-w-[90vw] overflow-hidden rounded-[32px]"
      >
        <img
          src={backdropPath}
          alt={title}
          loading="lazy"
          decoding="async"
          className="h-full w-full object-cover"
        />
        <div
          className="
            absolute inset-0
            bg-gradient-to-t
            from-black/90
            via-transparent
            to-transparent
          "
        />
        <div className="absolute bottom-10 left-8 max-w-xl">
          {logoPath ? (
            <img
              src={logoPath}
              alt={title}
              loading="lazy"
              decoding="async"
              className="mb-6 max-h-20 object-contain"
            />
          ) : (
            <h2 className="mb-4 text-4xl font-bold">{title}</h2>
          )}
        </div>
      </motion.div>
    </Link>
  )
}
