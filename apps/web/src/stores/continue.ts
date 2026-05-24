import { create } from "zustand"
import { persist } from "zustand/middleware"

interface WatchProgress {
  id: number
  title: string
  posterPath: string
  mediaType: string
  currentTime: number
  duration: number
  season?: number
  episode?: number
  episodeName?: string
  updatedAt: number
}

function matches(progress: WatchProgress, id: number, season?: number, episode?: number) {
  if (progress.id !== id) return false
  if (season === undefined || episode === undefined) return true
  return progress.season === season && progress.episode === episode
}

interface ContinueWatchingStore {
  items: WatchProgress[]
  updateProgress: (progress: Omit<WatchProgress, "updatedAt">) => void
  remove: (id: number, season?: number, episode?: number) => void
  getProgress: (id: number, season?: number, episode?: number) => WatchProgress | undefined
  clearAll: () => void
}

export const useContinueWatching = create<ContinueWatchingStore>()(
  persist(
    (set, get) => ({
      items: [],
      updateProgress: (progress) => {
        set((state) => {
          const filtered = state.items.filter(
            (i) => !matches(i, progress.id, progress.season, progress.episode)
          )
          return {
            items: [
              { ...progress, updatedAt: Date.now() },
              ...filtered,
            ].slice(0, 50),
          }
        })
      },
      remove: (id, season, episode) =>
        set((state) => ({
          items: state.items.filter((i) => !matches(i, id, season, episode)),
        })),
      getProgress: (id, season, episode) =>
        get().items.find((i) => matches(i, id, season, episode)),
      clearAll: () => set({ items: [] }),
    }),
    {
      name: "watchfy-continue",
    }
  )
)
