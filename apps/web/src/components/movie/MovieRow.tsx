import { ChevronLeft, ChevronRight } from "lucide-react"
import { useRef } from "react"
import { motion } from "framer-motion"
import { Link } from "@tanstack/react-router"

import { toSlug } from "@/utils/slug"
import { Button } from "@/components/ui/button"

interface Movie {
  id: number
  title: string
  posterPath: string
  mediaType?: string
  progress?: number
  season?: number
  episode?: number
}

interface Props {
  title: string
  movies: Movie[]
}

export function MovieRow({
  title,
  movies,
}: Props) {
  const rowRef = useRef<HTMLDivElement | null>(null)

  function scrollLeft() {
    rowRef.current?.scrollBy({ left: -1200, behavior: "smooth" })
  }

  function scrollRight() {
    rowRef.current?.scrollBy({ left: 1200, behavior: "smooth" })
  }

  return (
    <div className="relative">
      {/* TITLE */}
      <div className="mb-6 flex items-center justify-between px-6 md:px-16">
        <h2 className="text-2xl font-semibold tracking-tight">
          {title}
        </h2>

        <div className="flex gap-3">
          <Button
            variant="ghost"
            size="icon"
            onClick={scrollLeft}
            className="h-11 w-11 rounded-full border border-border/50 bg-secondary/30 backdrop-blur-3xl hover:bg-secondary hover:scale-110 transition-all duration-300"
          >
            <ChevronLeft size={20} />
          </Button>

          <Button
            variant="ghost"
            size="icon"
            onClick={scrollRight}
            className="h-11 w-11 rounded-full border border-border/50 bg-secondary/30 backdrop-blur-3xl hover:bg-secondary hover:scale-110 transition-all duration-300"
          >
            <ChevronRight size={20} />
          </Button>
        </div>
      </div>

      {/* ROW */}
      <div
        ref={rowRef}
        className="scrollbar-none flex gap-5 overflow-x-auto px-6 md:px-16"
      >
        {movies.map((movie) => {
          const isResume = movie.season !== undefined && movie.episode !== undefined
          const slug = toSlug(movie.title)
          const type = movie.mediaType || "movie"
          return (
            <Link
              key={movie.id}
              to={isResume
                ? "/watch/$type/$slug/$season/$episode"
                : "/details/$type/$slug"
              }
              params={isResume
                ? { type, slug, season: "sn" + movie.season, episode: "ep" + movie.episode }
                : { type, slug }
              }
            >
            <motion.div
              whileHover={{ scale: 1.05, y: -10 }}
              transition={{ duration: 0.35 }}
              className="group relative min-w-[220px] overflow-hidden rounded-[28px]"
            >
              {/* POSTER */}
              <img
                src={movie.posterPath}
                alt={movie.title}
                loading="lazy"
                decoding="async"
                className="h-[330px] w-[220px] object-cover"
              />

              {/* OVERLAY */}
              <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-transparent to-transparent opacity-0 transition-opacity duration-300 group-hover:opacity-100" />

              {/* PROGRESS */}
              {movie.progress !== undefined && movie.progress > 0 && movie.progress < 1 && (
                <div className="absolute bottom-0 left-0 right-0 h-1 bg-white/10">
                  <div
                    className="h-full bg-primary"
                    style={{ width: `${movie.progress * 100}%` }}
                  />
                </div>
              )}

              {/* TITLE */}
              <div className="absolute bottom-0 left-0 right-0 p-5 opacity-0 transition-all duration-300 group-hover:translate-y-0 group-hover:opacity-100">
                <h3 className="text-lg font-semibold">
                  {movie.title}
                </h3>
              </div>
            </motion.div>
          </Link>
          )
        })}
      </div>
    </div>
  )
}
