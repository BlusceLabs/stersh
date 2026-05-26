import React, { useRef, useEffect } from 'react';

interface VideoPlayerProps {
  src: string;
  title?: string;
  autoPlay?: boolean;
  onNextEpisode?: () => void;
  hasNextEpisode?: boolean;
}

export default function VideoPlayer({ 
  src, 
  title, 
  autoPlay = false,
  onNextEpisode,
  hasNextEpisode = false
}: VideoPlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const handleEnded = () => {
      if (hasNextEpisode && onNextEpisode) {
        onNextEpisode();
      }
    };

    video.addEventListener('ended', handleEnded);
    return () => video.removeEventListener('ended', handleEnded);
  }, [hasNextEpisode, onNextEpisode]);

  return (
    <div class="relative w-full h-full bg-black rounded-lg overflow-hidden">
      <video
        ref={videoRef}
        src={src}
        controls
        autoPlay={autoPlay}
        class="w-full h-full"
        title={title}
      >
        Your browser does not support the video tag.
      </video>
    </div>
  );
}