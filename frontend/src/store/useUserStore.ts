import { create } from "zustand";
import { persist, createJSONStorage, devtools } from "zustand/middleware";
import api from "@/utils/api";

interface User {
  id: string;
  username: string;
  email: string;
  avatar?: string;
  role?: string;
}

interface UserState {
  user: User | null;
  accessToken: string | null;
  refreshTokenValue: string | null;
  loading: boolean;
  error: string | null;

  login: (email: string, password: string) => Promise<void>;
  register: (email: string, username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshToken: () => Promise<boolean>;
  loadUser: () => Promise<void>;
  clearError: () => void;
}

const useUser = create<UserState>()(
  devtools(
    persist(
      (set, get) => ({
        user: null,
        accessToken: null,
        refreshTokenValue: null,
        loading: false,
        error: null,

        login: async (email: string, password: string) => {
          set({ loading: true, error: null });
          try {
            const data = await api.login(email, password);
            set({
              accessToken: data.accessToken,
              refreshTokenValue: data.refreshToken,
              user: data.user,
            });
          } catch (err: any) {
            set({ error: err.message || "Login failed" });
            throw err;
          } finally {
            set({ loading: false });
          }
        },

        register: async (email: string, username: string, password: string) => {
          set({ loading: true, error: null });
          try {
            const data = await api.register(email, username, password);
            set({
              accessToken: data.accessToken,
              refreshTokenValue: data.refreshToken,
              user: data.user,
            });
          } catch (err: any) {
            set({ error: err.message || "Registration failed" });
            throw err;
          } finally {
            set({ loading: false });
          }
        },

        logout: async () => {
          try {
            await api.logout();
          } catch (_) {}

          set({
            user: null,
            accessToken: null,
            refreshTokenValue: null,
            error: null,
          });

          localStorage.removeItem("access_token");
          localStorage.removeItem("refresh_token");
        },

        refreshToken: async (): Promise<boolean> => {
          const { refreshTokenValue } = get();
          if (!refreshTokenValue) return false;

          try {
            const data = await api.refreshToken(refreshTokenValue);
            set({
              accessToken: data.accessToken,
              refreshTokenValue: data.refreshToken || refreshTokenValue,
            });
            return true;
          } catch (err) {
            get().logout();
            return false;
          }
        },

        loadUser: async () => {
          const { accessToken } = get();
          if (!accessToken) return;

          set({ loading: true });
          try {
            const userData = await api.getProfile(accessToken);
            set({ user: userData });
          } catch (err: any) {
            if (err.message.includes("401") || err.message.includes("token")) {
              await get().refreshToken();
            } else {
              set({ error: err.message });
            }
          } finally {
            set({ loading: false });
          }
        },

        clearError: () => set({ error: null }),
      }),

      {
        name: "watchfy-user-storage",
        storage: createJSONStorage(() => localStorage),
        partialize: (state) => ({
          accessToken: state.accessToken,
          refreshTokenValue: state.refreshTokenValue,
          user: state.user,
        }),
      }
    )
  )
);

export default useUser;