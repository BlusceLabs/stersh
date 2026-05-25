import { useState, useEffect } from "react";
import { useParams, useNavigate } from "@tanstack/react-router";
import { ArrowLeft, Loader2 } from "lucide-react";
import VideoPlayer from "@/components/player/VideoPlayer";
import { EpisodeSidebar } from "@/components/player/EpisodeSidebar";
import api from "@/utils/api";
import { usePlayerStore } from "@/store/usePlayerStore";

interface SeasonInfo {
  season_number: number;
  name: string;
  episode_count: number;
}

interface Episode {
  episode_number: number;
  name: string;
  overview: string;
  still_path: string | null;
  air_date: string;
  vote_average: number;
  runtime: number;
}

export default function PlayerPage() {
  const { mediaType, id } = useParams({ from: "/watch/$mediaType/$id" });
  const navigate = useNavigate();

  const [media, setMedia] = useState<any>(null);
  const [streamUrl, setStreamUrl] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showEpisodes, setShowEpisodes] = useState(false);
  const [episodes, setEpisodes] = useState<Episode[]>([]);
  const [seasons, setSeasons] = useState<SeasonInfo[]>([]);
  const [currentSeason, setCurrentSeason] = useState(1);
  const [currentEpisode, setCurrentEpisode] = useState(1);

  const { loadMedia } = usePlayerStore();

  useEffect(() => {
    const fetchMediaAndStream = async () => {
      if (!mediaType || !id) return;

      setLoading(true);
      setError(null);

      try {
        const mediaData =
          mediaType === "movie"
            ? await api.getMovie(Number(id))
            : await api.getTVShow(Number(id));

        setMedia(mediaData);

        if (mediaType === "tv" && mediaData) {
          const tvDetails = await api.get(`/tmdb/tv/${id}`);
          const seasonList =
            tvDetails.seasons?.map((s: any) => ({
              season_number: s.season_number,
              name: s.name,
              episode_count: s.episode_count,
            })) || [];
          setSeasons(seasonList);

          const seasonRes = await api.get(`/tmdb/tv/${id}/season/1`);
          if (seasonRes.episodes) {
            setEpisodes(seasonRes.episodes);
          }
        }

        const streamRes = await fetch(`/api/watch/${mediaType}/${id}`);

        if (!streamRes.ok) {
          const errorText = await streamRes.text();
          throw new Error(`Stream fetch failed: ${streamRes.status} ${errorText}`);
        }

        const streamData = await streamRes.json();

        if (streamData?.stream_url) {
          setStreamUrl(streamData.stream_url);
        } else {
          throw new Error("Stream URL not available");
        }

        loadMedia(id, mediaType as "movie" | "tv", mediaData.title || mediaData.name);
      } catch (err: any) {
        setError(err.message || "Failed to load content");
      } finally {
        setLoading(false);
      }
    };

    fetchMediaAndStream();
  }, [mediaType, id, loadMedia]);

  const handleBack = () => {
    navigate({ to: mediaType === "movie" ? `/movie/${id}` : `/tv/${id}` });
  };

  const playEpisode = (season: number, episode: number) => {
    setCurrentSeason(season);
    setCurrentEpisode(episode);
    navigate({ to: `/watch/tv/${id}?season=${season}&episode=${episode}` });
    setShowEpisodes(false);
  };

  const handleNextEpisode = () => {
    if (mediaType !== "tv") return;
    
    const currentIndex = episodes.findIndex(e => e.episode_number === currentEpisode);
    if (currentIndex >= 0 && currentIndex < episodes.length - 1) {
      const nextEpisode = episodes[currentIndex + 1];
      if (nextEpisode) {
        playEpisode(currentSeason, nextEpisode.episode_number);
      }
    }
  };

  const hasNextEpisode = mediaType === "tv" && episodes.some(e => e.episode_number > currentEpisode);

  if (loading) {
    return (
      <div className="fixed inset-0 bg-black flex items-center justify-center z-50">
        <div className="flex flex-col items-center gap-4">
          <Loader2 size={48} className="animate-spin text-yellow-500" />
          <p className="text-gray-400">Preparing your stream...</p>
        </div>
      </div>
    );
  }

  if (error || !streamUrl) {
    return (
      <div className="fixed inset-0 bg-black flex items-center justify-center z-50">
        <div className="text-center">
          <h2 className="text-2xl font-bold mb-3">Unable to Play</h2>
          <p className="text-gray-400 mb-8">{error || "Stream is currently unavailable"}</p>
          <button
            onClick={handleBack}
            className="px-8 py-3 bg-zinc-800 hover:bg-zinc-700 rounded-lg transition-colors"
          >
            Go Back
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-black overflow-hidden">
      {/* Back Button */}
      <button
        onClick={handleBack}
        className="absolute top-4 left-4 z-50 flex items-center gap-2 text-white hover:text-yellow-500 transition-colors bg-black/50 rounded-lg px-3 py-2"
      >
        <ArrowLeft size={20} />
        <span className="text-sm">Back</span>
      </button>

      {/* Title */}
      <div className="absolute top-4 right-36 z-40 pointer-events-none">
        <h1 className="text-white text-lg font-semibold bg-black/50 px-4 py-2 rounded-lg max-w-xs truncate">
          {media?.title || media?.name || "Watch"}
        </h1>
      </div>

      {/* Episode Toggle for TV Shows */}
      {mediaType === "tv" && episodes.length > 0 && (
        <button
          onClick={() => setShowEpisodes(!showEpisodes)}
          className="absolute top-4 right-4 z-50 text-white bg-black/50 rounded-lg px-3 py-2 hover:bg-yellow-500 hover:text-black transition-colors"
        >
          Episodes ({episodes.length})
        </button>
      )}

      {/* Video Player */}
      <div className="w-full h-full">
        <VideoPlayer src={streamUrl} autoPlay onNextEpisode={handleNextEpisode} hasNextEpisode={hasNextEpisode} />
      </div>

      {/* Episode Sidebar for TV Shows */}
      {mediaType === "tv" && episodes.length > 0 && (
        <>
          {/* Backdrop */}
          {showEpisodes && (
            <div
              className="absolute inset-0 bg-black/50 z-40"
              onClick={() => setShowEpisodes(false)}
            />
          )}

          {/* Sidebar */}
          <div
            className={`absolute top-0 right-0 bottom-0 w-80 bg-surface-raised border-l border-border z-50 transform transition-transform duration-300 ${
              showEpisodes ? "translate-x-0" : "translate-x-full"
            }`}
          >
            <EpisodeSidebar
              seasons={seasons}
              episodes={episodes}
              currentSeason={currentSeason}
              currentEpisode={currentEpisode}
              onSelectEpisode={playEpisode}
              onClose={() => setShowEpisodes(false)}
            />
          </div>
        </>
      )}
    </div>
  );
}