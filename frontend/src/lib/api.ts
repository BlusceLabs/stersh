const API_BASE = import.meta.env.BACKEND_URL || '/api';

export const api = {
  get: async (path: string, token?: string) => {
    const headers: Record<string, string> = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const res = await fetch(`${API_BASE}${path}`, { headers });
    if (!res.ok) throw new Error(`API error: ${res.statusText}`);
    return res.json();
  },
  
  getStreamSource: (tmdbId: number, mediaType: string, season?: number, episode?: number) => {
    let url = `/vidking/source?tmdbId=${tmdbId}&mediaType=${mediaType}`;
    if (season && episode) {
      url += `&season=${season}&episode=${episode}`;
    }
    return `${API_BASE}${url}`;
  },
};

export const tmdbApi = {
  trending: (mediaType: 'movie' | 'tv', timeWindow: 'day' | 'week' = 'day') => 
    api.get(`/tmdb/trending/${mediaType}/${timeWindow}`),
  
  popular: (mediaType: 'movie' | 'tv') => 
    api.get(`/tmdb/${mediaType}/popular`),
  
  search: (query: string, mediaType: string = 'multi') => 
    api.get(`/tmdb/search?query=${encodeURIComponent(query)}${mediaType ? `&media_type=${mediaType}` : ''}`),
  
  details: (mediaType: 'movie' | 'tv', id: number) => 
    api.get(`/tmdb/${mediaType}/${id}`),
};

export type Movie = {
  id: number;
  title: string;
  overview: string;
  poster_path: string | null;
  backdrop_path: string | null;
  release_date: string;
  vote_average: number;
  genre_ids: number[];
  media_type?: string;
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
  media_type?: string;
};