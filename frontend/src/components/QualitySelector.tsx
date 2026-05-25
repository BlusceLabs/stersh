import { useState } from "react";

interface QualityOption {
  label: string;
  value: string;
  src: string;
}

interface QualitySelectorProps {
  qualities: QualityOption[];
  currentQuality: string;
  onSelectQuality: (quality: string) => void;
}

export default function QualitySelector({ qualities, currentQuality, onSelectQuality }: QualitySelectorProps) {
  const [showMenu, setShowMenu] = useState(false);

  return (
    <div className="relative">
      <button
        onClick={() => setShowMenu(!showMenu)}
        className="bg-gray-800 text-white px-4 py-2 rounded flex items-center gap-2"
      >
        <span>{currentQuality}</span>
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      
      {showMenu && (
        <div className="absolute mt-2 w-full bg-gray-900 rounded-lg shadow-xl z-10">
          {qualities.map((quality) => (
            <button
              key={quality.value}
              onClick={() => {
                onSelectQuality(quality.value);
                setShowMenu(false);
              }}
              className={`w-full text-left px-4 py-3 border-b border-gray-700 hover:bg-gray-800 ${quality.value === currentQuality ? "bg-gray-700" : ""}`}
            >
              <div className="flex items-center justify-between">
                <span>{quality.label}</span>
                {quality.value === currentQuality && (
                  <svg className="w-5 h-5 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L12 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                )}
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}