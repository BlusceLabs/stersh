import { useState, useEffect, useCallback } from "react";
import { Search, X, TrendingUp, Film, Tv } from "lucide-react";
import MovieCard from "@/components/movie/MovieCard";

interface SearchFilters {
  query: string;
  type: "all" | "movie" | "tv";
}

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [filters, setFilters] = useState<SearchFilters>({ query: "", type: "all" });
  const [results, setResults] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [totalResults, setTotalResults] = useState(0);
  const [trendingMovies, setTrendingMovies] = useState<any[]>([]);
  const [trendingTV, setTrendingTV] = useState<any[]>([]);
  const [trendingLoading, setTrendingLoading] = useState(true);

  const debouncedSearch = useCallback(
    debounce(async (searchQuery: string, currentFilters: SearchFilters) => {
      if (!searchQuery.trim()) {
        setResults([]);
        setTotalResults(0);
        return;
      }

      setLoading(true);
      try {
        const endpoint = currentFilters.type === "tv" 
          ? `/api/tmdb/search/tv?query=${encodeURIComponent(searchQuery)}&include_adult=false&language=en-US&page=1`
          : currentFilters.type === "movie"
          ? `/api/tmdb/search/movie?query=${encodeURIComponent(searchQuery)}&include_adult=false&language=en-US&page=1`
          : `/api/tmdb/search/multi?query=${encodeURIComponent(searchQuery)}&include_adult=false&language=en-US&page=1`;
        const data = await fetch(endpoint).then(res => res.json());
        setResults(data.results || []);
        setTotalResults(data.total_results || 0);
      } catch (error) {
        console.error("Search error:", error);
        setResults([]);
      } finally {
        setLoading(false);
      }
    }, 500),
    []
  );

  useEffect(() => {
    debouncedSearch(query, filters);
  }, [query, filters, debouncedSearch]);

  useEffect(() => {
    const fetchTrending = async () => {
      setTrendingLoading(true);
      try {
        const [moviesData, tvData] = await Promise.all([
          fetch("/api/tmdb/trending/movie/week").then(res => res.json()),
          fetch("/api/tmdb/trending/tv/week").then(res => res.json())
        ]);
        setTrendingMovies(moviesData.results?.slice(0, 10) || []);
        setTrendingTV(tvData.results?.slice(0, 10) || []);
      } catch (error) {
        console.error("Error fetching trending:", error);
      } finally {
        setTrendingLoading(false);
      }
    };
    fetchTrending();
  }, []);

  const clearSearch = () => {
    setQuery("");
    setResults([]);
    setTotalResults(0);
  };

  return (
    <div className="min-h-screen bg-black text-white">
      <div className="max-w-7xl mx-auto px-6 py-10">
        <div className="text-center mb-12">
          <h1 className="text-6xl font-black mb-4 bg-gradient-to-r from-white to-gray-400 bg-clip-text text-transparent">
            Search & Discover
          </h1>
          <p className="text-gray-400 text-lg max-w-2xl mx-auto">
            Find your next favorite movie or TV show from thousands of titles
          </p>
        </div>

        <div className="relative max-w-3xl mx-auto mb-16">
          <div className="relative group">
            <Search className="absolute left-6 top-1/2 -translate-y-1/2 text-gray-500 group-focus-within:text-yellow-500 transition-colors" size={24} />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search for movies, TV shows, actors..."
              className="w-full bg-zinc-900/80 backdrop-blur-sm border-2 border-zinc-700 focus:border-yellow-500 rounded-full pl-16 pr-16 py-5 text-xl placeholder-gray-500 focus:outline-none transition-all shadow-2xl"
              autoFocus
            />
            {query && (
              <button
                onClick={clearSearch}
                className="absolute right-6 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white p-2 rounded-full hover:bg-zinc-800 transition-all"
              >
                <X size={20} />
              </button>
            )}
          </div>
          <div className="flex justify-center gap-4 mt-6">
            {["all", "movie", "tv"].map((type) => (
              <button
                key={type}
                onClick={() => setFilters(prev => ({ ...prev, type: type as any }))}
                className={`px-6 py-2 rounded-full text-sm font-medium transition-all ${
                  filters.type === type
                    ? "bg-yellow-500 text-black"
                    : "bg-zinc-800 text-gray-400 hover:bg-zinc-700"
                }`}
              >
                {type === "all" ? "All" : type === "movie" ? "Movies" : "TV Shows"}
              </button>
            ))}
          </div>
        </div>

        {loading ? (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-6">
            {Array.from({ length: 12 }).map((_, i) => (
              <div key={i} className="aspect-[2/3] bg-zinc-800 rounded-2xl animate-pulse" />
            ))}
          </div>
        ) : results.length > 0 ? (
          <div>
            <div className="flex items-center gap-3 mb-6">
              <h2 className="text-2xl font-bold">Search Results</h2>
              <span className="text-gray-400">{totalResults.toLocaleString()} found</span>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-6">
              {results.map((result) => (
                <MovieCard
                  key={result.id}
                  movie={result}
                  type={result.media_type || "movie"}
                />
              ))}
            </div>
          </div>
        ) : query ? (
          <div className="text-center py-20">
            <p className="text-2xl text-gray-400 mb-3">No results found</p>
            <p className="text-gray-500">Try a different search term</p>
          </div>
        ) : (
          <div className="space-y-12">
            <section>
              <div className="flex items-center gap-3 mb-6">
                <Film className="text-yellow-500" size={28} />
                <h2 className="text-3xl font-bold">Trending Movies</h2>
                <TrendingUp className="text-yellow-500" size={20} />
              </div>
              {trendingLoading ? (
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
                  {Array.from({ length: 10 }).map((_, i) => (
                    <div key={i} className="aspect-[2/3] bg-zinc-800 rounded-xl animate-pulse" />
                  ))}
                </div>
              ) : (
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
                  {trendingMovies.map((movie) => (
                    <MovieCard key={movie.id} movie={movie} type="movie" />
                  ))}
                </div>
              )}
            </section>

            <section>
              <div className="flex items-center gap-3 mb-6">
                <Tv className="text-yellow-500" size={28} />
                <h2 className="text-3xl font-bold">Trending TV Shows</h2>
                <TrendingUp className="text-yellow-500" size={20} />
              </div>
              {trendingLoading ? (
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
                  {Array.from({ length: 10 }).map((_, i) => (
                    <div key={i} className="aspect-[2/3] bg-zinc-800 rounded-xl animate-pulse" />
                  ))}
                </div>
              ) : (
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
                  {trendingTV.map((show) => (
                    <MovieCard key={show.id} movie={show} type="tv" />
                  ))}
                </div>
              )}
            </section>
          </div>
        )}
      </div>
    </div>
  );
}

function debounce<T extends (...args: any[]) => void>(func: T, delay: number) {
  let timeoutId: NodeJS.Timeout;
  return (...args: Parameters<T>) => {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => func(...args), delay);
  };
}