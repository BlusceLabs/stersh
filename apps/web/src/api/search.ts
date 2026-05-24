import { api } from "./client"

export interface SearchResult {
  id: number;
  title: string;
  posterPath: string;
  mediaType: string;
}

export async function searchContent(query: string) {
  return api.get<{ results: SearchResult[] }>(
    `/search?q=${encodeURIComponent(query)}`
  )
}
