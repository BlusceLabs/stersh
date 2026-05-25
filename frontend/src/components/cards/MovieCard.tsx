import { Link } from "@tanstack/react-router";
import { Play } from "lucide-react";

interface MovieCardProps {
  movie: {
    id: number;
    title?: string;
    name?: string;
    poster_path?: string | null;
    backdrop_path?: string | null;
    vote_average?: number;
    release_date?: string;
    first_air_date?: string;
    media_type?: "movie" | "tv";
  };
  type?: "movie" | "tv";
}

export default function MovieCard({ movie, type = "movie" }: MovieCardProps) {
  const title = movie.title || movie.name || "Untitled";
  const year = movie.release_date || movie.first_air_date 
    ? new Date(movie.release_date || movie.first_air_date!).getFullYear() 
    : null;
  
  const posterUrl = movie.poster_path 
    ? `https://image.tmdb.org/t/p/w500${movie.poster_path}` 
    : "/placeholder-poster.jpg";

  const rating = movie.vote_average ? Math.round(movie.vote_average * 10) / 10 : null;

  const mediaType = movie.media_type || type;
  const detailPath = mediaType === "tv" ? `/tv/${movie.id}` : `/movie/${movie.id}`;

  return (
    <Link to={detailPath} className="group block">
      <div className="relative overflow-hidden rounded-xl aspect-[2/3] bg-zinc-900 shadow-lg transition-all duration-300 group-hover:scale-105 group-hover:shadow-2xl">
        {/* Poster Image */}
        <img
          src={posterUrl}
          alt={title}
          className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110"
          loading="lazy"
        />

        {/* Overlay Gradient */}
        <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/40 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />

        {/* Content Overlay */}
        <div className="absolute inset-0 flex flex-col justify-end p-4 opacity-0 group-hover:opacity-100 transition-all duration-300">
          <div className="flex items-center justify-between">
            {rating && (
              <div className="bg-black/70 text-yellow-400 text-xs font-bold px-2 py-1 rounded flex items-center gap-1">
                ★ {rating}
              </div>
            )}
            
            <div className="bg-black/70 text-[10px] px-2 py-1 rounded text-gray-300">
              {year || "N/A"}
            </div>
          </div>

          <h3 className="font-semibold text-lg leading-tight mt-3 line-clamp-2">
            {title}
          </h3>
        </div>

        {/* Play Button Hover */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-12 h-12 bg-red-600 rounded-full flex items-center justify-center opacity-0 scale-75 group-hover:opacity-100 group-hover:scale-100 transition-all duration-300 shadow-lg">
          <Play size={22} className="text-white ml-0.5" fill="white" />
        </div>

        {/* Type Badge */}
        {mediaType && (
          <div className="absolute top-3 right-3 bg-black/70 text-[10px] uppercase tracking-widest px-2 py-1 rounded font-mono text-gray-400">
            {mediaType}
          </div>
        )}
      </div>
    </Link>
  );
}