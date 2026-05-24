import { useEffect, useRef } from "react"

interface Props {
  trailerKey: string
  backdropPath: string
  title: string
  onEnded: () => void
}

export function HeroPlayer({
  trailerKey,
  backdropPath,
  title,
  onEnded,
}: Props) {
  const iframeRef =
    useRef<HTMLIFrameElement | null>(null)

  useEffect(() => {
    if (trailerKey) return

    const timer = setTimeout(onEnded, 7000)
    return () => clearTimeout(timer)
  }, [trailerKey, onEnded])

  useEffect(() => {
    if (!trailerKey) return

    function handleMessage(
      event: MessageEvent
    ) {
      if (
        typeof event.data !== "string"
      ) {
        return
      }

      try {
        const data = JSON.parse(
          event.data
        )

        if (
          data.event === "onStateChange" &&
          data.info === 0
        ) {
          onEnded()
        }
      } catch {
        //
      }
    }

    window.addEventListener(
      "message",
      handleMessage
    )

    return () => {
      window.removeEventListener(
        "message",
        handleMessage
      )
    }
  }, [trailerKey, onEnded])

  if (!trailerKey) {
    return (
      <div className="absolute inset-0 overflow-hidden">
        <img
          src={backdropPath}
          alt={title}
          className="absolute inset-0 h-full w-full object-cover opacity-60"
        />
      </div>
    )
  }

  return (
    <div
      className="
        absolute
        inset-0
        overflow-hidden
      "
    >
      <iframe
        key={trailerKey}
        ref={iframeRef}
        className="
          absolute
          left-1/2
          top-1/2
          h-[56.25vw]
          min-h-full
          w-[177.77vh]
          min-w-full
          -translate-x-1/2
          -translate-y-1/2
          scale-[1.2]
        "
        src={`https://www.youtube.com/embed/${trailerKey}?autoplay=1&mute=1&controls=0&showinfo=0&rel=0&modestbranding=1&iv_load_policy=3&cc_load_policy=0&fs=0&enablejsapi=1`}
        allow="autoplay; encrypted-media"
      />
    </div>
  )
}
