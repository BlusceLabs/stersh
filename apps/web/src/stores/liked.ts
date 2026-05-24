import { create } from "zustand"
import { persist } from "zustand/middleware"

interface LikedItem {
  id: number
  title: string
  posterPath: string
  mediaType: string
  year?: string
  likedAt: number
}

interface LikedStore {
  items: LikedItem[]
  toggle: (item: Omit<LikedItem, "likedAt">) => void
  isLiked: (id: number) => boolean
}

export const useLiked = create<LikedStore>()(
  persist(
    (set, get) => ({
      items: [],
      toggle: (item) => {
        const exists = get().isLiked(item.id)
        if (exists) {
          set((state) => ({
            items: state.items.filter((i) => i.id !== item.id),
          }))
        } else {
          set((state) => ({
            items: [{ ...item, likedAt: Date.now() }, ...state.items],
          }))
        }
      },
      isLiked: (id) => get().items.some((i) => i.id === id),
    }),
    {
      name: "watchfy-liked",
    }
  )
)
