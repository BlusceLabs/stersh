import { create } from "zustand"
import { persist } from "zustand/middleware"

interface AuthStore {
  user: Record<string, unknown> | null
  isAuthenticated: boolean
  setUser: (user: Record<string, unknown> | null) => void
  logout: () => void
}

export const useAuthStore = create<AuthStore>()(
  persist(
    (set) => ({
      user: null,
      isAuthenticated: false,
      setUser: (user) => set({ user, isAuthenticated: !!user }),
      logout: () => set({ user: null, isAuthenticated: false }),
    }),
    {
      name: "watchfy-auth",
    }
  )
)
