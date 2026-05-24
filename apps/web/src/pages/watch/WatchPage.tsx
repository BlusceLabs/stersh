import { useEffect, useState, useCallback } from "react"
import { useNavigate, useParams } from "@tanstack/react-router"

import { getMovieDetailsBySlug, getTVDetailsBySlug, getTVSeason } from "@/api/details"
import { getWatchSource, getSubtitles } from "@/api/watch"
import type { Episode } from "@/api/details"
import type { SubtitleTrack } from "@/api/watch"
import HlsPlayer from "@/components/player/HlsPlayer"
import { WatchSkeleton } from "@/components/shared/LoadingSkeleton"
import { useContinueWatching } from "@/stores/continue"
import { Button } from "@/components/ui/button"

interface MovieDetails {
  id: number
  title: string
  overview: string
  backdropPath: string
  posterPath: string
  logoPath: string
  rating: number
  runtime?: string
  year: string
  genres: string[]
  mediaType: string
}

function useWatchParams() {
  const params = useParams({ strict: false })
  const qs = new URLSearchParams(window.location.search)

  const type = (params.type as string) || ""
  const slug = (params.slug as string) || ""

  // New path-based route: season="sn1", episode="ep3"
  let season = params.season
    ? parseInt(String(params.season).replace(/^sn/, ""))
    : undefined
  let episode = params.episode
    ? parseInt(String(params.episode).replace(/^ep/, ""))
    : undefined

  // Fall back to query params for legacy URLs
  if (season === undefined) {
    season = qs.get("season") ? parseInt(qs.get("season")!) : undefined
  }
  if (episode === undefined) {
    episode = qs.get("episode") ? parseInt(qs.get("episode")!) : undefined
  }

  return { type, slug, season, episode }
}

const SERVERS = ["Black", "White"]

export default function WatchPage() {
  const navigate = useNavigate()
  const { type, slug, season, episode } = useWatchParams()

  const [movie, setMovie] = useState<MovieDetails | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)
  const [sources, setSources] = useState<{ url: string; quality: string; resolution: number }[]>([])
  const [seasonEpisodes, setSeasonEpisodes] = useState<Episode[]>([])
  const [subtitles, setSubtitles] = useState<SubtitleTrack[]>([])
  const [server, setServer] = useState("Black")

  const load = useCallback(async (selectedServer?: string) => {
    try {
      setLoading(true)
      setError(null)
      const srv = selectedServer ?? server
      const detailsFn = type === "tv" ? getTVDetailsBySlug : getMovieDetailsBySlug
      const details = await detailsFn(slug)
      setMovie(details)

      if (type === "tv" && season !== undefined) {
        const seasonData = await getTVSeason(String(details.id), season).catch(() => null)
        if (seasonData) setSeasonEpisodes(seasonData.episodes)
      }

      if (details.imdbId) {
        const subsData = await getSubtitles(details.imdbId).catch(() => null)
        if (subsData) setSubtitles(subsData.subtitles)
      }

      const watchData = await getWatchSource(String(details.id), {
        mediaType: type,
        season,
        episode,
        server: srv,
      })
      setSources(watchData.sources || [])
    } catch (err) {
      console.error(err)
      setError(err instanceof Error ? err : new Error("Failed to load stream"))
    } finally {
      setLoading(false)
    }
  }, [type, slug, season, episode, server])

  const loadSources = useCallback(async (srv: string) => {
    if (!movie) return
    try {
      setError(null)
      const watchData = await getWatchSource(String(movie.id), {
        mediaType: type,
        season,
        episode,
        server: srv,
      })
      setSources(watchData.sources || [])
    } catch (err) {
      console.error(err)
      setError(err instanceof Error ? err : new Error("Failed to load stream"))
    }
  }, [movie, type, season, episode])

  const handleServerChange = (newServer: string) => {
    if (newServer === server) return
    setServer(newServer)
    loadSources(newServer)
  }

  const nextEpisode = seasonEpisodes.find(e => e.episodeNumber === (episode ?? 1) + 1)

  const handleNextEpisode = () => {
    if (type !== "tv" || episode === undefined || season === undefined) return
    if (movie) {
      useContinueWatching.getState().remove(movie.id, season, episode)
    }
    navigate({
      to: "/watch/$type/$slug/$season/$episode",
      params: { type, slug, season: "sn" + season, episode: "ep" + (episode + 1) },
    })
  }

  useEffect(() => { load() }, [load])

  if (error) {
    return (
      <main className="flex h-screen flex-col items-center justify-center bg-black text-white">
        <div className="text-center">
          <div className="mx-auto mb-6 flex h-20 w-20 items-center justify-center rounded-full bg-destructive/10">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-10 w-10 text-destructive">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
          </div>
          <h2 className="text-2xl font-semibold">Failed to load stream</h2>
          <p className="mt-3 text-white/50">{error.message}</p>
          <Button onClick={() => load()} className="mt-8 rounded-full px-8">
            Try Again
          </Button>
        </div>
      </main>
    )
  }

  return (
    <main className="relative h-screen w-screen overflow-hidden bg-black">
      {loading && <WatchSkeleton />}

      {!loading && sources.length > 0 && movie && (
        <HlsPlayer
          sources={sources.map((s) => ({
            src: s.url,
            type: s.url.includes(".m3u8") ? "application/x-mpegURL" : "video/mp4",
            quality: s.quality,
            resolution: s.resolution,
          }))}
          movieId={movie.id}
          movieTitle={movie.title}
          moviePoster={movie.posterPath}
          movieType={movie.mediaType || type}
          season={season}
          episode={episode}
          autoplay
          onNextEpisode={nextEpisode ? handleNextEpisode : undefined}
          nextEpisodeTitle={nextEpisode?.name}
          subtitles={subtitles}
          server={server}
          servers={SERVERS}
          onServerChange={handleServerChange}
        />
      )}

      <div className="absolute left-6 right-6 top-6 z-50 flex items-start justify-between gap-4">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => window.history.back()}
          className="h-14 w-14 shrink-0 rounded-full border border-white/10 bg-white/10 text-white backdrop-blur-3xl hover:bg-white/20 hover:text-white hover:scale-110 transition-all duration-300"
        >
          <svg viewBox="0 0 24 24" fill="currentColor" width={22} height={22}>
            <path d="M20 11H7.83l5.59-5.59L12 4l-8 8 8 8 1.41-1.41L7.83 13H20v-2z" />
          </svg>
        </Button>

        {movie && (
          <div className="max-w-[50%] text-right">
            <h1 className="truncate text-lg font-semibold text-white drop-shadow-lg">
              {movie.title}
              {type === "tv" && season !== undefined && (
                <span className="ml-2 text-white/60">S{season}</span>
              )}
            </h1>
            <div className="mt-0.5 flex items-center justify-end gap-2 text-sm text-white/60 drop-shadow-md">
              <span>{movie.year}</span>
              {movie.runtime && (
                <>
                  <span className="text-white/20">|</span>
                  <span>{movie.runtime}</span>
                </>
              )}
              {type === "tv" && episode !== undefined && (
                <>
                  <span className="text-white/20">|</span>
                  <span>E{episode}</span>
                </>
              )}
            </div>
          </div>
        )}
      </div>
    </main>
  )
}
