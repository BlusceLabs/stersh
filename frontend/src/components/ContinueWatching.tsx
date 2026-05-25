import { useState, useEffect } from "react";
import { Link } from "@tanstack/react-router";

interface ContinueWatchingItem {
  id: number;
  title: string;
  poster_path: string | null;
  backdrop_path: string | null;
  media_type: "movie" | "tv";
  progress: number;
  total_duration: number;
}

export default function ContinueWatching() {
  const [continueWatching, setContinueWatching] = useState<ContinueWatchingItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchContinueWatching() {
      try {
        const token = localStorage.getItem("access_token");
        if (!token) {
          setContinueWatching([]);
          setLoading(false);
          return;
        }

        const response = await fetch("/api/history/continue_watching", {
          headers: { Authorization: `Bearer ${token}` },
        });
        const data = await response.json();
        setContinueWatching(data.items || []);
      } catch (error) {
        console.error("Error fetching continue watching:", error);
      } finally {
        setLoading(false);
      }
    }

    fetchContinueWatching();
  }, []);

  if (loading) {
    return (
      <div className="relative h-[300px] w-full overflow-hidden">
        <div className="absolute inset-0 bg-gray-800 loader" />
      </div>
    );
  }

  return (
    <div className="relative h-[300px] w-full overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-r from-black/90 to-transparent" />
      
      <div className="relative z-10 flex h-full flex-col justify-center px-10">
        <h2 className="text-2xl font-bold mb-6 text-white">Continue Watching</h2>
        
        <div className="flex gap-4 overflow-x-auto pb-4">
          {continueWatching.map((item) => (
            <Link
              key={item.id}
              to={`/player/${item.media_type}/${item.id}`}
              className="min-w-[200px] group"
            >
              <div className="aspect-ratio-2/3 overflow-hidden rounded-lg bg-gray-800">
                <img
                  src={`https://image.tmdb.org/t/p/w200${item.poster_path}`}
                  alt={item.title}
                  className="w-full h-full object-cover"
                />
                <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent p-2">
                  <div className="flex items-center justify-between text-white">
                    <span className="text-sm">
                      {Math.round((item.progress / item.total_duration) * 100)}% watched
                    </span>
                    <button className="text-xs bg-red-600 px-2 py-1 rounded">
                      Resume
                    </button>
                  </div>
                </div>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}