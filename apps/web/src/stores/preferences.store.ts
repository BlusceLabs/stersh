import { create } from "zustand"
import { persist } from "zustand/middleware"

interface PreferencesStore {
  theme: "dark" | "light"
  autoplay: boolean
  quality: "auto" | "1080p" | "720p" | "480p"
  setTheme: (theme: "dark" | "light") => void
  setAutoplay: (autoplay: boolean) => void
  setQuality: (quality: "auto" | "1080p" | "720p" | "480p") => void
}

export const usePreferencesStore = create<PreferencesStore>()(
  persist(
    (set) => ({
      theme: "dark",
      autoplay: true,
      quality: "auto",
      setTheme: (theme) => set({ theme }),
      setAutoplay: (autoplay) => set({ autoplay }),
      setQuality: (quality) => set({ quality }),
    }),
    {
      name: "watchfy-preferences",
    }
  )
)
