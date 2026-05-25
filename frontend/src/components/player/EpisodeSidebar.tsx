import { ChevronDown, ChevronUp, Film, Tv2, Calendar, Star, Clock } from "lucide-react";
import { useState } from "react";

interface Episode {
  episode_number: number;
  name: string;
  overview: string;
  still_path: string | null;
  air_date: string;
  vote_average: number;
  runtime: number;
}

interface EpisodeSidebarProps {
  seasons: { season_number: number; name: string; episode_count: number }[];
  episodes: Episode[];
  currentSeason: number;
  currentEpisode: number;
  onSelectEpisode: (season: number, episode: number) => void;
  onClose?: () => void;
}

export function EpisodeSidebar({
  seasons,
  episodes,
  currentSeason,
  currentEpisode,
  onSelectEpisode,
  onClose,
}: EpisodeSidebarProps) {
  const [selectedSeason, setSelectedSeason] = useState(currentSeason);
  const [isSeasonOpen, setIsSeasonOpen] = useState(false);

  const formatDate = (date: string) => {
    if (!date) return "N/A";
    return new Date(date).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  };

  return (
    <div className="flex flex-col h-full bg-surface-raised">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-border bg-surface/50">
        <h2 className="text-lg font-semibold text-text">Episodes</h2>
        {onClose && (
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-surface-sunken transition-all duration-200 hover:rotate-180"
            aria-label="Close sidebar"
          >
            <ChevronDown className="w-5 h-5 text-text-muted" />
          </button>
        )}
      </div>

      {/* Season Selector */}
      <div className="p-3 border-b border-border">
        <button
          onClick={() => setIsSeasonOpen(!isSeasonOpen)}
          className="flex items-center justify-between w-full px-3 py-2.5 rounded-lg bg-surface hover:bg-surface-sunken transition-all duration-200 shadow-subtle"
        >
          <div className="flex items-center gap-2">
            <Tv2 className="w-4 h-4 text-yellow-500" />
            <span className="font-medium text-text">
              Season {selectedSeason}
            </span>
          </div>
          <div className={`transition-transform duration-200 ${isSeasonOpen ? "rotate-180" : ""}`}>
            <ChevronDown className="w-4 h-4 text-text-muted" />
          </div>
        </button>

        <div
          className={`mt-2 max-h-60 overflow-y-auto rounded-lg border border-border bg-surface transition-all duration-300 ${
            isSeasonOpen ? "max-h-60 opacity-100" : "max-h-0 opacity-0 pointer-events-none"
          }`}
        >
          {seasons.map((season) => (
            <button
              key={season.season_number}
              onClick={() => {
                setSelectedSeason(season.season_number);
                setIsSeasonOpen(false);
              }}
              className={`flex items-center justify-between w-full px-3 py-2.5 text-left transition-all duration-200 first:rounded-t-lg last:rounded-b-lg ${
                season.season_number === selectedSeason
                  ? "bg-gradient-to-r from-yellow-500/20 to-yellow-500/5 text-yellow-500"
                  : "text-text hover:bg-surface-sunken"
              }`}
            >
              <span className="font-medium">
                Season {season.season_number}
              </span>
              <span className="text-sm text-text-muted">
                {season.episode_count} Episodes
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Episode List */}
      <div className="flex-1 overflow-y-auto">
        {episodes.map((episode, index) => {
          const isActive = episode.episode_number === currentEpisode;
          return (
            <button
              key={episode.episode_number}
              onClick={() => onSelectEpisode(selectedSeason, episode.episode_number)}
              className={`w-full p-3 text-left border-b border-border/50 transition-all duration-200 ${
                isActive
                  ? "bg-gradient-to-r from-yellow-500/30 to-transparent border-l-4 border-l-yellow-500"
                  : "hover:bg-surface-sunken"
              }`}
              style={{
                animationDelay: `${index * 30}ms`,
              }}
            >
              <div className="flex gap-3">
                {/* Episode Image */}
                <div className="relative flex-shrink-0">
                  {episode.still_path ? (
                    <img
                      src={`https://image.tmdb.org/t/p/w200${episode.still_path}`}
                      alt={episode.name}
                      className="w-28 h-16 object-cover rounded-md shadow-card"
                      onError={(e) => {
                        e.currentTarget.src =
                          "https://via.placeholder.com/200x112?text=No+Image";
                      }}
                    />
                  ) : (
                    <div className="w-28 h-16 rounded-md bg-surface-sunken flex items-center justify-center shadow-card">
                      <Film className="w-6 h-6 text-text-muted" />
                    </div>
                  )}
                  <div className="absolute bottom-1 right-1 bg-black/70 text-white text-xs px-1.5 py-0.5 rounded">
                    {episode.episode_number}
                  </div>
                </div>

                {/* Episode Info */}
                <div className="flex-1 min-w-0">
                  <h3
                    className={`font-medium text-sm line-clamp-1 ${
                      isActive ? "text-yellow-500" : "text-text"
                    }`}
                  >
                    {episode.name}
                  </h3>

                  <p className="text-text-muted text-xs mt-1 line-clamp-2">
                    {episode.overview || "No overview available."}
                  </p>

                  <div className="flex items-center gap-3 mt-2 text-xs text-text-muted">
                    <div className="flex items-center gap-1">
                      <Calendar className="w-3 h-3" />
                      {formatDate(episode.air_date)}
                    </div>
                    {episode.vote_average > 0 && (
                      <div className="flex items-center gap-1">
                        <Star className="w-3 h-3 text-yellow-500 fill-current" />
                        {episode.vote_average.toFixed(1)}
                      </div>
                    )}
                    {episode.runtime > 0 && (
                      <div className="flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {episode.runtime}m
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}