import { useCallback, useEffect } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { Search, X, Clock, TrendingUp } from "lucide-react"

import { searchContent } from "@/api/search"
import { MovieCard } from "@/components/cards/MovieCard"
import { AmbientBackground } from "@/components/cinematic/AmbientBackground/AmbientBackground"
import { useSearchStore } from "@/stores/search.store"

import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"

const TRENDING_SUGGESTIONS = [
  "Dune: Part Two",
  "The Bear",
  "Oppenheimer",
  "Attack on Titan",
  "Poor Things",
  "True Detective",
]

export default function SearchPage() {
  const query = useSearchStore((s) => s.query)
  const results = useSearchStore((s) => s.results)
  const loading = useSearchStore((s) => s.loading)
  const searched = useSearchStore((s) => s.searched)
  const error = useSearchStore((s) => s.error)
  const setQuery = useSearchStore((s) => s.setQuery)
  const setResults = useSearchStore((s) => s.setResults)
  const setLoading = useSearchStore((s) => s.setLoading)
  const setSearched = useSearchStore((s) => s.setSearched)
  const setError = useSearchStore((s) => s.setError)

  const doSearch = useCallback(async (q: string) => {
    if (!q.trim()) {
      setResults([])
      setSearched(false)
      setError(null)
      return
    }
    setLoading(true)
    setSearched(true)
    setError(null)
    try {
      const data = await searchContent(q.trim())
      setResults(data.results ?? [])
    } catch (err) {
      setResults([])
      setError(err instanceof Error ? err.message : "Search failed")
    } finally {
      setLoading(false)
    }
  }, [setResults, setSearched, setError, setLoading])

  useEffect(() => {
    const timer = setTimeout(() => doSearch(query), 300)
    return () => clearTimeout(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [query])

  return (
    <main className="relative min-h-screen bg-background text-foreground">
      <AmbientBackground />

      <div className="relative z-10 mx-auto max-w-6xl px-6 pt-12 pb-40">
        {/* SEARCH BAR */}
        <div className="relative">
          <Search
            size={22}
            className="absolute left-4 top-1/2 -translate-y-1/2 text-muted-foreground z-10"
          />
          <Input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search movies, TV shows, anime..."
            autoFocus
            className="w-full rounded-2xl border-border bg-secondary/50 py-6 pl-12 pr-12 text-lg text-foreground placeholder:text-muted-foreground/50 backdrop-blur-2xl transition-all focus-visible:ring-primary/40 focus-visible:ring-2 focus-visible:border-primary/30"
          />
          <AnimatePresence>
            {query && (
              <motion.div
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.8 }}
                className="absolute right-3 top-1/2 -translate-y-1/2"
              >
                <Button
                  variant="ghost"
                  size="icon"
                  className="rounded-full h-8 w-8 text-muted-foreground hover:text-foreground"
                  onClick={() => setQuery("")}
                >
                  <X size={18} />
                </Button>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* CONTENT */}
        <AnimatePresence mode="wait">
          {/* LOADING */}
          {loading && (
            <motion.div
              key="loading"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="mt-20 flex justify-center"
            >
              <div className="h-8 w-8 animate-spin rounded-full border-2 border-muted border-t-primary" />
            </motion.div>
          )}

          {/* SUGGESTIONS (no query yet) */}
          {!loading && !searched && (
            <motion.div
              key="suggestions"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
            >
              {/* TRENDING */}
              <div className="mt-10">
                <div className="flex items-center gap-2 text-muted-foreground">
                  <TrendingUp size={16} />
                  <span className="text-[11px] font-medium uppercase tracking-[0.2em]">
                    Trending Searches
                  </span>
                </div>

                <div className="mt-5 flex flex-wrap gap-3">
                  {TRENDING_SUGGESTIONS.map((term) => (
                    <Button
                      key={term}
                      variant="outline"
                      size="sm"
                      className="rounded-full border-border/60 bg-secondary/30 text-muted-foreground hover:bg-secondary hover:text-foreground"
                      onClick={() => setQuery(term)}
                    >
                      {term}
                    </Button>
                  ))}
                </div>
              </div>

              {/* RECENT */}
              <div className="mt-12">
                <div className="flex items-center gap-2 text-muted-foreground">
                  <Clock size={16} />
                  <span className="text-[11px] font-medium uppercase tracking-[0.2em]">
                    Recent Searches
                  </span>
                </div>
                <p className="mt-5 text-sm text-muted-foreground/40">
                  Your recent searches will appear here
                </p>
              </div>
            </motion.div>
          )}

          {/* RESULTS */}
          {!loading && searched && (
            <motion.div
              key="results"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
            >
              {error ? (
                <div className="mt-20 text-center">
                  <p className="text-lg text-destructive">
                    Search error
                  </p>
                  <p className="mt-2 text-sm text-muted-foreground">
                    {error}
                  </p>
                  <Button
                    variant="outline"
                    className="mt-6 rounded-full"
                    onClick={() => doSearch(query)}
                  >
                    Try Again
                  </Button>
                </div>
              ) : results.length > 0 ? (
                <>
                  <p className="mt-8 text-sm text-muted-foreground/60">
                    <Badge variant="secondary" className="mr-2 rounded-full">{results.length}</Badge>
                    result{results.length !== 1 ? "s" : ""} for{" "}
                    <span className="text-foreground/80">{query}</span>
                  </p>

                  <div className="mt-8 grid grid-cols-2 gap-6 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
                    {results.map((result) => (
                      <MovieCard
                        key={result.id}
                        movie={{
                          id: result.id,
                          title: result.title,
                          posterPath: result.posterPath,
                          mediaType: result.mediaType,
                        }}
                      />
                    ))}
                  </div>
                </>
              ) : (
                <div className="mt-20 text-center">
                  <p className="text-lg text-muted-foreground">
                    No results found
                  </p>
                  <p className="mt-2 text-sm text-muted-foreground/50">
                    Try a different keyword or check spelling
                  </p>
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </main>
  )
}
