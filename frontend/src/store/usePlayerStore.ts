import { create } from "zustand";
import { persist, createJSONStorage, devtools } from "zustand/middleware";

interface PlayerState {
  // Playback
  playing: boolean;
  currentTime: number;
  duration: number;
  buffered: number;

  // Settings
  volume: number;
  muted: boolean;
  playbackRate: number;
  isFullscreen: boolean;

  // Media Info
  mediaId: string | null;
  mediaType: "movie" | "tv" | null;
  title: string | null;

  // Actions
  setPlaying: (playing: boolean) => void;
  togglePlay: () => void;
  setCurrentTime: (time: number) => void;
  setDuration: (duration: number) => void;
  setBuffered: (buffered: number) => void;

  setVolume: (volume: number) => void;
  toggleMute: () => void;
  setPlaybackRate: (rate: number) => void;
  setFullscreen: (isFullscreen: boolean) => void;

  loadMedia: (id: string, type: "movie" | "tv", title?: string) => void;
  resetPlayer: () => void;
}

export const usePlayerStore = create<PlayerState>()(
  devtools(
    persist(
      (set, get) => ({
        // Initial State
        playing: false,
        currentTime: 0,
        duration: 0,
        buffered: 0,

        volume: 1,
        muted: false,
        playbackRate: 1,
        isFullscreen: false,

        mediaId: null,
        mediaType: null,
        title: null,

        // Playback Controls
        setPlaying: (playing) => set({ playing }),

        togglePlay: () => set((state) => ({ playing: !state.playing })),

        setCurrentTime: (time) => set({ currentTime: Math.max(0, time) }),

        setDuration: (duration) => set({ duration }),

        setBuffered: (buffered) => set({ buffered }),

        // Volume & Settings
        setVolume: (volume) =>
          set({
            volume: Math.max(0, Math.min(1, volume)),
            muted: volume === 0,
          }),

        toggleMute: () =>
          set((state) => ({
            muted: !state.muted,
            volume: state.muted && state.volume === 0 ? 0.7 : state.volume,
          })),

        setPlaybackRate: (rate) =>
          set({ playbackRate: [0.5, 0.75, 1, 1.25, 1.5, 2].includes(rate) ? rate : 1 }),

        setFullscreen: (isFullscreen) => set({ isFullscreen }),

        // Media Loading
        loadMedia: (id, type, title?: string | null) =>
          set({
            mediaId: id,
            mediaType: type,
            title: title ?? null,
            currentTime: 0,
            playing: true, // Auto-play on load
          }),

        // Reset
        resetPlayer: () =>
          set({
            playing: false,
            currentTime: 0,
            duration: 0,
            buffered: 0,
            mediaId: null,
            mediaType: null,
            title: null,
            isFullscreen: false,
          }),
      }),

      {
        name: "watchfy-player-storage",
        storage: createJSONStorage(() => localStorage),
        partialize: (state) => ({
          volume: state.volume,
          muted: state.muted,
          playbackRate: state.playbackRate,
        }),
      }
    )
  )
);