const API_BASE = "/api";

const api = {
  get: async (path: string) => {
    const res = await fetch(`${API_BASE}${path}`);
    if (!res.ok) throw new Error("API error");
    return res.json();
  },
  post: async (path: string, data: unknown) => {
    const res = await fetch(`${API_BASE}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error("API error");
    return res.json();
  },
  login: async (email: string, password: string) => {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) throw new Error("Login failed");
    return res.json();
  },
  register: async (email: string, username: string, password: string) => {
    const res = await fetch(`${API_BASE}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, username, password }),
    });
    if (!res.ok) throw new Error("Registration failed");
    return res.json();
  },
  logout: async () => {
    await fetch(`${API_BASE}/auth/logout`, { method: "POST" });
  },
  refreshToken: async (token: string) => {
    const res = await fetch(`${API_BASE}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token }),
    });
    if (!res.ok) throw new Error("Refresh failed");
    return res.json();
  },
  getProfile: async (token: string) => {
    const res = await fetch(`${API_BASE}/user/profile`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) throw new Error("Profile fetch failed");
    return res.json();
  },
  getMovie: async (id: number) => {
    return api.get(`/tmdb/movie/${id}?append_to_response=images`);
  },
  getTVShow: async (id: number) => {
    return api.get(`/tmdb/tv/${id}?append_to_response=images`);
  },
  search: async (filters: { query: string; type?: string; year?: number; genre?: string; minRating?: number }) => {
    const params = new URLSearchParams();
    if (filters.query) params.append("query", filters.query);
    if (filters.type && filters.type !== "all") params.append("type", filters.type);
    if (filters.year) params.append("year", String(filters.year));
    if (filters.genre) params.append("genre", filters.genre);
    if (filters.minRating) params.append("minRating", String(filters.minRating));
    return api.get(`/tmdb/search?${params.toString()}`);
  },
};

export default api;