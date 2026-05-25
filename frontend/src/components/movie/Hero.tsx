import { useState, useEffect, useRef } from "react";
import { Link } from "@tanstack/react-router";
import { Volume2, VolumeX } from "lucide-react";

export default function Hero() {
  const [featured, setFeatured] = useState<any>(null);
  const [logoUrl, setLogoUrl] = useState<string | null>(null);
  const [trailerKey, setTrailerKey] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [isMuted, setIsMuted] = useState(true);
  const iframeRef = useRef<HTMLIFrameElement>(null);

  useEffect(() => {
    const fetchFeatured = async () => {
      try {
        const data = await fetch("/api/tmdb/trending/all/week").then(res => res.json());
        const randomItem = data.results[Math.floor(Math.random() * 5)];
        setFeatured(randomItem);
        
        if (randomItem.id) {
          const mediaType = randomItem.media_type || "movie";
          const [imagesData, videosData] = await Promise.all([
            fetch(`/api/tmdb/${mediaType}/${randomItem.id}/images`).then(res => res.json()),
            fetch(`/api/tmdb/${mediaType}/${randomItem.id}/videos`).then(res => res.json())
          ]);
          
          const englishLogo = imagesData.logos?.find((l: any) => l.iso_639_1 === "en");
          const fallbackLogo = imagesData.logos?.[0];
          if (englishLogo?.file_path) {
            setLogoUrl(`https://image.tmdb.org/t/p/original${englishLogo.file_path}`);
          } else if (fallbackLogo?.file_path) {
            setLogoUrl(`https://image.tmdb.org/t/p/original${fallbackLogo.file_path}`);
          }

          const trailer = videosData.results?.find((v: any) => 
            v.site === "YouTube" && v.type === "Trailer"
          );
          if (trailer) {
            setTrailerKey(trailer.key);
          }
        }
      } catch (error) {
        console.error("Failed to fetch hero content:", error);
        setFeatured({
          id: 1,
          title: "Dune: Part Two",
          name: "Dune: Part Two",
          backdrop_path: "/xOMo8BRK7PfcJv9JCnx7s5hj0PX.jpg",
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
      <div className="relative h-screen w-full bg-black flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-yellow-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
        </div>
      </div>
    );
  }

  const title = featured.title || featured.name;
  const backdropUrl = featured.backdrop_path 
    ? `https://image.tmdb.org/t/p/original${featured.backdrop_path}` 
    : "https://image.tmdb.org/t/p/original/5a4JdoFwll5DRtKMe7J0VzhTDpR.jpg";

return (
    <section className="relative h-screen w-full overflow-hidden">
      {trailerKey ? (
        <>
          <div className="absolute inset-0 overflow-hidden">
            <iframe
              ref={iframeRef}
              src={`https://www.youtube.com/embed/${trailerKey}?autoplay=1&mute=1&loop=1&playlist=${trailerKey}&controls=0&showinfo=0&rel=0&iv_load_policy=3&modestbranding=1&disablekb=1&fs=0`}
              className="absolute w-full h-full"
              style={{ 
                width: "200vh",
                height: "100vh",
                left: "50%",
                top: "50%",
                transform: "translate(-50%, -50%)",
                filter: "brightness(1.1)"
              }}
              allow="autoplay; encrypted-media"
              allowFullScreen
            />
          </div>
          <button
            onClick={() => {
              if (iframeRef.current) {
                iframeRef.current.contentWindow?.postMessage(
                  JSON.stringify({
                    event: "command",
                    func: isMuted ? "unMute" : "mute",
                    args: []
                  }),
                  "*"
                );
              }
              setIsMuted(!isMuted);
            }}
            className="absolute top-6 right-6 z-20 flex items-center gap-2 bg-black/50 hover:bg-black/70 text-white px-4 py-2 rounded-full backdrop-blur-sm transition-all"
          >
            {isMuted ? <VolumeX size={18} /> : <Volume2 size={18} />}
            <span className="text-sm font-medium">{isMuted ? "Unmute" : "Mute"}</span>
          </button>
        </>
      ) : (
        <img
          src={backdropUrl}
          alt={title}
          className="absolute inset-0 h-full w-full object-cover"
          style={{ filter: "brightness(1.1)" }}
        />
      )}

      <div className="absolute inset-0 bg-gradient-to-b from-black via-black/85 to-transparent" />
      <div className="absolute inset-0 bg-gradient-to-r from-black/95 via-black/70 to-transparent" />

      <div className="absolute bottom-20 left-12 md:left-20 z-10 max-w-3xl">
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

        <div className="flex items-center gap-6">
          <Link
            to="/home"
            className="flex items-center gap-3 bg-white text-black hover:bg-white/90 transition-all px-10 py-4 rounded-full font-bold text-lg uppercase tracking-wider shadow-2xl"
          >
            Home
          </Link>
          
          <Link
            to="/search"
            className="flex items-center gap-3 bg-white/10 hover:bg-white/20 backdrop-blur-md border border-white/20 transition-all px-10 py-4 rounded-full font-bold text-lg uppercase tracking-wider"
          >
            Browse
          </Link>
        </div>
      </div>

      <div className="absolute bottom-8 right-12 md:right-20 z-10">
        <div className="text-right">
          <h2 className="text-5xl md:text-6xl font-black bg-gradient-to-r from-yellow-500 to-yellow-300 bg-clip-text text-transparent mb-2">
            WATCHFY
          </h2>
          <p className="text-gray-400 text-sm tracking-wider">Stream Anywhere</p>
        </div>
      </div>
    </section>
  );
}