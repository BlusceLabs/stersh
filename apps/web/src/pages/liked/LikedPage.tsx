import { motion, AnimatePresence } from "framer-motion"
import { Trash2, Heart } from "lucide-react"
import { useNavigate } from "@tanstack/react-router"

import { useLiked } from "@/stores/liked"
import { MovieCard } from "@/components/cards/MovieCard"
import { AmbientBackground } from "@/components/cinematic/AmbientBackground/AmbientBackground"

import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"

export default function LikedPage() {
  const navigate = useNavigate()
  const items = useLiked((s) => s.items)
  const remove = useLiked((s) => s.toggle)

  return (
    <main className="relative min-h-screen bg-background text-foreground">
      <AmbientBackground />

      <div className="relative z-10 mx-auto max-w-7xl px-6 pt-32 pb-40">
        <div className="flex items-center justify-between">
          <h1 className="text-4xl font-bold tracking-tight md:text-5xl">Liked</h1>
          <Badge variant="secondary" className="rounded-full">
            {items.length} title{items.length !== 1 ? "s" : ""}
          </Badge>
        </div>

        {items.length === 0 ? (
          <div className="mt-20 flex flex-col items-center text-center">
            <div className="flex h-20 w-20 items-center justify-center rounded-full bg-muted">
              <Heart size={36} className="text-muted-foreground/40" />
            </div>
            <p className="mt-6 text-lg text-muted-foreground">No favorites yet</p>
            <p className="mt-2 text-sm text-muted-foreground/50">
              Tap the heart on any movie or show to add it here
            </p>
            <Button
              className="mt-8 rounded-full px-8"
              onClick={() => navigate({ to: "/discover" })}
            >
              Discover Content
            </Button>
          </div>
        ) : (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="mt-10 grid grid-cols-2 gap-6 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6"
          >
            <AnimatePresence>
              {items.map((item) => (
                <motion.div
                  key={item.id}
                  layout
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.9 }}
                  className="group relative"
                >
                  <MovieCard
                    movie={{
                      id: item.id,
                      title: item.title,
                      posterPath: item.posterPath,
                      mediaType: item.mediaType,
                      year: item.year,
                    }}
                  />
                  <Button
                    variant="ghost"
                    size="icon"
                    className="absolute right-2 top-2 z-20 h-8 w-8 rounded-full bg-black/60 text-white/60 opacity-0 backdrop-blur-xl transition-all hover:bg-destructive hover:text-white group-hover:opacity-100"
                    onClick={(e) => {
                      e.stopPropagation()
                      e.preventDefault()
                      remove({
                        id: item.id,
                        title: item.title,
                        posterPath: item.posterPath,
                        mediaType: item.mediaType,
                        year: item.year,
                      })
                    }}
                    title="Remove from liked"
                  >
                    <Trash2 size={14} />
                  </Button>
                </motion.div>
              ))}
            </AnimatePresence>
          </motion.div>
        )}
      </div>
    </main>
  )
}
