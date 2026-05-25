import { useState, useEffect } from "react";
import MovieCard from "./MovieCard";
import api from "@/utils/api";

export default function TopRated() {
  const [topRated, setTopRated] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchTopRated = async () => {
      setLoading(true);
      setError(null);
      
      try {
        const data = await fetch("/api/tmdb/movie/top_rated").then(res => res.json());
        setTopRated(data.results?.slice(0, 10) || []);
      } catch (err: any) {
        setError(err.message || "Failed to load top rated content");
        console.error("Error fetching top rated:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchTopRated();
  }, []);

  if (loading) {
    return (
      <div className="mb-12">
        <div className="flex items-center justify-between mb-6">
          <div className="h-9 w-48 bg-zinc-800 rounded animate-pulse" />
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-6">
          {Array.from({ length: 10 }).map((_, i) => (
            <div key={i} className="aspect-[2/3] bg-zinc-800 rounded-xl animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="mb-12 text-center py-10">
        <p className="text-red-500">{error}</p>
        <button 
          onClick={() => window.location.reload()}
          className="mt-4 px-6 py-2 bg-zinc-800 hover:bg-zinc-700 rounded-lg transition-colors"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="mb-16">
      <div className="flex items-end justify-between mb-6">
        <h2 className="text-3xl font-bold tracking-tight">Top Rated</h2>
        <span className="text-sm text-gray-500">All time best • Movies</span>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-6">
        {topRated.map((movie) => (
          <MovieCard 
            key={movie.id} 
            movie={movie} 
            type="movie" 
          />
        ))}
      </div>

      {topRated.length === 0 && (
        <div className="text-center py-12 text-gray-400">
          No top rated content available at the moment.
        </div>
      )}
    </div>
  );
}