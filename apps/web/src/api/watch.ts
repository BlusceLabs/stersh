import { api } from "./client"

export interface WatchSource {
  sources: {
    url: string
    quality: string
    resolution: number
  }[]
}

export interface SubtitleTrack {
  label: string
  language: string
  url: string
  format: string
}

export interface SubtitlesResponse {
  subtitles: SubtitleTrack[]
}

interface WatchOptions {
  mediaType?: string
  season?: number
  episode?: number
  server?: string
}

export async function getWatchSource(
  id: string,
  options?: WatchOptions
) {
  const params = new URLSearchParams()
  if (options?.mediaType) params.set("mediaType", options.mediaType)
  if (options?.season) params.set("season", String(options.season))
  if (options?.episode) params.set("episode", String(options.episode))
  if (options?.server) params.set("server", options.server)
  const qs = params.toString()
  return api.get<WatchSource>(
    `/watch/${id}${qs ? `?${qs}` : ""}`
  )
}

export async function getSubtitles(imdbId: string) {
  return api.get<SubtitlesResponse>(`/subtitles?imdbId=${encodeURIComponent(imdbId)}`)
}
