import { create } from "zustand"

interface PlayerStore {
  currentTime: number
  duration: number
  isPlaying: boolean
  volume: number
  setCurrentTime: (time: number) => void
  setDuration: (duration: number) => void
  setIsPlaying: (playing: boolean) => void
  setVolume: (volume: number) => void
}

export const usePlayerStore = create<PlayerStore>((set) => ({
  currentTime: 0,
  duration: 0,
  isPlaying: false,
  volume: 1,
  setCurrentTime: (currentTime) => set({ currentTime }),
  setDuration: (duration) => set({ duration }),
  setIsPlaying: (isPlaying) => set({ isPlaying }),
  setVolume: (volume) => set({ volume }),
}))
