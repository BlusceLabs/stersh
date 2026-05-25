import { useState, useEffect } from "react";
import MovieCard from "@/components/movie/MovieCard";

export default function Recommendations() {
  const [recommendations, setRecommendations] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchRecommendations() {
      try {
        const token = localStorage.getItem("access_token");
        if (!token) {
          const response = await fetch("/api/tmdb/movie/popular");
          const data = await response.json();
          setRecommendations(data.results.slice(0, 8));
        } else {
          const response = await fetch("/api/recommendations/personalized", {
            headers: { Authorization: `Bearer ${token}` },
          });
          const data = await response.json();
          setRecommendations(data.recommendations || []);
        }
        setLoading(false);
      } catch (error) {
        console.error("Error fetching recommendations:", error);
        setLoading(false);
      }
    }

    fetchRecommendations();
  }, []);

  if (loading) {
    return (
      <div className="h-64 flex items-center justify-center">
        <div className="text-gray-400">Loading recommendations...</div>
      </div>
    );
  }

  return (
    <div className="mb-12">
      <h2 className="text-2xl font-bold mb-6">Recommended for You</h2>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-6">
        {recommendations.map((movie) => (
          <MovieCard key={movie.id} movie={movie} type={movie.media_type || "movie"} />
        ))}
      </div>
    </div>
  );
}