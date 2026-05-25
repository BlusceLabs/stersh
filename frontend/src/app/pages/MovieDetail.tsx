import { useState, useEffect } from "react";
import { useParams, useNavigate } from "@tanstack/react-router";
import { Play, Plus, ThumbsUp, Share2 } from "lucide-react";
import api from "@/utils/api";
import VideoPlayer from "@/components/player/VideoPlayer";

interface Movie {
  id: number;
  title: string;
  overview: string;
  backdrop_path: string;
  poster_path: string;
  release_date: string;
  runtime: number;
  vote_average: number;
  genres: Array<{ id: number; name: string }>;
  tagline?: string;
}

export default function MovieDetail() {
  const { id } = useParams({ from: "/movie/$id" });
  const navigate = useNavigate();

  const [movie, setMovie] = useState<Movie | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchMovie = async () => {
      if (!id) return;
      
      setLoading(true);
      setError(null);
      
      try {
        const data = await api.getMovie(Number(id));
        setMovie(data);
      } catch (err: any) {
        setError(err.message || "Failed to load movie details");
      } finally {
        setLoading(false);
      }
    };

    fetchMovie();
  }, [id]);

  const handleWatchNow = () => {
    navigate({ to: `/watch/movie/${id}` });
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <div className="flex flex-col items-center">
          <div className="w-12 h-12 border-4 border-zinc-700 border-t-yellow-500 rounded-full animate-spin mb-4"></div>
          <p className="text-gray-400">Loading movie details...</p>
        </div>
      </div>
    );
  }

  if (error || !movie) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center text-center px-6">
        <div>
          <h2 className="text-2xl font-bold mb-3">Something went wrong</h2>
          <p className="text-gray-400 mb-6">{error || "Movie not found"}</p>
          <button 
            onClick={() => window.history.back()}
            className="px-6 py-2 bg-zinc-800 hover:bg-zinc-700 rounded-lg transition-colors"
          >
            Go Back
          </button>
        </div>
      </div>
    );
  }

  const backdropUrl = movie.backdrop_path 
    ? `https://image.tmdb.org/t/p/original${movie.backdrop_path}` 
    : "/placeholder-backdrop.jpg";

  return (
    <div className="min-h-screen bg-black text-white">
      {/* Hero Background */}
      <div className="relative h-[85vh] overflow-hidden">
        <img
          src={backdropUrl}
          alt={movie.title}
          className="absolute inset-0 w-full h-full object-cover"
        />
        <div className="absolute inset-0 bg-gradient-to-r from-black via-black/80 to-transparent" />
        <div className="absolute inset-0 bg-gradient-to-t from-black via-black/50 to-transparent" />

        {/* Content */}
        <div className="relative z-10 h-full flex items-center px-8 md:px-16 max-w-7xl mx-auto">
          <div className="max-w-2xl">
            <h1 className="text-5xl md:text-6xl font-bold mb-4 tracking-tight">
              {movie.title}
            </h1>
            
            {movie.tagline && (
              <p className="text-xl text-yellow-500 italic mb-6">{movie.tagline}</p>
            )}

            <div className="flex items-center gap-5 text-sm mb-6">
              <span className="bg-yellow-500 text-black font-semibold px-3 py-0.5 rounded">
                {movie.vote_average.toFixed(1)}
              </span>
              <span>{new Date(movie.release_date).getFullYear()}</span>
              <span>{movie.runtime} min</span>
            </div>

            <p className="text-lg text-gray-300 leading-relaxed mb-8 line-clamp-3">
              {movie.overview}
            </p>

            <div className="flex items-center gap-4">
              <button
                onClick={handleWatchNow}
                className="flex items-center gap-3 bg-white text-black hover:bg-white/90 transition-colors px-8 py-3.5 rounded font-semibold text-lg"
              >
                <Play className="fill-current" size={26} />
                Play Now
              </button>

              <button className="p-4 bg-white/20 hover:bg-white/30 backdrop-blur rounded-full transition-all">
                <Plus size={26} />
              </button>
              <button className="p-4 bg-white/20 hover:bg-white/30 backdrop-blur rounded-full transition-all">
                <ThumbsUp size={26} />
              </button>
              <button className="p-4 bg-white/20 hover:bg-white/30 backdrop-blur rounded-full transition-all">
                <Share2 size={26} />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Details Section */}
      <div className="max-w-7xl mx-auto px-8 md:px-16 py-12">
        <div className="grid md:grid-cols-3 gap-10">
          <div className="md:col-span-2">
            <h2 className="text-2xl font-semibold mb-6">Overview</h2>
            <p className="text-gray-300 leading-relaxed text-lg">
              {movie.overview}
            </p>
          </div>

          <div>
            <h3 className="text-lg font-medium mb-4 text-gray-400">Details</h3>
            <div className="space-y-6">
              <div>
                <span className="text-sm text-gray-500">Genres</span>
                <p className="mt-1">
                  {movie.genres.map(g => g.name).join(", ")}
                </p>
              </div>
              <div>
                <span className="text-sm text-gray-500">Release Date</span>
                <p>{new Date(movie.release_date).toLocaleDateString('en-US', { 
                  year: 'numeric', 
                  month: 'long', 
                  day: 'numeric' 
                })}</p>
              </div>
              <div>
                <span className="text-sm text-gray-500">Rating</span>
                <p>{movie.vote_average}/10 • TMDB</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}