import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Mock fetch globally
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('apiClient', () => {
  beforeEach(() => {
    mockFetch.mockReset();
  });

  it('makes a GET request with correct URL', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ id: 1, title: 'Test' }),
    });
    const { apiClient } = await import('$lib/api');
    const result = await apiClient.get('/api/tmdb/movie/1');
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/tmdb/movie/1'),
      expect.objectContaining({ headers: expect.any(Object) })
    );
    expect(result).toEqual({ id: 1, title: 'Test' });
  });

  it('sets Authorization header when token is provided', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ results: [] }),
    });
    const { apiClient } = await import('$lib/api');
    apiClient.setToken('my-test-token');
    await apiClient.get('/api/tmdb/trending/movie/day');
    expect(mockFetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: 'Bearer my-test-token',
        }),
      })
    );
  });

  it('throws ApiError on non-OK response', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 404,
      statusText: 'Not Found',
      json: async () => ({ detail: 'Movie not found' }),
    });
    const { apiClient, ApiError } = await import('$lib/api');
    await expect(apiClient.get('/api/tmdb/movie/0')).rejects.toThrow(ApiError);
    try {
      await apiClient.get('/api/tmdb/movie/0');
    } catch (err) {
      expect(err).toBeInstanceOf(Error);
      expect((err as Error).message).toBe('Movie not found');
    }
  });

  it('throws ApiError with statusText when response body is not JSON', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      statusText: 'Internal Server Error',
      json: async () => { throw new Error('not json'); },
    });
    const { apiClient } = await import('$lib/api');
    await expect(apiClient.get('/api/health')).rejects.toThrow('Internal Server Error');
  });

  it('aborts in-flight request when same key is used', async () => {
    let resolveFirst: (value: any) => void;
    mockFetch.mockImplementationOnce(
      () => new Promise((resolve) => { resolveFirst = resolve; })
    );
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ id: 2 }),
    });

    const { apiClient } = await import('$lib/api');
    const first = apiClient.get('/api/tmdb/movie/1', { key: 'test-key' });
    const second = apiClient.get('/api/tmdb/movie/2', { key: 'test-key' });

    // Resolve the first request (it was aborted but the promise resolves)
    resolveFirst!({ ok: false, status: 0, statusText: 'Aborted', json: async () => ({}) });

    const result = await second;
    expect(result).toEqual({ id: 2 });
  });

  it('POST sends JSON body', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ message: 'saved' }),
    });
    const { apiClient } = await import('$lib/api');
    const result = await apiClient.post('/api/continue-watching', { tmdb_id: 123 });
    expect(mockFetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ tmdb_id: 123 }),
      })
    );
    expect(result).toEqual({ message: 'saved' });
  });
});

describe('api.getStreamSource', () => {
  it('builds correct URL for movie', async () => {
    const { api } = await import('$lib/api');
    const url = api.getStreamSource(123, 'movie', undefined, undefined, 'white');
    expect(url).toBe('/api/white/source?tmdbId=123&mediaType=movie');
  });

  it('builds correct URL for TV with season/episode', async () => {
    const { api } = await import('$lib/api');
    const url = api.getStreamSource(456, 'tv', 2, 5, 'black');
    expect(url).toBe('/api/black/source?tmdbId=456&mediaType=tv&season=2&episode=5');
  });

  it('falls back to white server for invalid server', async () => {
    const { api } = await import('$lib/api');
    const url = api.getStreamSource(123, 'movie', undefined, undefined, 'purple');
    expect(url).toContain('/api/white/');
  });

  it('sanitizes negative tmdbId', async () => {
    const { api } = await import('$lib/api');
    const url = api.getStreamSource(-1, 'movie');
    expect(url).toContain('tmdbId=0');
  });
});
