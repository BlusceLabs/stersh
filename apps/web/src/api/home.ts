import { api } from "./client"

export interface HomepageResponse {
  hero: {
    id: number
    title: string
    overview: string
    backdropPath: string
    logoPath: string
    trailerKey: string
    releaseYear?: string
    runtime?: string
    rating?: number
  }[]

  rows: {
    id: string
    title: string

    items: {
      id: number
      title: string
      posterPath: string
      mediaType?: string
      year?: string
      rating?: number
    }[]
  }[]
}

export async function getHomepage() {
  return api.get<HomepageResponse>(
    "/home"
  )
}
