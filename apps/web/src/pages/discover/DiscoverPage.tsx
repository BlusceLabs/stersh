import { useCallback, useEffect, useState } from "react"
import { motion } from "framer-motion"
import { getHomepage, type HomepageResponse } from "@/api/home"
import { MovieCard } from "@/components/cards/MovieCard"
import { AmbientBackground } from "@/components/cinematic/AmbientBackground/AmbientBackground"
import { HomeSkeleton } from "@/components/shared/LoadingSkeleton"

import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

const FILTERS = ["All", "Movies", "TV Shows"]

export default function DiscoverPage() {
  const [rows, setRows] = useState<HomepageResponse["rows"]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)
  const [activeFilter, setActiveFilter] = useState("All")

  const load = useCallback(async () => {
    try {
      setError(null)
      const data = await getHomepage()
      setRows(data.rows ?? [])
    } catch (err) {
      console.error(err)
      setError(err instanceof Error ? err : new Error("Failed to load discover"))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const allItems = rows.flatMap((row) => row.items ?? [])

  const filteredItems =
    activeFilter === "All"
      ? allItems
      : activeFilter === "Movies"
        ? allItems.filter((item) => item.mediaType === "movie")
        : allItems.filter((item) => item.mediaType === "tv")

  const uniqueItems = Array.from(new Map(filteredItems.map((item) => [item.id, item])).values())

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
          <h2 className="text-2xl font-semibold">Failed to load discover</h2>
          <p className="mt-3 text-muted-foreground">{error.message}</p>
          <Button onClick={load} className="mt-8 rounded-full px-8">
            Try Again
          </Button>
        </div>
      </main>
    )
  }

  if (loading) {
    return <HomeSkeleton />
  }

  return (
    <main className="relative min-h-screen bg-background text-foreground">
      <AmbientBackground />

      <div className="relative z-10 mx-auto max-w-7xl px-6 pt-32 pb-40">
        <h1 className="text-4xl font-bold tracking-tight md:text-5xl">Discover</h1>

        {/* FILTERS */}
        <div className="mt-8 flex gap-2">
          {FILTERS.map((filter) => (
            <Button
              key={filter}
              variant={activeFilter === filter ? "default" : "outline"}
              size="sm"
              className={cn(
                "rounded-full px-5",
                activeFilter === filter
                  ? "bg-foreground text-background hover:bg-foreground/90"
                  : "border-border/60 bg-secondary/30 text-muted-foreground hover:bg-secondary hover:text-foreground"
              )}
              onClick={() => setActiveFilter(filter)}
            >
              {filter}
            </Button>
          ))}
        </div>

        {/* GRID */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="mt-10 grid grid-cols-2 gap-6 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6"
        >
          {uniqueItems.map((item) => (
            <MovieCard
              key={item.id}
              movie={{
                id: item.id,
                title: item.title,
                posterPath: item.posterPath,
                mediaType: item.mediaType,
                year: item.year,
                rating: item.rating,
              }}
            />
          ))}
        </motion.div>

        {uniqueItems.length === 0 && (
          <p className="mt-20 text-center text-lg text-muted-foreground">No content found</p>
        )}
      </div>
    </main>
  )
}
