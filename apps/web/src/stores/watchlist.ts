import { create } from "zustand"
import { persist } from "zustand/middleware"

interface WatchlistItem {
  id: number
  title: string
  posterPath: string
  mediaType: string
  year?: string
  addedAt: number
}

interface WatchlistStore {
  items: WatchlistItem[]
  add: (item: Omit<WatchlistItem, "addedAt">) => void
  remove: (id: number) => void
  isInWatchlist: (id: number) => boolean
}

export const useWatchlist = create<WatchlistStore>()(
  persist(
    (set, get) => ({
      items: [],
      add: (item) => {
        if (get().isInWatchlist(item.id)) return
        set((state) => ({
          items: [{ ...item, addedAt: Date.now() }, ...state.items],
        }))
      },
      remove: (id) =>
        set((state) => ({
          items: state.items.filter((i) => i.id !== id),
        })),
      isInWatchlist: (id) => get().items.some((i) => i.id === id),
    }),
    {
      name: "watchfy-watchlist",
    }
  )
)
