import { create } from "zustand"
import type { HomepageResponse } from "@/api/home"

export type HomeHeroItem = HomepageResponse["hero"][number]
export type HomeRowItem = HomepageResponse["rows"][number]

interface HomeStore {
  hero: HomeHeroItem[]
  rows: HomeRowItem[]
  loading: boolean
  setHero: (hero: HomeHeroItem[]) => void
  setRows: (rows: HomeRowItem[]) => void
  setLoading: (loading: boolean) => void
}

export const useHomeStore = create<HomeStore>((set) => ({
  hero: [],
  rows: [],
  loading: true,
  setHero: (hero) => set({ hero }),
  setRows: (rows) => set({ rows }),
  setLoading: (loading) => set({ loading }),
}))
