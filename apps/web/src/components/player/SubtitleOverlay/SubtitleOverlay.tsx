"use client";

import { useEffect, useRef, useState, useCallback } from "react";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface SubtitleTrack {
  label: string;
  language: string;
  url: string;
  format: string;
}

export interface SubtitleCue {
  start: number;
  end: number;
  text: string;
}

export interface SubtitleOverlayProps {
  currentTime: number;
  duration: number;
  tracks: SubtitleTrack[];
  activeTrack: string | null;
  onTrackChange: (url: string | null) => void;
  visible: boolean;
}

// ─── VTT Parser ──────────────────────────────────────────────────────────────

function parseVTT(vttContent: string): SubtitleCue[] {
  const cues: SubtitleCue[] = [];
  const lines = vttContent.split("\n");
  let i = 0;

  // Skip WEBVTT header
  while (i < lines.length && !lines[i].includes("-->")) {
    i++;
  }

  while (i < lines.length) {
    const line = lines[i].trim();
    if (line.includes("-->")) {
      const parts = line.split("-->");
      if (parts.length === 2) {
        const start = parseVTTime(parts[0].trim());
        const end = parseVTTime(parts[1].trim());

        // Collect text lines
        const textLines: string[] = [];
        i++;
        while (i < lines.length && lines[i].trim() !== "" && !lines[i].includes("-->")) {
          textLines.push(lines[i].trim());
          i++;
        }

        if (textLines.length > 0 && start !== null && end !== null) {
          cues.push({
            start,
            end,
            text: textLines.join("\n"),
          });
        }
        continue;
      }
    }
    i++;
  }

  return cues;
}

function parseVTTime(timeStr: string): number | null {
  // Format: HH:MM:SS.mmm or MM:SS.mmm
  const match = timeStr.match(/(?:(\d{2}):)?(\d{2}):(\d{2})\.(\d{3})/);
  if (!match) return null;
  const hours = parseInt(match[1] || "0", 10);
  const minutes = parseInt(match[2], 10);
  const seconds = parseInt(match[3], 10);
  const ms = parseInt(match[4], 10);
  return hours * 3600 + minutes * 60 + seconds + ms / 1000;
}

// ─── Component ────────────────────────────────────────────────────────────────

