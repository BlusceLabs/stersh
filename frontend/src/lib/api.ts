const API_BASE = import.meta.env.BACKEND_URL || 'http://localhost:8000';

export const api = {
  get: async (path: string, token?: string) => {
    const headers: Record<string, string> = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const res = await fetch(`${API_BASE}${path}`, { headers });
    if (!res.ok) throw new Error(`API error: ${res.statusText}`);
    return res.json();
  },

  getMovie: (id: number, token?: string) => api.get(`/tmdb/movie/${id}`, token),
  getTVShow: (id: number, token?: string) => api.get(`/tmdb/tv/${id}`, token),
  search: (query: string) => api.get(`/tmdb/search/multi?query=${encodeURIComponent(query)}`),
  
  getStream: (mediaType: string, id: number, season?: number, episode?: number, token?: string) => {
    let url = `/watch/${mediaType}/${id}`;
    if (season && episode) {
      url += `?season=${season}&episode=${episode}`;
    }
    return api.get(url, token);
  },
};