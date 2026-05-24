import { useCallback, useEffect, useState } from "react"
import { motion } from "framer-motion"
import {
  Clock3,
  Play,
  Plus,
  Check,
  Heart,
  Star,
  Calendar,
  Building2,
} from "lucide-react"
import { useNavigate, useParams } from "@tanstack/react-router"

import {
  getMovieDetailsBySlug,
  getTVDetailsBySlug,
  getCredits,
  getSimilar,
  getTVSeason,
} from "@/api/details"
import type { MovieDetails, CastMember, SimilarItem, Episode, SeasonInfo, ProductionCompany } from "@/api/details"

import { useWatchlist } from "@/stores/watchlist"
import { useLiked } from "@/stores/liked"
import { AmbientBackground } from "@/components/cinematic/AmbientBackground/AmbientBackground"
import { DetailsSkeleton } from "@/components/shared/LoadingSkeleton"

import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Separator } from "@/components/ui/separator"
import { ScrollArea, ScrollBar } from "@/components/ui/scroll-area"
import { cn } from "@/lib/utils"

export default function DetailsPage() {
  const navigate = useNavigate()
  const { type, slug } = useParams({
    from: "/details/$type/$slug",
  })

  const [movie, setMovie] = useState<MovieDetails | null>(null)
  const [cast, setCast] = useState<CastMember[]>([])
  const [similar, setSimilar] = useState<SimilarItem[]>([])
  const [selectedSeason, setSelectedSeason] = useState<number>(1)
  const [episodes, setEpisodes] = useState<Episode[]>([])
  const [error, setError] = useState<Error | null>(null)

  const addToWatchlist = useWatchlist((s) => s.add)
  const removeFromWatchlist = useWatchlist((s) => s.remove)
  const isInWatchlist = useWatchlist((s) => s.isInWatchlist)

  const toggleLiked = useLiked((s) => s.toggle)
  const isLiked = useLiked((s) => s.isLiked)

  const load = useCallback(async () => {
    try {
      setError(null)
      setMovie(null)
      setCast([])
      setSimilar([])
      setEpisodes([])

      const fn = type === "tv" ? getTVDetailsBySlug : getMovieDetailsBySlug
      const data = await fn(slug)
      setMovie(data)

      const id = String(data.id)
      const mediaType = data.mediaType || type
      const [creditsRes, similarRes] = await Promise.all([
        getCredits(id, mediaType).catch(() => null),
        getSimilar(id, mediaType).catch(() => null),
      ])

      if (creditsRes) setCast(creditsRes.cast.slice(0, 12))
      if (similarRes) setSimilar(similarRes.results.slice(0, 12))

      if (mediaType === "tv" && data.seasons && data.seasons.length > 0) {
        const firstSeason = data.seasons[0].seasonNumber
        setSelectedSeason(firstSeason)
        const seasonData = await getTVSeason(id, firstSeason).catch(() => null)
        if (seasonData) setEpisodes(seasonData.episodes)
      }
    } catch (err) {
      console.error(err)
      setError(err instanceof Error ? err : new Error("Failed to load details"))
    }
  }, [slug, type])

  useEffect(() => {
    load()
  }, [load])

  const loadSeason = useCallback(async (seasonNum: number) => {
    if (!movie) return
    setSelectedSeason(seasonNum)
    const seasonData = await getTVSeason(String(movie.id), seasonNum).catch(() => null)
    if (seasonData) setEpisodes(seasonData.episodes)
  }, [movie])

  if (error) {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center bg-background text-foreground">
        <div className="text-center">
          <div className="mx-auto mb-6 flex h-20 w-20 items-center justify-center rounded-full bg-destructive/10">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-10 w-10 text-destructive">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
          </div>
          <h2 className="text-2xl font-semibold">Failed to load details</h2>
          <p className="mt-3 text-muted-foreground">{error.message}</p>
          <Button onClick={load} className="mt-8 rounded-full px-8">
            Try Again
          </Button>
        </div>
      </main>
    )
  }

  if (!movie) {
    return <DetailsSkeleton />
  }

  const isTV = movie.mediaType === "tv"
  const seasons: SeasonInfo[] = movie.seasons || []

  return (
    <main className="relative min-h-screen overflow-hidden bg-background text-foreground">
      <AmbientBackground />

      {/* BACKDROP */}
      <div className="absolute inset-0">
        <img
          src={movie.backdropPath}
          alt={movie.title}
          loading="lazy"
          decoding="async"
          className="h-full w-full object-cover opacity-40"
        />
        <div className="absolute inset-0 bg-gradient-to-r from-background via-background/80 to-transparent" />
        <div className="absolute inset-0 bg-gradient-to-t from-background via-transparent to-black/50" />
      </div>

      {/* CONTENT */}
      <section className="relative z-20 flex min-h-screen items-end px-6 pb-20 pt-32 md:px-16">
        <motion.div
          initial={{ opacity: 0, y: 60 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 1, ease: [0.22, 1, 0.36, 1] }}
          className="grid w-full gap-12 lg:grid-cols-[300px_1fr]"
        >
          {/* POSTER */}
          <div className="hidden lg:block">
            <img
              src={movie.posterPath}
              alt={movie.title}
              loading="lazy"
              decoding="async"
              className="w-full rounded-3xl border border-border shadow-2xl"
            />
          </div>

          {/* INFO */}
          <div className="max-w-3xl">
            {/* LOGO / TITLE */}
            {movie.logoPath ? (
              <img
                src={movie.logoPath}
                alt={movie.title}
                loading="lazy"
                decoding="async"
                className="mb-6 max-h-32 max-w-[380px] object-contain"
              />
            ) : (
              <h1 className="text-4xl font-semibold tracking-tight md:text-6xl lg:text-7xl">
                {movie.title}
              </h1>
            )}

            {/* META */}
            <div className="mb-6 mt-5 flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
              <div className="flex items-center gap-1.5">
                <Star size={14} className="text-primary" fill="currentColor" />
                <span className="text-foreground font-medium">{movie.rating.toFixed(1)}</span>
              </div>

              <Separator orientation="vertical" className="h-4" />

              {movie.runtime && (
                <div className="flex items-center gap-1.5">
                  <Clock3 size={14} />
                  <span>{movie.runtime}</span>
                </div>
              )}

              <Separator orientation="vertical" className="h-4" />

              <div className="flex items-center gap-1.5">
                <Calendar size={14} />
                <span>{movie.year}</span>
              </div>

              <Separator orientation="vertical" className="h-4" />

              <Badge variant="secondary" className="rounded-full">
                {movie.genres.join(" \u2022 ")}
              </Badge>

              {isTV && seasons.length > 0 && (
                <Badge variant="outline" className="rounded-full">
                  {seasons.length} Season{seasons.length > 1 ? "s" : ""}
                </Badge>
              )}
            </div>

            {/* PRODUCTION COMPANIES */}
            {movie.productionCompanies && movie.productionCompanies.length > 0 && (
              <div className="mb-6 flex flex-wrap items-center gap-3">
                <Building2 size={14} className="text-muted-foreground" />
                {movie.productionCompanies.map((company: ProductionCompany) => (
                  <a
                    key={company.id}
                    href={`https://www.themoviedb.org/company/${company.id}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="group flex items-center gap-2 rounded-md border border-border bg-secondary/50 px-2.5 py-1.5 transition-colors hover:bg-secondary"
                  >
                    {company.logoPath ? (
                      <img
                        src={company.logoPath}
                        alt={company.name}
                        className="h-4 w-auto max-w-[70px] object-contain invert opacity-60 group-hover:opacity-100 transition-opacity"
                      />
                    ) : (
                      <span className="text-xs font-medium text-muted-foreground">{company.name}</span>
                    )}
                  </a>
                ))}
              </div>
            )}

            {/* OVERVIEW */}
            <p className="max-w-2xl text-base leading-7 text-muted-foreground md:text-lg md:leading-8">
              {movie.overview}
            </p>

            {/* ACTIONS */}
            <div className="mt-10 flex flex-wrap gap-3">
              <Button
                size="lg"
                className="rounded-full bg-gradient-to-r from-primary to-cyan-500 text-primary-foreground hover:opacity-90 gap-2 px-8"
                onClick={() => {
                  if (isTV) {
                    navigate({
                      to: "/watch/$type/$slug/$season/$episode",
                      params: { type: "tv", slug, season: "sn1", episode: "ep1" },
                    })
                  } else {
                    navigate({ to: "/watch/$type/$slug", params: { type: movie.mediaType || "movie", slug } })
                  }
                }}
              >
                <Play size={18} />
                Watch Now
              </Button>

              <Button
                size="lg"
                variant="outline"
                className={cn(
                  "rounded-full gap-2 px-6",
                  isInWatchlist(movie.id) && "border-green-500/30 bg-green-500/10 text-green-400 hover:bg-green-500/20 hover:text-green-400"
                )}
                onClick={() => {
                  if (isInWatchlist(movie.id)) {
                    removeFromWatchlist(movie.id)
                  } else {
                    addToWatchlist({
                      id: movie.id,
                      title: movie.title,
                      posterPath: movie.posterPath,
                      mediaType: movie.mediaType || "movie",
                      year: movie.year,
                    })
                  }
                }}
              >
                {isInWatchlist(movie.id) ? <Check size={18} /> : <Plus size={18} />}
                {isInWatchlist(movie.id) ? "In Watchlist" : "Watchlist"}
              </Button>

              <Button
                size="lg"
                variant="outline"
                className={cn(
                  "rounded-full h-11 w-11 p-0",
                  isLiked(movie.id) && "border-red-500/30 bg-red-500/10 text-red-400 hover:bg-red-500/20 hover:text-red-400"
                )}
                onClick={() =>
                  toggleLiked({
                    id: movie.id,
                    title: movie.title,
                    posterPath: movie.posterPath,
                    mediaType: movie.mediaType || "movie",
                    year: movie.year,
                  })
                }
              >
                <Heart size={18} fill={isLiked(movie.id) ? "currentColor" : "none"} />
              </Button>
            </div>
          </div>
        </motion.div>
      </section>

      <Separator className="relative z-20 mx-6 md:mx-16 bg-border/50" />

      {/* CAST */}
      {cast.length > 0 && (
        <section className="relative z-20 px-6 py-12 md:px-16">
          <h2 className="mb-6 text-xl font-semibold tracking-tight">Cast</h2>
          <ScrollArea className="w-full whitespace-nowrap">
            <div className="flex gap-4 pb-4">
              {cast.map((member) => (
                <div key={member.id} className="w-32 shrink-0 space-y-2">
                  <div className="aspect-[2/3] overflow-hidden rounded-xl bg-muted">
                    {member.profilePath ? (
                      <img
                        src={member.profilePath}
                        alt={member.name}
                        loading="lazy"
                        className="h-full w-full object-cover"
                      />
                    ) : (
                      <div className="flex h-full items-center justify-center text-muted-foreground/30">
                        <svg viewBox="0 0 24 24" fill="currentColor" width={32} height={32}>
                          <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z" />
                        </svg>
                      </div>
                    )}
                  </div>
                  <p className="text-sm font-medium text-foreground truncate">{member.name}</p>
                  <p className="text-xs text-muted-foreground truncate">{member.character}</p>
                </div>
              ))}
            </div>
            <ScrollBar orientation="horizontal" />
          </ScrollArea>
        </section>
      )}

      {/* TV SEASONS & EPISODES */}
      {isTV && seasons.length > 0 && (
        <section className="relative z-20 px-6 py-12 md:px-16">
          <Tabs
            value={String(selectedSeason)}
            onValueChange={(v) => loadSeason(Number(v))}
            className="w-full"
          >
            <div className="flex items-center gap-4 mb-6">
              <h2 className="text-xl font-semibold tracking-tight">Episodes</h2>
              <TabsList className="rounded-full bg-secondary/50">
                {seasons.map((s) => (
                  <TabsTrigger
                    key={s.seasonNumber}
                    value={String(s.seasonNumber)}
                    className="rounded-full data-[state=active]:bg-foreground data-[state=active]:text-background text-xs px-3"
                  >
                    S{s.seasonNumber}
                  </TabsTrigger>
                ))}
              </TabsList>
            </div>

            <div className="grid gap-3">
              {episodes.map((ep) => (
                <div
                  key={ep.episodeNumber}
                  className="group flex gap-4 rounded-xl border border-border/50 bg-card/30 p-3 transition-all hover:bg-card/60 hover:border-border"
                >
                  <div className="w-40 shrink-0 overflow-hidden rounded-lg bg-muted aspect-video">
                    {ep.stillPath ? (
                      <img
                        src={ep.stillPath}
                        alt={ep.name}
                        loading="lazy"
                        className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
                      />
                    ) : (
                      <div className="flex h-full items-center justify-center text-muted-foreground/30">
                        <Play size={24} />
                      </div>
                    )}
                  </div>
                  <div className="flex flex-1 flex-col justify-center min-w-0">
                    <div className="flex items-center gap-3">
                      <span className="text-sm font-semibold text-muted-foreground">E{ep.episodeNumber}</span>
                      <h3 className="text-sm font-medium text-foreground truncate">{ep.name}</h3>
                      {ep.runtime > 0 && (
                        <span className="text-xs text-muted-foreground shrink-0">{ep.runtime}m</span>
                      )}
                    </div>
                    <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">{ep.overview}</p>
                  </div>
                  <Button
                    size="icon"
                    variant="ghost"
                    className="shrink-0 self-center rounded-full opacity-0 group-hover:opacity-100 transition-opacity"
                    onClick={() => navigate({
                      to: "/watch/$type/$slug/$season/$episode",
                      params: { type: "tv", slug, season: "sn" + selectedSeason, episode: "ep" + ep.episodeNumber },
                    })}
                  >
                    <Play size={18} fill="currentColor" />
                  </Button>
                </div>
              ))}
            </div>
          </Tabs>
        </section>
      )}

      <Separator className="relative z-20 mx-6 md:mx-16 bg-border/50" />

      {/* SIMILAR */}
      {similar.length > 0 && (
        <section className="relative z-20 px-6 py-12 md:px-16 pb-24">
          <h2 className="mb-6 text-xl font-semibold tracking-tight">More Like This</h2>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6">
            {similar.map((item) => (
              <div
                key={item.id}
                onClick={() => navigate({ to: "/details/$type/$slug", params: { type: item.mediaType, slug: item.title.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "") } })}
                className="group cursor-pointer"
              >
                <div className="aspect-[2/3] overflow-hidden rounded-xl bg-muted">
                  {item.posterPath ? (
                    <img
                      src={item.posterPath}
                      alt={item.title}
                      loading="lazy"
                      className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
                    />
                  ) : (
                    <div className="flex h-full items-center justify-center text-muted-foreground/30">
                      <svg viewBox="0 0 24 24" fill="currentColor" width={32} height={32}>
                        <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z" />
                      </svg>
                    </div>
                  )}
                </div>
                <p className="mt-2 text-sm font-medium text-foreground/80 truncate">{item.title}</p>
                <p className="text-xs text-muted-foreground">{item.year}</p>
              </div>
            ))}
          </div>
        </section>
      )}
    </main>
  )
}
