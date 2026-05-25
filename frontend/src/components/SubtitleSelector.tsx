import { useState } from "react";

interface SubtitleOption {
  language: string;
  label: string;
  src: string;
}

interface SubtitleSelectorProps {
  subtitles: SubtitleOption[];
  currentLanguage: string;
  onSelect: (language: string) => void;
}

export default function SubtitleSelector({
  subtitles,
  currentLanguage,
  onSelect,
}: SubtitleSelectorProps) {
  const [showMenu, setShowMenu] = useState(false);

  return (
    <div className="relative">
      <button
        onClick={() => setShowMenu(!showMenu)}
        className="bg-gray-800 text-white px-3 py-2 rounded flex items-center gap-2"
      >
        <span>Subtitle: {currentLanguage || "Off"}</span>
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      
      {showMenu && (
        <div className="absolute mt-2 w-48 bg-gray-900 rounded-lg shadow-xl z-10">
          <button
            onClick={() => {
              onSelect("");
              setShowMenu(false);
            }}
            className="w-full text-left px-4 py-2 hover:bg-gray-800 text-gray-300"
          >
            Off
          </button>
          {subtitles.map((subtitle) => (
            <button
              key={subtitle.language}
              onClick={() => {
                onSelect(subtitle.language);
                setShowMenu(false);
              }}
              className="w-full text-left px-4 py-2 hover:bg-gray-800 text-gray-300"
            >
              {subtitle.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}