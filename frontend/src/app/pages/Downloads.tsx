import { useState, useEffect } from "react";
import { Download, Pause, Play, Trash2, RefreshCw } from "lucide-react";

interface Download {
  id: number;
  title: string;
  progress: number;
  status: "downloading" | "completed" | "paused" | "failed";
  quality?: string;
  size?: string;
}

export default function Downloads() {
  const [downloads, setDownloads] = useState<Download[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchDownloads = async () => {
      try {
        const res = await fetch("/api/downloads");
        const data = await res.json();
        setDownloads(data || []);
      } catch (err) {
        console.error("Error fetching downloads:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchDownloads();
  }, []);

  const handleAction = (id: number, action: string) => {
    // TODO: Connect to real API endpoints
    console.log(`Action ${action} on download ${id}`);
    // Refresh logic can be added here
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "completed": return "text-green-500";
      case "downloading": return "text-blue-500";
      case "paused": return "text-yellow-500";
      case "failed": return "text-red-500";
      default: return "text-gray-400";
    }
  };

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-3xl font-bold">Downloads</h1>
        <button 
          onClick={() => window.location.reload()}
          className="flex items-center gap-2 text-sm text-gray-400 hover:text-white transition-colors"
        >
          <RefreshCw size={16} />
          Refresh
        </button>
      </div>

      {loading ? (
        <div className="flex justify-center py-20">
          <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-yellow-500"></div>
        </div>
      ) : downloads.length === 0 ? (
        <div className="text-center py-20">
          <Download size={64} className="mx-auto text-gray-600 mb-4" />
          <h3 className="text-xl font-medium mb-2">No downloads yet</h3>
          <p className="text-gray-500">Your downloaded content will appear here</p>
        </div>
      ) : (
        <div className="space-y-4">
          {downloads.map((download) => (
            <div 
              key={download.id} 
              className="bg-zinc-900 hover:bg-zinc-800 transition-colors rounded-xl p-5 flex items-center gap-5 group"
            >
              {/* Thumbnail / Icon */}
              <div className="w-20 h-12 bg-zinc-700 rounded-lg flex-shrink-0" />

              {/* Info */}
              <div className="flex-1 min-w-0">
                <h3 className="font-medium truncate">{download.title}</h3>
                <div className="flex items-center gap-3 text-sm text-gray-500 mt-1">
                  {download.quality && <span>{download.quality}</span>}
                  {download.size && <span>{download.size}</span>}
                  <span className={getStatusColor(download.status)}>
                    {download.status.charAt(0).toUpperCase() + download.status.slice(1)}
                  </span>
                </div>

                {/* Progress Bar */}
                <div className="mt-3">
                  <div className="w-full bg-zinc-700 h-1.5 rounded-full overflow-hidden">
                    <div 
                      className="h-1.5 bg-yellow-500 rounded-full transition-all duration-300"
                      style={{ width: `${download.progress}%` }}
                    />
                  </div>
                  <div className="text-xs text-gray-500 mt-1 flex justify-between">
                    <span>{download.progress}%</span>
                    {download.status === "downloading" && <span>Downloading...</span>}
                  </div>
                </div>
              </div>

              {/* Actions */}
              <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                {download.status === "downloading" && (
                  <button 
                    onClick={() => handleAction(download.id, "pause")}
                    className="p-3 hover:bg-zinc-700 rounded-full transition-colors"
                  >
                    <Pause size={20} />
                  </button>
                )}

                {download.status === "paused" && (
                  <button 
                    onClick={() => handleAction(download.id, "resume")}
                    className="p-3 hover:bg-zinc-700 rounded-full transition-colors"
                  >
                    <Play size={20} />
                  </button>
                )}

                {download.status === "failed" && (
                  <button 
                    onClick={() => handleAction(download.id, "retry")}
                    className="p-3 hover:bg-zinc-700 rounded-full transition-colors"
                  >
                    <RefreshCw size={20} />
                  </button>
                )}

                <button 
                  onClick={() => handleAction(download.id, "delete")}
                  className="p-3 hover:bg-red-500/20 hover:text-red-500 rounded-full transition-colors text-gray-400 hover:text-red-500"
                >
                  <Trash2 size={20} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}