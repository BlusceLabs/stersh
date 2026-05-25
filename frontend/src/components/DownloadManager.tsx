import { useState, useEffect } from "react";

export default function DownloadManager() {
  const [downloads, setDownloads] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchDownloads() {
      try {
        const token = localStorage.getItem("access_token");
        if (!token) {
          setDownloads([]);
          setLoading(false);
          return;
        }

        const response = await fetch("/api/downloads", {
          headers: { Authorization: `Bearer ${token}` },
        });
        const data = await response.json();
        setDownloads(data.downloads || []);
      } catch (error) {
        console.error("Error fetching downloads:", error);
      } finally {
        setLoading(false);
      }
    }

    fetchDownloads();
  }, []);

  if (loading) {
    return <div>Loading...</div>;
  }

  return (
    <div className="px-6 py-8">
      <div className="max-w-6xl mx-auto">
        <h2 className="text-3xl font-bold mb-8">My Downloads</h2>
        
        {downloads.length === 0 ? (
          <div className="text-center text-gray-500 py-12">
            <p>No downloads yet.</p>
            <p className="mt-4">
              Download movies and TV shows to watch offline.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-6">
            {downloads.map((download) => (
              <div key={download.id} className="aspect-ratio-2/3 overflow-hidden rounded-lg bg-gray-800">
                <img
                  src={`https://image.tmdb.org/t/p/w200${download.poster_path}`}
                  alt={download.title || download.name}
                  className="w-full h-full object-cover"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black/80 to-transparent" />
                <div className="absolute bottom-2 left-2 right-2">
                  <div className="flex justify-between items-center">
                    <span className="text-white text-sm">{download.progress}%</span>
                    <button
                      onClick={() => {}}
                      className="text-red-500 hover:text-red-400"
                    >
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 7l-.5-2.5L7 3V9l10 5-10 5V17l-2-2m-2 6l-2-2m2 2l2-2m-2 2l-2 2m2-2l2 2" />
                      </svg>
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}