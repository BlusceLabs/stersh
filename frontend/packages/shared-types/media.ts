// src/types/media.ts

/**
 * Clean data model for a feature film entry.
 */
export interface Movie {
  id: number
  title: string
  posterPath: string
  backdropPath?: string
  rating?: number
  year?: string
  /** Explicit discriminator type to simplify server routing logic */
  mediaType: 'movie'
}

/**
 * Clean data model for an episodic broadcast series.
 */
export interface TVShow {
  id: number
  name: string
  posterPath: string
  backdropPath?: string
  rating?: number
  firstAirDate?: string
  /** Explicit discriminator type to simplify server routing logic */
  mediaType: 'tv'
}

/**
 * Structural stream metadata definition targeting the internal media engine.
 */
export interface VideoSource {
  url: string
  /** Quality label tier descriptor (e.g., 'HD', '4K Ultra HD', 'SD') */
  quality: string
  /** Progressive line height standard (e.g., 720, 1080, 2160) */
  resolution: number
}

/* Composite Helper Utilities */

/**
 * Unified compound union type.
 * Perfect for typing variable collections like interactive carousels or unified search results.
 */
export type MediaItem = Movie | TVShow;

/**
 * Collection signature representing a full api result framework payload.
 */
export interface MediaCatalogResponse<T extends MediaItem> {
  page: number;
  results: T[];
  total_pages: number;
  total_results: number;
}