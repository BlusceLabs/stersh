const API_URL =
  process.env.VITE_API_URL || "http://localhost:8080/api"

interface CacheEntry {
  data: unknown
  expiry: number
}

const cache = new Map<string, CacheEntry>()
const inflight = new Map<string, Promise<unknown>>()

const CACHE_TTL = 60_000

function getCached(key: string): unknown | undefined {
  const entry = cache.get(key)
  if (!entry) return
  if (Date.now() > entry.expiry) {
    cache.delete(key)
    return
  }
  return entry.data
}

function setCache(key: string, data: unknown) {
  cache.set(key, { data, expiry: Date.now() + CACHE_TTL })
}

async function request<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const cacheKey = `GET ${path}`

  if (!options?.method || options.method === "GET") {
    const cached = getCached(cacheKey)
    if (cached) return cached as T

    const pending = inflight.get(cacheKey)
    if (pending) return pending as Promise<T>

    const promise = (async () => {
      try {
        const response = await fetch(`${API_URL}${path}`, {
          ...options,
          headers: {
            "Content-Type": "application/json",
            ...(options?.headers || {}),
          },
        })

        if (!response.ok) {
          throw new Error(`API Error ${response.status}`)
        }

        const data = await response.json()
        setCache(cacheKey, data)
        return data
      } finally {
        inflight.delete(cacheKey)
      }
    })()

    inflight.set(cacheKey, promise)
    return promise as Promise<T>
  }

  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers || {}),
    },
  })

  if (!response.ok) {
    throw new Error(`API Error ${response.status}`)
  }

  return response.json()
}

export const api = {
  get: <T>(path: string) =>
    request<T>(path),

  post: <T>(
    path: string,
    body?: unknown
  ) =>
    request<T>(path, {
      method: "POST",
      body: JSON.stringify(body),
    }),
}
