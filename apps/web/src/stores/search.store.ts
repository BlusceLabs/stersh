import { create } from "zustand"
import { persist } from "zustand/middleware"
import type { SearchResult } from "@/api/search"

interface SearchStore {
  query: string
  results: SearchResult[]
  loading: boolean
  searched: boolean
  error: string | null
  setQuery: (query: string) => void
  setResults: (results: SearchResult[]) => void
  setLoading: (loading: boolean) => void
  setSearched: (searched: boolean) => void
  setError: (error: string | null) => void
  clear: () => void
}

export const useSearchStore = create<SearchStore>()(
  persist(
    (set) => ({
      query: "",
      results: [],
      loading: false,
      searched: false,
      error: null,
      setQuery: (query) => set({ query }),
      setResults: (results) => set({ results }),
      setLoading: (loading) => set({ loading }),
      setSearched: (searched) => set({ searched }),
      setError: (error) => set({ error }),
      clear: () => set({ query: "", results: [], loading: false, searched: false, error: null }),
    }),
    {
      name: "watchfy-search",
      partialize: (state) => ({ query: state.query }),
    }
  )
)
