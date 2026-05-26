const API_BASE = 'http://localhost:8000';

export const api = {
  get: async (path: string) => {
    const res = await fetch(`${API_BASE}${path}`);
    if (!res.ok) throw new Error(`API error: ${res.statusText}`);
    return res.json();
  },

  getMovie: (id: number) => api.get(`/tmdb/movie/${id}`),
  getTVShow: (id: number) => api.get(`/tmdb/tv/${id}`),
  search: (query: string) => api.get(`/tmdb/search/multi?query=${encodeURIComponent(query)}`),
  
  getStream: (mediaType: string, id: number, season?: number, episode?: number) => {
    let url = `/watch/${mediaType}/${id}`;
    if (season && episode) {
      url += `?season=${season}&episode=${episode}`;
    }
    return api.get(url);
  },
};