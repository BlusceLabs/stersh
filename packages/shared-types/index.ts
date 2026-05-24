export interface Movie {
  id: number
  title: string
  posterPath: string
  backdropPath?: string
  rating?: number
  year?: string
}

export interface TVShow {
  id: number
  name: string
  posterPath: string
  backdropPath?: string
  rating?: number
  firstAirDate?: string
}

export interface VideoSource {
  url: string
  quality: string
  resolution: number
}
