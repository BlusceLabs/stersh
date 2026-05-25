// frontend/utils/api.ts
const API_BASE_URL = "/api";

interface ApiResponse<T = any> {
  data?: T;
  error?: string;
  message?: string;
}

const handleResponse = async <T>(response: Response): Promise<T> => {
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.message || errorData.error || `HTTP Error: ${response.status}`);
  }
  return response.json();
};

export const api = {
  // TMDB endpoints (proxied through backend)
  getMovie: async (id: number): Promise<any> => {
    const response = await fetch(`${API_BASE_URL}/tmdb/movie/${id}`);
    return handleResponse(response);
  },

  getTVShow: async (id: number): Promise<any> => {
    const response = await fetch(`${API_BASE_URL}/tmdb/tv/${id}`);
    return handleResponse(response);
  },

  search: async (query: string, page = 1): Promise<any> => {
    const params = new URLSearchParams({ query, page: page.toString() });
    const response = await fetch(`${API_BASE_URL}/tmdb/search?${params}`);
    return handleResponse(response);
  },

  // Auth endpoints
  login: async (email: string, password: string): Promise<any> => {
    const response = await fetch(`${API_BASE_URL}/auth/token`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username: email, password }),
    });
    return handleResponse(response);
  },

  register: async (email: string, username: string, password: string): Promise<any> => {
    const response = await fetch(`${API_BASE_URL}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, username, password }),
    });
    return handleResponse(response);
  },

  getProfile: async (token: string): Promise<any> => {
    const response = await fetch(`${API_BASE_URL}/auth/profile`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    return handleResponse(response);
  },

  // Token refresh
  refreshToken: async (refreshToken: string): Promise<any> => {
    const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refreshToken }),
    });
    return handleResponse(response);
  },

  // Logout
  logout: async (token: string): Promise<any> => {
    const response = await fetch(`${API_BASE_URL}/auth/logout`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
    });
    return handleResponse(response);
  },
};

export default api;