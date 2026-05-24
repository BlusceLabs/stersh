import { api } from "./client"

export interface SeasonInfo {
  seasonNumber: number
  episodeCount: number
}

export interface ProductionCompany {
  id: number
  name: string
  logoPath: string
  originCountry: string
}

export interface MovieDetails {
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
  imdbId?: string
  seasons?: SeasonInfo[]
  numberOfSeasons?: number
  productionCompanies?: ProductionCompany[]
}

export interface CastMember {
  id: number
  name: string
  character: string
  profilePath: string
  order: number
}

export interface CreditsResponse {
  cast: CastMember[]
}

export interface SimilarItem {
  id: number
  title: string
  overview: string
  posterPath: string
  year: string
  mediaType: string
}

export interface SimilarResponse {
  results: SimilarItem[]
}

export interface Episode {
  episodeNumber: number
  name: string
  overview: string
  stillPath: string
  airDate: string
  runtime: number
}

export interface SeasonDetailsResponse {
  seasonNumber: number
  episodes: Episode[]
}

export async function getMovieDetails(id: string) {
  return api.get<MovieDetails>(`/details/${id}`)
}

export async function getMovieDetailsBySlug(slug: string) {
  return api.get<MovieDetails>(`/details/by-slug/${slug}`)
}

export async function getTVDetailsBySlug(slug: string) {
  return api.get<MovieDetails>(`/details/tv/by-slug/${slug}`)
}

export async function getCredits(id: string, mediaType: string) {
  return api.get<CreditsResponse>(`/details/${id}/credits?mediaType=${mediaType}`)
}

export async function getSimilar(id: string, mediaType: string) {
  return api.get<SimilarResponse>(`/details/${id}/similar?mediaType=${mediaType}`)
}

export async function getTVSeason(id: string, season: number) {
  return api.get<SeasonDetailsResponse>(`/tv/${id}/season?season=${season}`)
}
