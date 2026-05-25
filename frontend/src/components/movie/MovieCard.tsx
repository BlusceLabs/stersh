import { Link } from "@tanstack/react-router";
import { Play } from "lucide-react";

interface MovieCardProps {
  movie: {
    id: number;
    title?: string;
    name?: string;
    poster_path?: string | null;
    backdrop_path?: string | null;
    overview?: string;
    release_date?: string;
    first_air_date?: string;
    vote_average?: number;
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

  const rating = movie.vote_average ? movie.vote_average.toFixed(1) : null;

  const mediaType = movie.media_type || type;
  const detailPath = mediaType === "tv" ? `/tv/${movie.id}` : `/movie/${movie.id}`;

  return (
    <Link to={detailPath} className="group block">
      <div className="relative overflow-hidden rounded-xl aspect-[2/3] bg-zinc-900 shadow-lg transition-all duration-300 group-hover:scale-[1.04] group-hover:shadow-2xl">
        {/* Poster */}
        <img
          src={posterUrl}
          alt={title}
          className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110"
          loading="lazy"
        />

        {/* Hover Overlay */}
        <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/50 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />

        {/* Bottom Info */}
        <div className="absolute bottom-0 left-0 right-0 p-4 opacity-0 group-hover:opacity-100 transition-all duration-300 translate-y-2 group-hover:translate-y-0">
          <h3 className="font-semibold text-lg leading-tight line-clamp-2 mb-1">
            {title}
          </h3>
          
          <div className="flex items-center justify-between text-sm">
            {rating && (
              <span className="flex items-center gap-1 text-yellow-400">
                ★ {rating}
              </span>
            )}
            {year && <span className="text-gray-400 text-xs">{year}</span>}
          </div>
        </div>

        {/* Play Button on Hover */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-14 h-14 bg-red-600 rounded-full flex items-center justify-center opacity-0 scale-75 group-hover:opacity-100 group-hover:scale-100 transition-all duration-300 shadow-xl">
          <Play size={26} className="text-white ml-0.5" fill="white" />
        </div>

        {/* Media Type Badge */}
        <div className="absolute top-3 right-3 bg-black/70 text-[10px] uppercase tracking-widest px-2.5 py-1 rounded font-mono text-gray-400">
          {mediaType}
        </div>
      </div>
    </Link>
  );
}