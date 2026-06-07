// src/lib/api.ts

const API_BASE = import.meta.env.BACKEND_URL || '';

/** Typed error from the API layer. */
export class ApiError extends Error {
  status: number;
  detail: string;
  constructor(status: number, detail: string) {
    super(detail);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

/**
 * Centralized API client with:
 *  - AbortController support (cancel in-flight requests)
 *  - Consistent error handling (ApiError with status + detail)
 *  - Auth token injection
 *  - Request timeout (10 s default)
 */
class ApiClient {
  private token: string | null = null;
  private pending: Map<string, AbortController> = new Map();

  setToken(token: string | null) {
    this.token = token;
  }

  /** Abort any in-flight request with the given key, then start a new one. */
  private cancelPending(key: string) {
    const ctrl = this.pending.get(key);
    if (ctrl) ctrl.abort();
  }

  async get<T>(path: string, opts?: { key?: string; timeout?: number }): Promise<T> {
    const key = opts?.key ?? path;
    this.cancelPending(key);

    const ctrl = new AbortController();
    this.pending.set(key, ctrl);

    const headers: Record<string, string> = {
      Accept: 'application/json',
      'Content-Type': 'application/json',
    };
    if (this.token) headers['Authorization'] = `Bearer ${this.token}`;

    const timeout = opts?.timeout ?? 10_000;
    const timer = setTimeout(() => ctrl.abort(), timeout);

    try {
      const response = await fetch(`${API_BASE}${path}`, {
        headers,
        signal: ctrl.signal,
      });
      clearTimeout(timer);

      if (!response.ok) {
        let detail = response.statusText;
        try {
          const body = await response.json();
          detail = body.detail ?? body.message ?? detail;
        } catch { /* not JSON */ }
        throw new ApiError(response.status, detail);
      }
      return response.json();
    } catch (err: unknown) {
      clearTimeout(timer);
      if (err instanceof ApiError) throw err;
      if (err instanceof DOMException && err.name === 'AbortError') {
        throw new ApiError(0, 'Request cancelled');
      }
      throw new ApiError(0, err instanceof Error ? err.message : 'Network error');
    } finally {
      this.pending.delete(key);
    }
  }

  async post<T>(path: string, body: unknown): Promise<T> {
    const headers: Record<string, string> = {
      Accept: 'application/json',
      'Content-Type': 'application/json',
    };
    if (this.token) headers['Authorization'] = `Bearer ${this.token}`;

    const response = await fetch(`${API_BASE}${path}`, {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      let detail = response.statusText;
      try {
        const j = await response.json();
        detail = j.detail ?? j.message ?? detail;
      } catch { /* not JSON */ }
      throw new ApiError(response.status, detail);
    }
    return response.json();
  }

  /** Cancel all in-flight requests (e.g. on navigation). */
  abortAll() {
    for (const ctrl of this.pending.values()) ctrl.abort();
    this.pending.clear();
  }
}

/** Singleton API client. */
export const apiClient = new ApiClient();

// ── Convenience wrappers (backward-compatible with old `api` export) ──────────

export const api = {
  get: <T>(path: string, token?: string) => {
    if (token) apiClient.setToken(token);
    return apiClient.get<T>(path);
  },

  getStreamSource: (
    tmdbId: number,
    mediaType: 'movie' | 'tv',
    season?: number,
    episode?: number,
    server: string = 'white',
  ): string => {
    const allowed = new Set(['white', 'black']);
    const safeServer = allowed.has(server) ? server : 'white';
    const safeMedia: 'movie' | 'tv' = mediaType === 'tv' ? 'tv' : 'movie';
    const safeTmdb = Number.isFinite(tmdbId) && tmdbId > 0 ? Math.floor(tmdbId) : 0;
    let url = `/api/${safeServer}/source?tmdbId=${safeTmdb}&mediaType=${safeMedia}`;
    if (safeMedia === 'tv' && Number.isFinite(season) && Number.isFinite(episode)) {
      url += `&season=${Math.max(1, Math.floor(season as number))}&episode=${Math.max(1, Math.floor(episode as number))}`;
    }
    return url;
  },
};

// ── TMDB endpoint gateway ──────────────────────────────────────────────────────

export const tmdbApi = {
  trending: (mediaType: 'movie' | 'tv', timeWindow: 'day' | 'week' = 'day') =>
    apiClient.get(`/api/tmdb/trending/${mediaType}/${timeWindow}`),

  popular: (mediaType: 'movie' | 'tv', page = 1) =>
    apiClient.get(`/api/tmdb/${mediaType}/popular?page=${page}`),

  topRated: (mediaType: 'movie' | 'tv', page = 1) =>
    apiClient.get(`/api/tmdb/${mediaType}/top_rated?page=${page}`),

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
  ) => {
    const q = new URLSearchParams();
    if (params.with_genres !== undefined) {
      const g = Array.isArray(params.with_genres)
        ? params.with_genres.join('|')
        : String(params.with_genres).replace(/,/g, '|');
      q.set('with_genres', g);
    }
    if (params.sort_by) q.set('sort_by', params.sort_by);
    if (params.primary_release_year) q.set('primary_release_year', String(params.primary_release_year));
    if (params.first_air_date_year) q.set('first_air_date_year', String(params.first_air_date_year));
    if (params.vote_count_gte !== undefined) q.set('vote_count.gte', String(params.vote_count_gte));
    if (params.vote_average_gte !== undefined) q.set('vote_average.gte', String(params.vote_average_gte));
    if (params.with_original_language) q.set('with_original_language', params.with_original_language);
    q.set('page', String(params.page ?? 1));
    return apiClient.get(`/api/tmdb/${mediaType}/discover?${q.toString()}`);
  },

  search: (query: string, mediaType: 'multi' | 'movie' | 'tv' = 'multi', page = 1) =>
    apiClient.get(`/api/tmdb/search/${mediaType}?query=${encodeURIComponent(query.trim())}&page=${page}`),

  details: (mediaType: 'movie' | 'tv', id: number | string) =>
    apiClient.get(`/api/tmdb/media/${mediaType}/${id}`),

  seasonEpisodes: (id: number | string, season: number) =>
    apiClient.get(`/api/tmdb/tv/${id}/season/${season}`),

  recommendations: (mediaType: 'movie' | 'tv', id: number | string) =>
    apiClient.get(`/api/tmdb/${mediaType}/${id}/recommendations`),

  similar: (mediaType: 'movie' | 'tv', id: number | string) =>
    apiClient.get(`/api/tmdb/${mediaType}/${id}/similar`),

  genres: (mediaType: 'movie' | 'tv') =>
    apiClient.get(`/api/tmdb/genre/${mediaType}/list`),
};

// ── Type exports ───────────────────────────────────────────────────────────────

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

export type MediaItem = (Movie & { name?: string; first_air_date?: string }) | (TVShow & { title?: string; release_date?: string });