export default function SubtitleOverlay({
  currentTime,
  tracks,
  activeTrack,
  onTrackChange,
  visible,
}: SubtitleOverlayProps) {
  const [cues, setCues] = useState<SubtitleCue[]>([]);
  const [currentCue, setCurrentCue] = useState<string | null>(null);
  const [showMenu, setShowMenu] = useState(false);
  const fetchedRef = useRef<string | null>(null);

  // Fetch and parse subtitle file when track changes
  useEffect(() => {
    if (!activeTrack) {
      setCues([]);
      fetchedRef.current = null;
      return;
    }

    if (fetchedRef.current === activeTrack) return;

    const fetchSubtitles = async () => {
      try {
        // Use our proxy to avoid CORS
        const proxyUrl = `/api/subtitles/proxy?url=${encodeURIComponent(activeTrack)}`;
        const resp = await fetch(proxyUrl);
        if (!resp.ok) throw new Error("Failed to fetch subtitles");
        const text = await resp.text();
        const parsed = parseVTT(text);
        setCues(parsed);
        fetchedRef.current = activeTrack;
      } catch (err) {
        console.error("Subtitle load failed:", err);
        setCues([]);
      }
    };

    fetchSubtitles();
  }, [activeTrack]);

  // Find current cue based on playback time
  useEffect(() => {
    if (cues.length === 0) {
      setCurrentCue(null);
      return;
    }

    const cue = cues.find(
      (c) => currentTime >= c.start && currentTime <= c.end
    );
    setCurrentCue(cue?.text || null);
  }, [currentTime, cues]);

  const handleTrackSelect = useCallback(
    (url: string | null) => {
      onTrackChange(url);
      setShowMenu(false);
    },
    [onTrackChange]
  );

  if (!visible && !activeTrack) return null;

  return (
    <>
      <style>{STYLES}</style>

      {/* Subtitle display */}
      {currentCue && (
        <div className="wfy-subtitle-display">
          <span className="wfy-subtitle-text">{currentCue}</span>
        </div>
      )}

      {/* Subtitle selector button */}
      {tracks.length > 0 && (
        <div className="wfy-subtitle-menu-wrap">
          <button
            className="wfy-subtitle-btn"
            onClick={() => setShowMenu((v) => !v)}
            title="Subtitles"
          >
            <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
              <path d="M20 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 14H4V6h16v12zM6 10h2v2H6zm0 4h8v2H6zm10 0h2v2h-2zm-6-4h8v2h-8z"/>
            </svg>
          </button>

          {showMenu && (
            <div className="wfy-subtitle-menu">
              <div className="wfy-subtitle-menu-header">Subtitles</div>
              <button
                className={`wfy-subtitle-option ${!activeTrack ? "selected" : ""}`}
                onClick={() => handleTrackSelect(null)}
              >
                Off
              </button>
              {tracks.map((track) => (
                <button
                  key={track.url}
                  className={`wfy-subtitle-option ${activeTrack === track.url ? "selected" : ""}`}
                  onClick={() => handleTrackSelect(track.url)}
                >
                  {track.language || track.label}
                  <span className="wfy-subtitle-lang">{track.format.toUpperCase()}</span>
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </>
  );
}

// ─── Styles ───────────────────────────────────────────────────────────────────

const STYLES = `
  .wfy-subtitle-display {
    position: absolute;
    bottom: 70px;
    left: 50%;
    transform: translateX(-50%);
    z-index: 15;
    pointer-events: none;
    max-width: 80%;
    text-align: center;
  }

  .wfy-subtitle-text {
    display: inline-block;
    background: rgba(0, 0, 0, 0.75);
    color: #fff;
    font-size: 16px;
    font-weight: 500;
    line-height: 1.4;
    padding: 4px 12px;
    border-radius: 4px;
    white-space: pre-wrap;
    text-shadow: 0 1px 2px rgba(0, 0, 0, 0.8);
    font-family: 'Syne', sans-serif;
  }

  .wfy-subtitle-menu-wrap {
    position: relative;
    display: inline-block;
  }

  .wfy-subtitle-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 38px;
    height: 38px;
    border: none;
    background: transparent;
    color: rgba(240, 238, 249, 0.8);
    border-radius: 8px;
    cursor: pointer;
    transition: color 0.15s ease, background 0.15s ease;
    padding: 0;
  }

  .wfy-subtitle-btn:hover {
    color: #F0EEF9;
    background: rgba(127, 119, 221, 0.18);
  }

  .wfy-subtitle-menu {
    position: absolute;
    bottom: calc(100% + 10px);
    right: 0;
    background: rgba(15, 12, 26, 0.95);
    border: 1px solid rgba(127, 119, 221, 0.2);
    border-radius: 10px;
    padding: 8px;
    min-width: 160px;
    box-shadow: 0 16px 48px rgba(0, 0, 0, 0.7);
    backdrop-filter: blur(16px);
    z-index: 30;
    animation: wfyFadeUp 0.18s ease;
  }

  .wfy-subtitle-menu-header {
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: rgba(240, 238, 249, 0.45);
    padding: 4px 8px 6px;
    margin: 0;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
    margin-bottom: 4px;
  }

  .wfy-subtitle-option {
    display: flex;
    align-items: center;
    justify-content: space-between;
    width: 100%;
    text-align: left;
    background: transparent;
    border: none;
    color: rgba(240, 238, 249, 0.75);
    font-family: 'Syne', sans-serif;
    font-size: 13px;
    font-weight: 500;
    padding: 6px 8px;
    border-radius: 6px;
    cursor: pointer;
    transition: background 0.12s ease, color 0.12s ease;
  }

  .wfy-subtitle-option:hover {
    background: rgba(127, 119, 221, 0.18);
    color: #F0EEF9;
  }

  .wfy-subtitle-option.selected {
    color: #7F77DD;
    background: rgba(127, 119, 221, 0.18);
  }

  .wfy-subtitle-lang {
    font-size: 9px;
    opacity: 0.5;
    margin-left: 8px;
  }

  @keyframes wfyFadeUp {
    from { opacity: 0; transform: translateY(6px); }
    to { opacity: 1; transform: translateY(0); }
  }
`;
