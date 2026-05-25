import { useState, useEffect } from "react";
import MovieCard from "@/components/movie/MovieCard";
import api from "@/utils/api";

interface Movie {
  id: number;
  title?: string;
  name?: string;
  poster_path: string | null;
  backdrop_path: string | null;
  overview: string;
  release_date?: string;
  first_air_date?: string;
  vote_average: number;
  genre_ids: number[];
  media_type?: "movie" | "tv";
}

interface MovieListProps {
  type?: "movie" | "tv";
}

export default function MovieList({ type = "movie" }: MovieListProps) {
  const [movies, setMovies] = useState<Movie[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const title = type === "movie" ? "Popular Movies" : "Popular TV Shows";

  useEffect(() => {
    const fetchMovies = async () => {
      setLoading(true);
      setError(null);
      
      try {
        const data = await fetch(`/api/tmdb/${type}/popular`).then(res => res.json());
        setMovies(data.results || []);
      } catch (err: any) {
        setError(err.message || "Failed to load content");
        console.error("Error fetching content:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchMovies();
  }, [type]);

  if (loading) {
    return (
      <div className="p-6">
        <div className="h-9 w-64 bg-zinc-800 rounded mb-8 animate-pulse" />
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
          {Array.from({ length: 12 }).map((_, i) => (
            <div key={i} className="aspect-[2/3] bg-zinc-800 rounded-xl animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 text-center py-20">
        <p className="text-red-500 mb-4">{error}</p>
        <button 
          onClick={() => window.location.reload()}
          className="px-6 py-2 bg-zinc-800 hover:bg-zinc-700 rounded-lg transition-colors"
        >
          Try Again
        </button>
      </div>
    );
  }

  return (
    <div className="px-6 py-8">
      <div className="flex items-end justify-between mb-6">
        <h1 className="text-3xl font-bold tracking-tight">{title}</h1>
        <span className="text-sm text-gray-500">Trending right now</span>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 2xl:grid-cols-7 gap-4 md:gap-6">
        {movies.map((movie) => (
          <MovieCard 
            key={movie.id} 
            movie={movie} 
            type={type} 
          />
        ))}
      </div>

      {movies.length === 0 && (
        <div className="text-center py-16 text-gray-400">
          No content available at the moment.
        </div>
      )}
    </div>
  );
}