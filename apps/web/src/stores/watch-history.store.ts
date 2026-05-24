import { create } from "zustand"

export interface WatchEntry {
  id: string
  title: string
  posterPath: string
  backdropPath?: string
  currentTime: number
  duration: number
  lastWatched: number // timestamp
  season?: number
  episode?: number
}

interface WatchHistoryStore {
  entries: Record<string, WatchEntry>
  addEntry: (entry: WatchEntry) => void
  removeEntry: (id: string) => void
  getEntry: (id: string) => WatchEntry | null
  getRecentEntries: (limit?: number) => WatchEntry[]
  getResumeTime: (id: string) => number
}

const STORAGE_KEY = "watchfy_history"

function loadFromStorage(): Record<string, WatchEntry> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) return JSON.parse(raw)
  } catch {
    // ignore
  }
  return {}
}

function saveToStorage(entries: Record<string, WatchEntry>) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(entries))
  } catch {
    // ignore
  }
}

export const useWatchHistoryStore = create<WatchHistoryStore>((set, get) => ({
  entries: loadFromStorage(),

  addEntry: (entry) => {
    const entries = {
      ...get().entries,
      [entry.id]: {
        ...entry,
        lastWatched: Date.now(),
      },
    }
    saveToStorage(entries)
    set({ entries })
  },

  removeEntry: (id) => {
    const entries = { ...get().entries }
    delete entries[id]
    saveToStorage(entries)
    set({ entries })
  },

  getEntry: (id) => {
    return get().entries[id] || null
  },

  getRecentEntries: (limit = 10) => {
    return Object.values(get().entries)
      .sort((a, b) => b.lastWatched - a.lastWatched)
      .slice(0, limit)
  },

  getResumeTime: (id) => {
    const entry = get().entries[id]
    if (!entry) return 0
    // Don't resume if we're within 5% of the end
    if (entry.duration > 0 && entry.currentTime >= entry.duration * 0.95) {
      return 0
    }
    // Don't resume if less than 30 seconds in
    if (entry.currentTime < 30) return 0
    return entry.currentTime
  },
}))
