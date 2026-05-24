"use client"

import { useEffect, useRef, useState, useCallback } from "react"
import Hls from "hls.js"

import { useContinueWatching } from "@/stores/continue"
import type { SubtitleTrack } from "@/api/watch"

interface Source {
  src: string
  type: "video/mp4" | "application/x-mpegURL"
  quality?: string
  resolution?: number
}

interface Props {
  sources: Source[]
  poster?: string
  autoplay?: boolean
  movieId?: number
  movieTitle?: string
  moviePoster?: string
  movieType?: string
  season?: number
  episode?: number
  onNextEpisode?: () => void
  nextEpisodeTitle?: string
  subtitles?: SubtitleTrack[]
  server?: string
  servers?: string[]
  onServerChange?: (server: string) => void
}

function formatTime(s: number): string {
  if (!isFinite(s) || s < 0) return "0:00"
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  const sec = Math.floor(s % 60)
  if (h > 0) return `${h}:${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")}`
  return `${m}:${String(sec).padStart(2, "0")}`
}

interface QualityLevel {
  index: number
  label: string
  height: number
}

export default function HlsPlayer({
  sources,
  autoplay = true,
  movieId,
  movieTitle,
  moviePoster,
  movieType,
  season,
  episode,
  onNextEpisode,
  nextEpisodeTitle,
  subtitles,
  server = "White",
  servers,
  onServerChange,
}: Props) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const hlsRef = useRef<Hls | null>(null)
  const controlsTimer = useRef<ReturnType<typeof setTimeout>>()
  const ctrlThrottle = useRef(0)
  const volumeRef = useRef<HTMLDivElement>(null)

  const updateProgress = useContinueWatching((s) => s.updateProgress)
  const savedProgress = useContinueWatching((s) =>
    movieId ? s.getProgress(movieId, season, episode) : undefined
  )

  const [playing, setPlaying] = useState(false)
  const [muted, setMuted] = useState(false)
  const [volume, setVolume] = useState(1)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [buffered, setBuffered] = useState(0)
  const [fullscreen, setFullscreen] = useState(false)
  const [showControls, setShowControls] = useState(true)
  const [loading, setLoading] = useState(true)
  const [autoplayBlocked, setAutoplayBlocked] = useState(false)
  const [showResumePrompt, setShowResumePrompt] = useState(false)
  const [showSettings, setShowSettings] = useState(false)
  const [playbackRate, setPlaybackRate] = useState(1)
  const [qualities, setQualities] = useState<QualityLevel[]>([])
  const [currentQuality, setCurrentQuality] = useState(-1)
  const [error, setError] = useState<string | null>(null)
  const [showTimeRemaining, setShowTimeRemaining] = useState(false)
  const [skipIndicator, setSkipIndicator] = useState<number | null>(null)
  const [showNextEpisode, setShowNextEpisode] = useState(false)
  const [showSubtitlesMenu, setShowSubtitlesMenu] = useState(false)
  const [selectedSubtitleLabel, setSelectedSubtitleLabel] = useState<string | null>(null)
  const [showServerMenu, setShowServerMenu] = useState(false)

  const showControlsTemp = useCallback(() => {
    const now = Date.now()
    if (now - ctrlThrottle.current < 200) return
    ctrlThrottle.current = now
    setShowControls(true)
    clearTimeout(controlsTimer.current)
    if (!videoRef.current?.paused) {
      controlsTimer.current = setTimeout(() => setShowControls(false), 4000)
    }
  }, [])

  const attachHls = useCallback((video: HTMLVideoElement, src: string) => {
    if (Hls.isSupported()) {
      hlsRef.current?.destroy()
      const hls = new Hls()
      hlsRef.current = hls
      hls.attachMedia(video)
      hls.on(Hls.Events.MEDIA_ATTACHED, () => hls.loadSource(src))
      hls.on(Hls.Events.MANIFEST_PARSED, () => {
        setLoading(false)
        const levels: QualityLevel[] = hls.levels.map((l, i) => ({
          index: i,
          label: l.height ? `${l.height}p` : `Auto`,
          height: l.height || 0,
        }))
        setQualities(levels)
        if (autoplay) {
          video.play().then(() => setAutoplayBlocked(false)).catch(() => setAutoplayBlocked(true))
        }
      })
      hls.on(Hls.Events.LEVEL_SWITCHED, (_, data) => {
        setCurrentQuality(data.level)
      })
      hls.on(Hls.Events.ERROR, (_, data) => {
        if (data.fatal) {
          setLoading(false)
          setError("Failed to load stream")
        }
      })
    } else if (video.canPlayType("application/vnd.apple.mpegurl")) {
      video.src = src
      video.addEventListener("loadedmetadata", () => setLoading(false))
    } else {
      setLoading(false)
      setError("HLS playback not supported in this browser")
    }
  }, [autoplay])

  useEffect(() => {
    const video = videoRef.current
    if (!video) return

    const hlsSrc = sources.find(s => s.type === "application/x-mpegURL")?.src
    const mp4Src = sources.find(s => s.type === "video/mp4")?.src

    if (hlsSrc) {
      attachHls(video, hlsSrc)
    } else if (mp4Src) {
      video.src = mp4Src
      video.addEventListener("loadedmetadata", () => setLoading(false))
    } else {
      setLoading(false)
      setError("No playable source found")
    }

    const onPlay = () => setPlaying(true)
    const onPause = () => setPlaying(false)
    const onVolumeChange = () => {
      setMuted(video.muted)
      setVolume(video.volume)
    }
    const updateBuffer = () => {
      const buf = video.buffered
      if (buf.length > 0) {
        setBuffered((buf.end(buf.length - 1) / video.duration) * 100)
      }
    }
    const onTimeUpdate = () => {
      setCurrentTime(video.currentTime)
      setDuration(video.duration || 0)
      updateBuffer()
    }
    const onProgress = () => updateBuffer()
    const onWaiting = () => setLoading(true)
    const onCanPlay = () => {
      setLoading(false)
      // Check for saved progress after video is ready
      if (savedProgress && savedProgress.currentTime > 10 && savedProgress.duration > 0) {
        const pct = savedProgress.currentTime / savedProgress.duration
        if (pct < 0.95) {
          setShowResumePrompt(true)
        }
      }
    }
    const onEnded = () => {
      setPlaying(false)
      // Clear saved progress when finished
      if (movieId) {
        useContinueWatching.getState().remove(movieId, season, episode)
      }
    }
    const onError = () => {
      if (video.error) setError(video.error.message || "Playback error")
    }

    video.addEventListener("play", onPlay)
    video.addEventListener("pause", onPause)
    video.addEventListener("volumechange", onVolumeChange)
    video.addEventListener("timeupdate", onTimeUpdate)
    video.addEventListener("progress", onProgress)
    video.addEventListener("waiting", onWaiting)
    video.addEventListener("canplay", onCanPlay)
    video.addEventListener("ended", onEnded)
    video.addEventListener("error", onError)

    // Periodic progress save
    const saveInterval = setInterval(() => {
      if (movieId && movieTitle && moviePoster && video.currentTime > 0 && video.duration > 0) {
        const pct = video.currentTime / video.duration
        if (pct > 0.05 && pct < 0.95) {
          updateProgress({
            id: movieId,
            title: movieTitle,
            posterPath: moviePoster,
            mediaType: movieType || "movie",
            currentTime: video.currentTime,
            duration: video.duration,
            season,
            episode,
          })
        }
      }
    }, 5000)

    return () => {
      hlsRef.current?.destroy()
      hlsRef.current = null
      clearInterval(saveInterval)
      video.removeEventListener("play", onPlay)
      video.removeEventListener("pause", onPause)
      video.removeEventListener("volumechange", onVolumeChange)
      video.removeEventListener("timeupdate", onTimeUpdate)
      video.removeEventListener("progress", onProgress)
      video.removeEventListener("waiting", onWaiting)
      video.removeEventListener("canplay", onCanPlay)
      video.removeEventListener("ended", onEnded)
      video.removeEventListener("error", onError)
    }
  }, [sources, attachHls, movieId, movieTitle, moviePoster, movieType, season, episode, savedProgress, updateProgress])

  useEffect(() => {
    const cb = () => setFullscreen(!!document.fullscreenElement)
    document.addEventListener("fullscreenchange", cb)
    return () => document.removeEventListener("fullscreenchange", cb)
  }, [])

  useEffect(() => {
    if (!showSettings) return
    const handler = (_e: MouseEvent) => setShowSettings(false)
    const t = setTimeout(() => document.addEventListener("click", handler), 0)
    return () => { clearTimeout(t); document.removeEventListener("click", handler) }
  }, [showSettings])

  useEffect(() => {
    if (!showSubtitlesMenu) return
    const handler = (_e: MouseEvent) => setShowSubtitlesMenu(false)
    const t = setTimeout(() => document.addEventListener("click", handler), 0)
    return () => { clearTimeout(t); document.removeEventListener("click", handler) }
  }, [showSubtitlesMenu])

  useEffect(() => {
    if (!onNextEpisode || duration <= 0) {
      setShowNextEpisode(false)
      return
    }
    const remaining = duration - currentTime
    setShowNextEpisode(remaining <= 15)
  }, [currentTime, duration, onNextEpisode])

  useEffect(() => {
    const video = videoRef.current
    if (!video) return
    const tracks = video.textTracks
    for (let i = 0; i < tracks.length; i++) {
      const track = tracks[i]
      if (track.kind === "subtitles" || track.kind === "captions") {
        track.mode = track.label === selectedSubtitleLabel ? "showing" : "disabled"
      }
    }
  }, [selectedSubtitleLabel])

  const handleContainerClick = (_e: React.MouseEvent) => {
    if (showSettings) { setShowSettings(false); return }
    if (showResumePrompt) { setShowResumePrompt(false); return }
    const video = videoRef.current
    if (!video) return
    if (autoplayBlocked) {
      setAutoplayBlocked(false)
      video.play().catch(() => setAutoplayBlocked(true))
    } else if (video.paused) {
      video.play()
    }
    showControlsTemp()
  }

  const resumeFromSaved = () => {
    const video = videoRef.current
    if (!video || !savedProgress) return
    video.currentTime = savedProgress.currentTime
    setShowResumePrompt(false)
    video.play().catch(() => {})
  }

  const dismissResume = () => {
    setShowResumePrompt(false)
  }

  const togglePlay = () => {
    const video = videoRef.current
    if (!video) return
    if (video.paused) { video.play() } else { video.pause() }
    showControlsTemp()
  }

  const setVolumeLevel = (v: number) => {
    const video = videoRef.current
    if (!video) return
    video.volume = Math.max(0, Math.min(1, v))
  }

  const toggleMute = () => {
    const video = videoRef.current
    if (!video) return
    video.muted = !video.muted
  }

  const toggleFullscreen = () => {
    if (!containerRef.current) return
    if (!document.fullscreenElement) {
      containerRef.current.requestFullscreen()
    } else {
      document.exitFullscreen()
    }
  }

  const togglePiP = async () => {
    const video = videoRef.current
    if (!video) return
    try {
      if (document.pictureInPictureElement) {
        await document.exitPictureInPicture()
      } else {
        await video.requestPictureInPicture()
      }
    } catch { /* PiP not supported */ }
  }

  const seek = (e: React.MouseEvent<HTMLDivElement>) => {
    const video = videoRef.current
    if (!video) return
    const rect = e.currentTarget.getBoundingClientRect()
    const ratio = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width))
    video.currentTime = ratio * (video.duration || 0)
  }

  const skip = (s: number) => {
    const video = videoRef.current
    if (!video) return
    video.currentTime = Math.max(0, Math.min(video.duration || 0, video.currentTime + s))
    setSkipIndicator(s)
    setTimeout(() => setSkipIndicator(null), 800)
  }

  const changeSpeed = (rate: number) => {
    const video = videoRef.current
    if (!video) return
    video.playbackRate = rate
    setPlaybackRate(rate)
    setShowSettings(false)
  }

  const changeQuality = (index: number) => {
    if (!hlsRef.current) return
    hlsRef.current.currentLevel = index
    setCurrentQuality(index)
    setShowSettings(false)
  }

  const progressPct = duration > 0 ? (currentTime / duration) * 100 : 0
  const displayTime = showTimeRemaining ? currentTime - duration : currentTime

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (document.activeElement?.tagName === "INPUT") return
      const video = videoRef.current
      if (!video) return

      switch (e.code) {
        case "Space":
        case "KeyK":
          e.preventDefault()
          togglePlay()
          break
        case "ArrowLeft":
          e.preventDefault()
          skip(-10)
          showControlsTemp()
          break
        case "ArrowRight":
          e.preventDefault()
          skip(10)
          showControlsTemp()
          break
        case "ArrowUp":
          e.preventDefault()
          setVolumeLevel((video.volume || 0) + 0.1)
          break
        case "ArrowDown":
          e.preventDefault()
          setVolumeLevel((video.volume || 0) - 0.1)
          break
        case "KeyM":
          e.preventDefault()
          toggleMute()
          break
        case "KeyF":
          e.preventDefault()
          toggleFullscreen()
          break
      }
    }
    window.addEventListener("keydown", handler)
    return () => window.removeEventListener("keydown", handler)
    // stable refs only — safe to run once
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  if (error) {
    return (
      <div className="flex h-full w-full flex-col items-center justify-center bg-black text-white">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="mb-4 h-12 w-12 text-red-400">
          <circle cx="12" cy="12" r="10" />
          <line x1="12" y1="8" x2="12" y2="12" />
          <line x1="12" y1="16" x2="12.01" y2="16" />
        </svg>
        <p className="text-sm text-white/60">{error}</p>
      </div>
    )
  }

  return (
    <div
      ref={containerRef}
      className="relative h-full w-full overflow-hidden bg-black select-none"
      tabIndex={0}
      onMouseMove={showControlsTemp}
      onTouchStart={showControlsTemp}
      onClick={handleContainerClick}
    >
      <style>{STYLES}</style>

      <video
        ref={videoRef}
        className="watchify-video"
        playsInline
        autoPlay={autoplay}
        preload="auto"
      >
        {subtitles?.map((sub, i) => (
          <track
            key={i}
            kind="subtitles"
            src={sub.url}
            srcLang={sub.language}
            label={sub.label}
          />
        ))}
      </video>

      {loading && (
        <div className="absolute inset-0 z-20 flex items-center justify-center pointer-events-none">
          <div className="h-10 w-10 rounded-full border-2 border-white/20 border-t-purple-500 animate-spin" />
        </div>
      )}

      {showResumePrompt && savedProgress && (
        <div className="absolute inset-0 z-40 flex flex-col items-center justify-center bg-black/70 backdrop-blur-sm">
          <p className="text-lg font-medium text-white">Resume from {formatTime(savedProgress.currentTime)}?</p>
          <div className="mt-4 flex gap-3">
            <button
              onClick={(e) => { e.stopPropagation(); resumeFromSaved(); }}
              className="rounded-full bg-[#8B5CF6] px-6 py-2.5 text-sm font-semibold text-white transition-all hover:bg-[#7C3AED] hover:scale-105"
            >
              Resume
            </button>
            <button
              onClick={(e) => { e.stopPropagation(); dismissResume(); }}
              className="rounded-full border border-white/10 bg-white/5 px-6 py-2.5 text-sm font-medium text-white/70 transition-all hover:bg-white/10 hover:text-white"
            >
              Start Over
            </button>
          </div>
        </div>
      )}

      {autoplayBlocked && !playing && (
        <div className="absolute inset-0 z-30 flex items-center justify-center pointer-events-none">
          <div className="flex h-20 w-20 items-center justify-center rounded-full bg-white/10 backdrop-blur-sm">
            <svg viewBox="0 0 24 24" fill="white" width={48} height={48} className="ml-1 drop-shadow-lg">
              <path d="M8 5.14v14l11-7-11-7z" />
            </svg>
          </div>
        </div>
      )}

      {!loading && !playing && !autoplayBlocked && !showResumePrompt && (
        <div className="absolute inset-0 z-10 flex items-center justify-center pointer-events-none">
          <svg viewBox="0 0 24 24" fill="white" width={64} height={64} className="opacity-80 drop-shadow-lg">
            <path d="M8 5.14v14l11-7-11-7z" />
          </svg>
        </div>
      )}

      {skipIndicator && (
        <div className="absolute left-1/2 top-1/2 z-20 -translate-x-1/2 -translate-y-1/2 pointer-events-none">
          <div className="flex items-center gap-2 rounded-full bg-black/60 px-4 py-2 text-white">
            <svg viewBox="0 0 24 24" fill="currentColor" width={20} height={20} className={skipIndicator < 0 ? "" : "rotate-180"}>
              <path d="M6 6h2v12H6zm3.5 6l8.5 6V6z" />
            </svg>
            <span className="text-sm font-medium">{Math.abs(skipIndicator)}s</span>
          </div>
        </div>
      )}

      {showNextEpisode && onNextEpisode && (
        <div
          className="absolute bottom-20 right-4 z-30 flex items-center gap-3 rounded-lg bg-black/80 backdrop-blur-xl border border-white/10 p-3 shadow-xl"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="flex flex-col">
            <span className="text-[11px] text-white/60 uppercase tracking-wider font-semibold">Up Next</span>
            <span className="text-sm font-medium text-white max-w-[200px] truncate">{nextEpisodeTitle || "Next Episode"}</span>
          </div>
          <button
            onClick={(e) => { e.stopPropagation(); onNextEpisode(); }}
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-white text-black hover:scale-105 transition-transform"
          >
            <svg viewBox="0 0 24 24" fill="currentColor" width={20} height={20}>
              <path d="M6 4l15 8-15 8z" />
            </svg>
          </button>
        </div>
      )}

      <div className={`absolute inset-x-0 bottom-0 z-10 transition-opacity duration-300 ${showControls ? "opacity-100" : "opacity-0 pointer-events-none"}`}>
        <div className="bg-gradient-to-t from-black/80 to-transparent px-4 pb-3 pt-12">
          <div className="relative mb-2">
            <div
              className="relative h-1 cursor-pointer group"
              onClick={(e) => { e.stopPropagation(); seek(e); }}
              onMouseMove={(e) => {
                if (e.buttons !== 1) return
                e.stopPropagation()
                seek(e)
              }}
            >
              <div className="absolute inset-0 rounded-full bg-white/20" />
              <div className="absolute inset-y-0 left-0 rounded-full bg-white/30" style={{ width: `${buffered}%` }} />
              <div className="absolute inset-y-0 left-0 rounded-full bg-purple-500 group-hover:bg-purple-400 transition-colors" style={{ width: `${progressPct}%` }}>
                <div className="absolute right-0 top-1/2 -translate-y-1/2 h-3 w-3 rounded-full bg-white opacity-0 group-hover:opacity-100 transition-opacity shadow" />
              </div>
            </div>
          </div>

          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-1">
              <button onClick={(e) => { e.stopPropagation(); togglePlay(); }} className="p-1.5 text-white/80 hover:text-white">
                {playing ? (
                  <svg viewBox="0 0 24 24" fill="currentColor" width={22} height={22}>
                    <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z" />
                  </svg>
                ) : (
                  <svg viewBox="0 0 24 24" fill="currentColor" width={22} height={22}>
                    <path d="M8 5.14v14l11-7-11-7z" />
                  </svg>
                )}
              </button>

              <button onClick={(e) => { e.stopPropagation(); skip(-10); }} className="p-1.5 text-white/60 hover:text-white">
                <svg viewBox="0 0 24 24" fill="currentColor" width={18} height={18}>
                  <path d="M6 6h2v12H6zm3.5 6l8.5 6V6z" />
                </svg>
              </button>

              <button onClick={(e) => { e.stopPropagation(); skip(10); }} className="p-1.5 text-white/60 hover:text-white">
                <svg viewBox="0 0 24 24" fill="currentColor" width={18} height={18}>
                  <path d="M6 18l8.5-6L6 6v12z" />
                </svg>
              </button>

              <div className="relative flex items-center group/mute ml-1">
                <button onClick={(e) => { e.stopPropagation(); toggleMute(); }} className="p-1.5 text-white/80 hover:text-white">
                  {muted || volume === 0 ? (
                    <svg viewBox="0 0 24 24" fill="currentColor" width={20} height={20}>
                      <path d="M16.5 12c0-1.77-1.02-3.29-2.5-4.03v2.21l2.45 2.45c.03-.2.05-.41.05-.63zm2.5 0c0 .94-.2 1.82-.54 2.64l1.51 1.51C20.63 14.91 21 13.5 21 12c0-4.28-2.99-7.86-7-8.77v2.06c2.89.86 5 3.54 5 6.71zM4.27 3L3 4.27 7.73 9H3v6h4l5 5v-6.73l4.25 4.25c-.67.52-1.42.93-2.25 1.18v2.06c1.38-.31 2.63-.95 3.69-1.81L19.73 21 21 19.73l-9-9L4.27 3zM12 4L9.91 6.09 12 8.18V4z" />
                    </svg>
                  ) : volume < 0.5 ? (
                    <svg viewBox="0 0 24 24" fill="currentColor" width={20} height={20}>
                      <path d="M18.5 12c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM5 9v6h4l5 5V4L9 9H5z" />
                    </svg>
                  ) : (
                    <svg viewBox="0 0 24 24" fill="currentColor" width={20} height={20}>
                      <path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z" />
                    </svg>
                  )}
                </button>
                <div ref={volumeRef} className="hidden group-hover/mute:flex items-center w-0 group-hover/mute:w-20 overflow-hidden transition-all duration-200">
                  <div
                    className="relative h-1 w-full cursor-pointer rounded-full bg-white/20"
                    onClick={(e) => { e.stopPropagation(); const r = e.currentTarget.getBoundingClientRect(); setVolumeLevel((e.clientX - r.left) / r.width); }}
                  >
                    <div className="absolute inset-y-0 left-0 rounded-full bg-white" style={{ width: `${muted ? 0 : volume * 100}%` }} />
                  </div>
                </div>
              </div>

              <span
                className="text-xs text-white/60 font-mono ml-1 cursor-pointer hover:text-white/80"
                onClick={(e) => { e.stopPropagation(); setShowTimeRemaining(!showTimeRemaining); }}
              >
                {formatTime(displayTime)} / {formatTime(duration)}
              </span>
            </div>

            <div className="flex items-center gap-1">
              <span className="hidden sm:inline text-xs text-white/60 mr-1">
                {playbackRate !== 1 ? `${playbackRate}x` : ""}
              </span>

              <div className="relative">
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    const next = !showServerMenu
                    setShowServerMenu(next)
                    if (next) { setShowSettings(false); setShowSubtitlesMenu(false) }
                    setShowControls(true)
                    clearTimeout(controlsTimer.current)
                  }}
                  className="px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wider rounded-full border border-white/20 text-white/80 hover:text-white hover:border-white/40 transition-colors"
                  title="Server"
                >
                  {server}
                </button>

                {showServerMenu && (
                  <div
                    className="absolute bottom-full right-0 mb-2 w-36 rounded-lg bg-black/90 backdrop-blur-xl border border-white/10 py-1 shadow-xl"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <div className="px-3 py-1.5 text-[11px] font-semibold uppercase tracking-wider text-white/40">Server</div>
                    {(servers ?? [server]).map((s) => (
                      <button
                        key={s}
                        onClick={() => { onServerChange?.(s); setShowServerMenu(false) }}
                        className={`flex w-full items-center px-3 py-1.5 text-sm ${server === s ? "text-purple-400" : "text-white/80 hover:text-white hover:bg-white/5"}`}
                      >
                        {s}
                        {server === s && (
                          <svg viewBox="0 0 24 24" fill="currentColor" width={16} height={16} className="ml-auto">
                            <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z" />
                          </svg>
                        )}
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {subtitles && subtitles.length > 0 && (
                <div className="relative">
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      const next = !showSubtitlesMenu
                      setShowSubtitlesMenu(next)
                      if (next) setShowSettings(false)
                      setShowControls(true)
                      clearTimeout(controlsTimer.current)
                    }}
                    className={`p-1.5 ${selectedSubtitleLabel ? "text-purple-400" : "text-white/80 hover:text-white"}`}
                    title="Subtitles"
                  >
                    <svg viewBox="0 0 24 24" fill="currentColor" width={20} height={20}>
                      <path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-8 12H7v-2h4v2zm6 0h-4v-2h4v2zm-6-4H7v-2h4v2zm6 0h-4v-2h4v2z" />
                    </svg>
                  </button>

                  {showSubtitlesMenu && (
                    <div
                      className="absolute bottom-full right-0 mb-2 w-48 rounded-lg bg-black/90 backdrop-blur-xl border border-white/10 py-1 shadow-xl"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <div className="px-3 py-1.5 text-[11px] font-semibold uppercase tracking-wider text-white/40">Subtitles</div>
                      <button
                        onClick={() => { setSelectedSubtitleLabel(null); setShowSubtitlesMenu(false); }}
                        className={`flex w-full items-center px-3 py-1.5 text-sm ${selectedSubtitleLabel === null ? "text-purple-400" : "text-white/80 hover:text-white hover:bg-white/5"}`}
                      >
                        Off
                        {selectedSubtitleLabel === null && (
                          <svg viewBox="0 0 24 24" fill="currentColor" width={16} height={16} className="ml-auto">
                            <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z" />
                          </svg>
                        )}
                      </button>
                      {subtitles.map((sub) => (
                        <button
                          key={sub.label + sub.language}
                          onClick={() => { setSelectedSubtitleLabel(sub.label); setShowSubtitlesMenu(false); }}
                          className={`flex w-full items-center px-3 py-1.5 text-sm ${selectedSubtitleLabel === sub.label ? "text-purple-400" : "text-white/80 hover:text-white hover:bg-white/5"}`}
                        >
                          {sub.label}
                          {selectedSubtitleLabel === sub.label && (
                            <svg viewBox="0 0 24 24" fill="currentColor" width={16} height={16} className="ml-auto">
                              <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z" />
                            </svg>
                          )}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              )}

              <div className="relative">
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    const next = !showSettings
                    setShowSettings(next)
                    if (next) setShowSubtitlesMenu(false)
                    setShowControls(true)
                    clearTimeout(controlsTimer.current)
                  }}
                  className="p-1.5 text-white/80 hover:text-white"
                >
                  <svg viewBox="0 0 24 24" fill="currentColor" width={20} height={20}>
                    <path d="M19.14 12.94c.04-.3.06-.61.06-.94 0-.32-.02-.64-.07-.94l2.03-1.58a.49.49 0 00.12-.61l-1.92-3.32a.49.49 0 00-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54a.484.484 0 00-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96a.49.49 0 00-.59.22L2.74 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.05.3-.07.62-.07.94s.02.64.07.94l-2.03 1.58a.49.49 0 00-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6z" />
                  </svg>
                </button>

                {showSettings && (
                  <div
                    className="absolute bottom-full right-0 mb-2 w-48 rounded-lg bg-black/90 backdrop-blur-xl border border-white/10 py-1 shadow-xl"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <div className="px-3 py-1.5 text-[11px] font-semibold uppercase tracking-wider text-white/40">Speed</div>
                    {[0.5, 1, 1.5, 2].map((rate) => (
                      <button
                        key={rate}
                        onClick={() => changeSpeed(rate)}
                        className={`flex w-full items-center px-3 py-1.5 text-sm ${playbackRate === rate ? "text-purple-400" : "text-white/80 hover:text-white hover:bg-white/5"}`}
                      >
                        {rate === 1 ? "Normal" : `${rate}x`}
                        {playbackRate === rate && (
                          <svg viewBox="0 0 24 24" fill="currentColor" width={16} height={16} className="ml-auto">
                            <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z" />
                          </svg>
                        )}
                      </button>
                    ))}
                    {qualities.length > 0 && (
                      <>
                        <div className="mt-1 border-t border-white/10" />
                        <div className="px-3 py-1.5 text-[11px] font-semibold uppercase tracking-wider text-white/40">Quality</div>
                        <button
                          onClick={() => changeQuality(-1)}
                          className={`flex w-full items-center px-3 py-1.5 text-sm ${currentQuality === -1 ? "text-purple-400" : "text-white/80 hover:text-white hover:bg-white/5"}`}
                        >
                          Auto
                          {currentQuality === -1 && (
                            <svg viewBox="0 0 24 24" fill="currentColor" width={16} height={16} className="ml-auto">
                              <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z" />
                            </svg>
                          )}
                        </button>
                        {qualities.map((q) => (
                          <button
                            key={q.index}
                            onClick={() => changeQuality(q.index)}
                            className={`flex w-full items-center px-3 py-1.5 text-sm ${currentQuality === q.index ? "text-purple-400" : "text-white/80 hover:text-white hover:bg-white/5"}`}
                          >
                            {q.label}
                            {currentQuality === q.index && (
                              <svg viewBox="0 0 24 24" fill="currentColor" width={16} height={16} className="ml-auto">
                                <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z" />
                              </svg>
                            )}
                          </button>
                        ))}
                      </>
                    )}
                  </div>
                )}
              </div>

              <button
                onClick={(e) => { e.stopPropagation(); togglePiP(); }}
                className="p-1.5 text-white/80 hover:text-white hidden sm:flex"
                title="Picture-in-Picture"
              >
                <svg viewBox="0 0 24 24" fill="currentColor" width={20} height={20}>
                  <path d="M19 11h-8v6h8v-6zm4 8V4.98C23 3.88 22.1 3 21 3H3c-1.1 0-2 .88-2 1.98V19c0 1.1.9 2 2 2h18c1.1 0 2-.9 2-2zm-2 .02H3V4.97h18v14.05z" />
                </svg>
              </button>

              <button onClick={(e) => { e.stopPropagation(); toggleFullscreen(); }} className="p-1.5 text-white/80 hover:text-white">
                {fullscreen ? (
                  <svg viewBox="0 0 24 24" fill="currentColor" width={20} height={20}>
                    <path d="M5 16h3v3h2v-5H5v2zm3-8H5v2h5V5H8v3zm6 11h2v-3h3v-2h-5v5zm2-11V5h-2v5h5V8h-3z" />
                  </svg>
                ) : (
                  <svg viewBox="0 0 24 24" fill="currentColor" width={20} height={20}>
                    <path d="M7 14H5v5h5v-2H7v-3zm-2-4h2V7h3V5H5v5zm12 7h-3v2h5v-5h-2v3zM14 5v2h3v3h2V5h-5z" />
                  </svg>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

const STYLES = `
  .watchify-video {
    position: absolute !important;
    inset: 0 !important;
    width: 100% !important;
    height: 100% !important;
    object-fit: cover;
  }
`
