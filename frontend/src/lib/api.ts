// src/lib/api.ts

// Dynamically fallback to standard server-side paths if the wrapper variable is unset
const API_BASE = import.meta.env.BACKEND_URL || 'http://localhost:8000';

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
  getStreamSource: (tmdbId: number, mediaType: 'movie' | 'tv', season?: number, episode?: number): string => {
    let url = `/vidking/source?tmdbId=${tmdbId}&mediaType=${mediaType}`;
    if (mediaType === 'tv' && season !== undefined && episode !== undefined) {
      url += `&season=${season}&episode=${episode}`;
    }
    return `${API_BASE}${url}`;
  },
};

/**
 * Organized TMDB Endpoint Gateway
 */
export const tmdbApi = {
  trending: (mediaType: 'movie' | 'tv', timeWindow: 'day' | 'week' = 'day'): Promise<any> => 
    api.get(`/api/tmdb/trending/${mediaType}/${timeWindow}`),
  
  popular: (mediaType: 'movie' | 'tv'): Promise<any> => 
    api.get(`/api/tmdb/${mediaType}/popular`),
  
  /**
   * Dynamically formats search endpoints based on media type mapping
   */
  search: (query: string, mediaType: 'multi' | 'movie' | 'tv' = 'multi'): Promise<any> => {
    const cleanQuery = encodeURIComponent(query.trim());
    // Directs routing traffic precisely to match standard API formats
    return api.get(`/api/tmdb/search/${mediaType}?query=${cleanQuery}`);
  },
  
  details: (mediaType: 'movie' | 'tv', id: number | string): Promise<any> => 
    api.get(`/api/tmdb/${mediaType}/${id}`),
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