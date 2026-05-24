import { useEffect, useState } from "react"
import { ChevronRight } from "lucide-react"

import { getTrendingMovies } from "@/api/movies"
import { MovieCard } from "@/components/cards/MovieCard"

import { Movie } from "@/api/movies"

export function TrendingRow() {
  const [movies, setMovies] = useState<Movie[]>([])

  useEffect(() => {
    async function load() {
      try {
        const data = await getTrendingMovies()
        setMovies(data.results || [])
      } catch (err) {
        console.error(err)
      }
    }

    load()
  }, [])

  return (
    <section className="relative z-20 px-6 md:px-16">
      {/* HEADER */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h2
            className="
              text-2xl
              font-semibold
              tracking-[-0.04em]
              text-white
            "
          >
            Trending Now
          </h2>

          <p className="mt-1 text-sm text-white/45">
            Worldwide cinematic picks
          </p>
        </div>

        <button
          className="
            flex
            items-center
            gap-2
            text-sm
            text-white/45
            transition-colors
            duration-300
            hover:text-white
          "
        >
          View All

          <ChevronRight size={16} />
        </button>
      </div>

      {/* ROW */}
      <div
        className="
          scrollbar-none
          flex
          gap-5
          overflow-x-auto
          pb-4
        "
      >
        {movies.map((movie) => (
          <MovieCard
            key={movie.id}
            movie={movie}
          />
        ))}
      </div>
    </section>
  )
}
