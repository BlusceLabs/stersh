import { useCallback, useEffect, useMemo, useState } from "react"
import { motion } from "framer-motion"
import { ChevronRight, Play } from "lucide-react"
import { useNavigate } from "@tanstack/react-router"

import { getHomepage, type HomepageResponse } from "@/api/home"
import { toSlug } from "@/utils/slug"

import { useContinueWatching } from "@/stores/continue"
import { AmbientBackground } from "@/components/cinematic/AmbientBackground/AmbientBackground"
import { MovieRow } from "@/components/movie/MovieRow"
import { HeroPlayer } from "@/components/hero/HeroPlayer"
import { HomeSkeleton } from "@/components/shared/LoadingSkeleton"

import { Button } from "@/components/ui/button"

interface HeroMovie {
  id: number
  title: string
  overview: string
  backdropPath: string
  logoPath: string
  trailerKey: string
}

export default function HomePage() {
  const navigate = useNavigate()
  const continueWatching = useContinueWatching((s) => s.items)
  const [heroMovies, setHeroMovies] = useState<HeroMovie[]>([])
  const [rows, setRows] = useState<HomepageResponse["rows"]>([])
  const [currentHero, setCurrentHero] = useState(0)
  const [error, setError] = useState<Error | null>(null)

  const load = useCallback(async () => {
    try {
      setError(null)
      const data = await getHomepage()
      setHeroMovies(data.hero ?? [])
      setRows(data.rows ?? [])
    } catch (err) {
      console.error(err)
      setError(err instanceof Error ? err : new Error("Failed to load homepage"))
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const activeHero = useMemo(() => {
    return heroMovies[currentHero]
  }, [heroMovies, currentHero])

  function handleTrailerEnded() {
    if (heroMovies.length === 0) return
    setCurrentHero((prev) => {
      if (prev >= heroMovies.length - 1) return 0
      return prev + 1
    })
  }

  if (error) {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center bg-background text-foreground">
        <div className="text-center">
          <div className="mx-auto mb-6 flex h-20 w-20 items-center justify-center rounded-full bg-destructive/10">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-10 w-10 text-destructive">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
          </div>
          <h2 className="text-2xl font-semibold">Failed to load homepage</h2>
          <p className="mt-3 text-muted-foreground">{error.message}</p>
          <Button onClick={load} className="mt-8 rounded-full px-8">
            Try Again
          </Button>
        </div>
      </main>
    )
  }

  if (!activeHero) {
    return <HomeSkeleton />
  }

  return (
    <main className="relative min-h-screen overflow-hidden bg-background text-foreground">
      <AmbientBackground />

      {/* HERO */}
      <section className="relative h-screen overflow-hidden">
        <HeroPlayer
          trailerKey={activeHero.trailerKey}
          backdropPath={activeHero.backdropPath}
          title={activeHero.title}
          onEnded={handleTrailerEnded}
        />

        <div className="absolute inset-0 bg-gradient-to-r from-background via-background/50 to-transparent" />
        <div className="absolute inset-0 bg-gradient-to-t from-background via-transparent to-transparent" />

        <div className="relative z-20 flex h-full items-end px-6 pb-44 md:px-16">
          <motion.div
            key={activeHero.id}
            initial={{ opacity: 0, y: 80 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 1, ease: [0.22, 1, 0.36, 1] }}
            className="max-w-2xl"
          >
            {activeHero.logoPath ? (
              <img
                src={activeHero.logoPath}
                alt={activeHero.title}
                loading="lazy"
                decoding="async"
                className="mb-8 max-h-40 max-w-[520px] object-contain"
              />
            ) : (
              <h1 className="text-5xl font-bold tracking-tight md:text-7xl">
                {activeHero.title}
              </h1>
            )}

            <p className="max-w-xl text-base leading-8 text-muted-foreground md:text-lg">
              {activeHero.overview}
            </p>

            <div className="mt-10 flex gap-4">
              <Button
                size="lg"
                className="rounded-full bg-gradient-to-r from-primary to-cyan-500 text-primary-foreground hover:opacity-90 gap-2 px-8"
                onClick={() => {
                  navigate({
                    to: "/watch/$type/$slug",
                    params: { type: "movie", slug: toSlug(activeHero.title) },
                  })
                }}
              >
                <Play size={18} fill="white" />
                Watch Now
              </Button>

              <Button
                size="lg"
                variant="outline"
                className="rounded-full gap-2 px-8 backdrop-blur-3xl"
                onClick={() => {
                  navigate({
                    to: "/details/$type/$slug",
                    params: { type: "movie", slug: toSlug(activeHero.title) },
                  })
                }}
              >
                More Info
                <ChevronRight size={18} />
              </Button>
            </div>
          </motion.div>
        </div>
      </section>

      {/* ROWS */}
      <section className="relative z-20 -mt-28 space-y-14 pb-40">
        {continueWatching.length > 0 && (
          <MovieRow
            title="Continue Watching"
            movies={continueWatching.map((item) => ({
              id: item.id,
              title: item.title,
              posterPath: item.posterPath,
              mediaType: item.mediaType,
              progress: item.duration > 0 ? item.currentTime / item.duration : 0,
              season: item.season,
              episode: item.episode,
            }))}
          />
        )}

        {rows.map((row) => (
          <MovieRow
            key={row.id}
            title={row.title}
            movies={row.items}
          />
        ))}
      </section>
    </main>
  )
}
