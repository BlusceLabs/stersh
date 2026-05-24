import { api } from "./client"

export interface Movie {
  id: number
  title: string
  posterPath: string
  backdropPath: string
  rating: number
  year: string
}

interface TrendingResponse {
  results: Movie[]
}

export async function getTrendingMovies() {
  return api.get<TrendingResponse>("/movies/trending")
}
