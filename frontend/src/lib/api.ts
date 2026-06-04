// src/lib/api.ts

// Use relative paths so requests go through the Vite/Astro proxy to the backend
const API_BASE = import.meta.env.BACKEND_URL || '';

/**
 * Core Network Interface Handler 
 */
export const api = {
  get: async (path: string, token?: string) => {
    const headers: Record<string, string> = {
      'Accept': 'application/json',
      'Content-Type': 'application/json',
    };
    
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    
    const response = await fetch(`${API_BASE}${path}`, { headers });
    
    if (!response.ok) {
      // Prevent pipeline crashes during server-side compilation
      console.error(`[Watchfy API Network Fault] Path: ${path} | Status: ${response.status} ${response.statusText}`);
      throw new Error(`Watchfy Handshake Exception: ${response.statusText}`);
    }
    
    return response.json();
  },
  
  /**
   * Generates production paths targeting internal streaming instances
   */
  getStreamSource: (tmdbId: number, mediaType: 'movie' | 'tv', season?: number, episode?: number, server: string = 'white'): string => {
    const allowedServers = new Set(['white', 'black']);
    const safeServer = allowedServers.has(server) ? server : 'white';
    const safeMedia: 'movie' | 'tv' = mediaType === 'tv' ? 'tv' : 'movie';
    const safeTmdb = Number.isFinite(tmdbId) && tmdbId > 0 ? Math.floor(tmdbId) : 0;
    let url = `/api/${safeServer}/source?tmdbId=${safeTmdb}&mediaType=${safeMedia}`;
    if (safeMedia === 'tv' && Number.isFinite(season) && Number.isFinite(episode)) {
      url += `&season=${Math.max(1, Math.floor(season as number))}&episode=${Math.max(1, Math.floor(episode as number))}`;
    }
    return url;
  },
};

/**
 * Organized TMDB Endpoint Gateway
 */
export const tmdbApi = {
  trending: (mediaType: 'movie' | 'tv', timeWindow: 'day' | 'week' = 'day'): Promise<any> => 
    api.get(`/api/tmdb/trending/${mediaType}/${timeWindow}`),
  
  popular: (mediaType: 'movie' | 'tv', page: number = 1): Promise<any> => 
    api.get(`/api/tmdb/${mediaType}/popular?page=${page}`),
  
  topRated: (mediaType: 'movie' | 'tv', page: number = 1): Promise<any> =>
    api.get(`/api/tmdb/${mediaType}/top_rated?page=${page}`),

  /**
   * TMDB discover — the proper way to filter by genre/year/runtime.
   * Pass any discover param via the second arg (e.g. { with_genres: '27', sort_by: 'vote_average.desc' }).
   * `with_genres` accepts either a comma- or pipe-separated list.
   */
  discover: (
    mediaType: 'movie' | 'tv',
    params: {
      with_genres?: string | number | number[];
      sort_by?: string;
      primary_release_year?: number;
      first_air_date_year?: number;
      vote_count_gte?: number;
      vote_average_gte?: number;
      with_original_language?: string;
      page?: number;
    } = {},
  ): Promise<any> => {
    const query = new URLSearchParams();
    if (params.with_genres !== undefined) {
      const g = Array.isArray(params.with_genres)
        ? params.with_genres.join('|')
        : String(params.with_genres).replace(/,/g, '|');
      query.set('with_genres', g);
    }
    if (params.sort_by)                       query.set('sort_by', params.sort_by);
    if (params.primary_release_year)          query.set('primary_release_year', String(params.primary_release_year));
    if (params.first_air_date_year)           query.set('first_air_date_year', String(params.first_air_date_year));
    if (params.vote_count_gte !== undefined)  query.set('vote_count.gte', String(params.vote_count_gte));
    if (params.vote_average_gte !== undefined) query.set('vote_average.gte', String(params.vote_average_gte));
    if (params.with_original_language)        query.set('with_original_language', params.with_original_language);
    query.set('page', String(params.page ?? 1));
    return api.get(`/api/tmdb/${mediaType}/discover?${query.toString()}`);
  },

  search: (query: string, mediaType: 'multi' | 'movie' | 'tv' = 'multi', page: number = 1): Promise<any> => {
    const cleanQuery = encodeURIComponent(query.trim());
    return api.get(`/api/tmdb/search/${mediaType}?query=${cleanQuery}&page=${page}`);
  },
  
  details: (mediaType: 'movie' | 'tv', id: number | string): Promise<any> => 
    api.get(`/api/tmdb/media/${mediaType}/${id}`),

  seasonEpisodes: (id: number | string, season: number): Promise<any> =>
    api.get(`/api/tmdb/tv/${id}/season/${season}`),

  recommendations: (mediaType: 'movie' | 'tv', id: number | string): Promise<any> =>
    api.get(`/api/tmdb/${mediaType}/${id}/recommendations`),

  similar: (mediaType: 'movie' | 'tv', id: number | string): Promise<any> =>
    api.get(`/api/tmdb/${mediaType}/${id}/similar`),

  genres: (mediaType: 'movie' | 'tv'): Promise<any> =>
    api.get(`/api/tmdb/genre/${mediaType}/list`),
};

/* Unified Structural Type Signatures */

export type Movie = {
  id: number;
  title: string;
  overview: string;
  poster_path: string | null;
  backdrop_path: string | null;
  release_date: string;
  vote_average: number;
  genre_ids: number[];
  media_type?: 'movie';
};

export type TVShow = {
  id: number;
  name: string;
  overview: string;
  poster_path: string | null;
  backdrop_path: string | null;
  first_air_date: string;
  vote_average: number;
  genre_ids: number[];
  media_type?: 'tv';
};

// General helper interface to simplify handling mixed lists
export type MediaItem = (Movie & { name?: string; first_air_date?: string }) | (TVShow & { title?: string; release_date?: string });