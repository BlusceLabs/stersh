import { motion } from "framer-motion"
import { Play, Star } from "lucide-react"
import { Link } from "@tanstack/react-router"

import { toSlug } from "@/utils/slug"
import { Badge } from "@/components/ui/badge"

interface Props {
  movie: {
    id: number
    title: string
    posterPath: string
    backdropPath?: string
    rating?: number
    year?: string
    mediaType?: string
  }
}

export function MovieCard({ movie }: Props) {
  return (
    <Link to="/details/$type/$slug" params={{ type: movie.mediaType || "movie", slug: toSlug(movie.title) }}>
      <motion.div
        whileHover={{ y: -10, scale: 1.03 }}
        transition={{ type: "spring", stiffness: 220, damping: 20 }}
        className="group relative min-w-[180px] overflow-hidden rounded-[28px]"
      >
        {/* POSTER */}
        <div className="relative overflow-hidden rounded-[28px]">
          <img
            src={movie.posterPath}
            alt={movie.title}
            loading="lazy"
            decoding="async"
            className="h-[270px] w-[180px] object-cover transition-transform duration-700 group-hover:scale-110"
          />

          {/* OVERLAY */}
          <div className="absolute inset-0 bg-gradient-to-t from-black via-black/10 to-transparent opacity-90" />

          {/* MEDIA TYPE BADGE */}
          {movie.mediaType && movie.mediaType !== "movie" && (
            <Badge
              variant="secondary"
              className="absolute left-3 top-3 z-10 rounded-full bg-black/50 text-white/80 backdrop-blur-xl border-none text-[10px] uppercase tracking-wide"
            >
              {movie.mediaType}
            </Badge>
          )}

          {/* GLOW */}
          <div className="absolute inset-0 opacity-0 transition-opacity duration-500 group-hover:opacity-100 bg-primary/10" />

          {/* PLAY BUTTON */}
          <motion.div
            initial={{ opacity: 0, scale: 0.7 }}
            whileHover={{ opacity: 1, scale: 1 }}
            className="absolute inset-0 flex items-center justify-center"
          >
            <div className="flex h-16 w-16 items-center justify-center rounded-full border border-white/10 bg-white/10 backdrop-blur-2xl">
              <Play size={22} fill="white" className="ml-1" />
            </div>
          </motion.div>

          {/* RATING */}
          {movie.rating !== undefined && (
            <Badge
              variant="secondary"
              className="absolute right-3 top-3 flex items-center gap-1 rounded-full bg-black/40 text-white/85 backdrop-blur-xl border-none text-xs"
            >
              <Star size={12} className="text-primary" fill="currentColor" />
              {movie.rating.toFixed(1)}
            </Badge>
          )}
        </div>

        {/* META */}
        <div className="px-2 pt-4">
          <h3 className="line-clamp-1 text-[15px] font-medium tracking-tight text-foreground">
            {movie.title}
          </h3>
          <p className="mt-1 text-sm text-muted-foreground">
            {movie.year || "Movie"}
          </p>
        </div>

        {/* BLOOM */}
        <div className="pointer-events-none absolute inset-0 rounded-[28px] opacity-0 blur-3xl transition-opacity duration-500 group-hover:opacity-100 bg-primary/20" />
      </motion.div>
    </Link>
  )
}
