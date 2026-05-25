import { useState, useEffect } from "react";
import { Link } from "@tanstack/react-router";
import { Play, Info } from "lucide-react";

export default function HomeHero() {
  const [featured, setFeatured] = useState<any>(null);
  const [logoUrl, setLogoUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchFeatured = async () => {
      try {
        const data = await fetch("/api/tmdb/trending/all/week").then(res => res.json());
        const randomItem = data.results[Math.floor(Math.random() * 5)];
        setFeatured(randomItem);
        
        if (randomItem.id) {
          const imagesData = await fetch(`/api/tmdb/${randomItem.media_type || "movie"}/${randomItem.id}/images`).then(res => res.json());
          const englishLogo = imagesData.logos?.find((l: any) => l.iso_639_1 === "en");
          const fallbackLogo = imagesData.logos?.[0];
          if (englishLogo?.file_path) {
            setLogoUrl(`https://image.tmdb.org/t/p/original${englishLogo.file_path}`);
          } else if (fallbackLogo?.file_path) {
            setLogoUrl(`https://image.tmdb.org/t/p/original${fallbackLogo.file_path}`);
          }
        }
      } catch (error) {
        console.error("Failed to fetch hero content:", error);
        setFeatured({
          id: 1,
          title: "Dune: Part Two",
          name: "Dune: Part Two",
          overview: "Paul Atreides unites with Chani and the Fremen while seeking revenge against conspirators who destroyed his family.",
          backdrop_path: "/xOMo8BRK7PfcJv9JCnx7s5hj0PX.jpg",
          vote_average: 8.4,
          media_type: "movie",
        });
      } finally {
        setLoading(false);
      }
    };

    fetchFeatured();
  }, []);

  if (loading || !featured) {
    return (
      <div className="relative h-[95vh] w-full bg-black flex items-center justify-center">
        <div className="w-16 h-16 border-4 border-yellow-500 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  const title = featured.title || featured.name;
  const backdropUrl = featured.backdrop_path 
    ? `https://image.tmdb.org/t/p/original${featured.backdrop_path}` 
    : "https://image.tmdb.org/t/p/original/5a4JdoFwll5DRtKMe7J0VzhTDpR.jpg";

  const mediaType = featured.media_type || "movie";
  const detailPath = mediaType === "tv" ? `/tv/${featured.id}` : `/movie/${featured.id}`;

  return (
    <section className="relative h-[95vh] w-full overflow-hidden">
      <img
        src={backdropUrl}
        alt={title}
        className="absolute inset-0 h-full w-full object-cover scale-105"
        style={{ filter: "brightness(0.65)" }}
      />

      <div className="absolute inset-0 bg-gradient-to-b from-black via-black/85 to-transparent" />
      <div className="absolute inset-0 bg-gradient-to-r from-black/95 via-black/70 to-transparent" />
      <div className="absolute inset-0 bg-gradient-to-t from-black via-transparent to-transparent" />

      <div className="absolute bottom-32 left-12 md:left-20 z-10 max-w-3xl">
        <div className="mb-6">
          <span className="text-yellow-500 text-sm font-bold tracking-[0.3em] uppercase">
            Featured Now
          </span>
        </div>

        {logoUrl ? (
          <img 
            src={logoUrl} 
            alt={`${title} logo`}
            className="h-20 md:h-28 mb-6 drop-shadow-2xl"
          />
        ) : (
          <h1 className="text-6xl md:text-7xl lg:text-8xl font-black tracking-tighter mb-6 leading-[0.9] text-white drop-shadow-2xl">
            {title}
          </h1>
        )}

        <p className="max-w-2xl text-lg md:text-xl text-gray-200 mb-8 line-clamp-3 drop-shadow-lg font-light leading-relaxed">
          {featured.overview}
        </p>

        <div className="flex items-center gap-6">
          <Link
            to={detailPath}
            className="flex items-center gap-3 bg-white text-black hover:bg-white/90 transition-all px-10 py-4 rounded-full font-bold text-lg uppercase tracking-wider shadow-2xl"
          >
            <Play size={24} className="fill-current" />
            Play Now
          </Link>

          <Link
            to={detailPath}
            className="flex items-center gap-3 bg-white/10 hover:bg-white/20 backdrop-blur-md border border-white/20 transition-all px-10 py-4 rounded-full font-bold text-lg uppercase tracking-wider"
          >
            <Info size={20} />
            More Info
          </Link>
        </div>

        {featured.vote_average && (
          <div className="mt-8 flex items-center gap-3 text-lg text-gray-300">
            <span className="text-yellow-400 text-2xl">★</span>
            <span className="font-medium">{featured.vote_average.toFixed(1)}/10</span>
            <span className="text-gray-600">•</span>
            <span className="text-gray-400">Highly Rated</span>
          </div>
        )}
      </div>
    </section>
  );
}