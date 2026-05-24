import { motion } from "framer-motion"
import { Info, Play } from "lucide-react"
import { useEffect, useMemo, useRef, useState } from "react"

import { getHomepage, type HomepageResponse } from "@/api/home"

export function HeroTrailerSection() {
  const [items, setItems] = useState<HomepageResponse["hero"]>([])
  const [currentIndex, setCurrentIndex] = useState(0)

  const videoRef = useRef<HTMLIFrameElement | null>(null)

  useEffect(() => {
    async function load() {
      try {
        const data = await getHomepage()
        setItems(data.hero || [])
      } catch (err) {
        console.error(err)
      }
    }

    load()
  }, [])

  const current = useMemo(
    () => items[currentIndex],
    [items, currentIndex]
  )

  useEffect(() => {
    if (!current) return

    const duration = 120000

    const timeout = setTimeout(() => {
      setCurrentIndex((prev) =>
        prev === items.length - 1 ? 0 : prev + 1
      )
    }, duration)

    return () => clearTimeout(timeout)
  }, [current, items.length])

  if (!current) {
    return (
      <section className="relative h-screen overflow-hidden bg-[#070B14]" />
    )
  }

  return (
    <section className="relative h-screen overflow-hidden">
      {/* BACKDROP */}
      <img
        src={current.backdropPath}
        alt={current.title}
        className="
          absolute
          inset-0
          h-full
          w-full
          object-cover
        "
      />

      {/* YOUTUBE TRAILER */}
      {current.trailerKey && (
        <iframe
          ref={videoRef}
          className="
            absolute
            inset-0
            h-full
            w-full
            scale-[1.35]
            opacity-40
          "
          src={`https://www.youtube.com/embed/${current.trailerKey}?autoplay=1&mute=1&controls=0&loop=0&playlist=${current.trailerKey}&modestbranding=1&showinfo=0`}
          allow="autoplay; fullscreen"
        />
      )}

      {/* OVERLAYS */}
      <div
        className="
          absolute
          inset-0
          bg-gradient-to-r
          from-[#070B14]
          via-[#070B14]/70
          to-transparent
        "
      />

      <div
        className="
          absolute
          inset-0
          bg-gradient-to-t
          from-[#070B14]
          via-transparent
          to-black/40
        "
      />

      <div
        className="
          absolute
          inset-0
          bg-[radial-gradient(circle,transparent_40%,rgba(0,0,0,0.7)_100%)]
        "
      />

      {/* CONTENT */}
      <div
        className="
          relative
          z-20
          flex
          h-full
          items-end
          px-6
          pb-40
          md:px-16
        "
      >
        <motion.div
          key={current.id}
          initial={{
            opacity: 0,
            y: 60,
          }}
          animate={{
            opacity: 1,
            y: 0,
          }}
          exit={{
            opacity: 0,
          }}
          transition={{
            duration: 1,
            ease: [0.22, 1, 0.36, 1],
          }}
          className="max-w-2xl"
        >
          {/* TMDB LOGO */}
          {current.logoPath && (
            <img
              src={current.logoPath}
              alt={current.title}
              className="
                mb-8
                max-w-[340px]
                object-contain
                drop-shadow-[0_10px_40px_rgba(0,0,0,0.7)]
              "
            />
          )}

          {/* METADATA */}
          <div
            className="
              mb-6
              flex
              items-center
              gap-3
              text-sm
              text-white/70
            "
          >
            <span>{current.releaseYear}</span>

            <span className="h-1 w-1 rounded-full bg-white/30" />

            <span>{current.runtime || "Movie"}</span>

            <span className="h-1 w-1 rounded-full bg-white/30" />

            <span
              className="
                rounded-full
                border
                border-[#8B5CF6]/30
                bg-[#8B5CF6]/10
                px-3
                py-1
                text-[#C4B5FD]
              "
            >
              ★ {current.rating}
            </span>
          </div>

          {/* OVERVIEW */}
          <p
            className="
              max-w-xl
              text-base
              leading-8
              text-white/70
              md:text-lg
            "
          >
            {current.overview}
          </p>

          {/* BUTTONS */}
          <div className="mt-10 flex items-center gap-4">
            <button
              className="
                group
                relative
                overflow-hidden
                rounded-full
                px-8
                py-4
                transition-all
                duration-500
                hover:scale-[1.03]
              "
            >
              <div
                className="
                  absolute
                  inset-0
                  bg-gradient-to-r
                  from-[#8B5CF6]
                  to-[#22D3EE]
                "
              />

              <span
                className="
                  relative
                  z-10
                  flex
                  items-center
                  gap-3
                  text-sm
                  font-semibold
                  tracking-wide
                "
              >
                <Play size={18} />
                WATCH NOW
              </span>
            </button>

            <button
              className="
                flex
                items-center
                gap-3
                rounded-full
                border
                border-white/[0.08]
                bg-white/[0.04]
                px-7
                py-4
                text-sm
                font-medium
                text-white/80
                backdrop-blur-2xl
                transition-all
                duration-300
                hover:bg-white/[0.08]
                hover:text-white
              "
            >
              <Info size={18} />
              More Info
            </button>
          </div>
        </motion.div>
      </div>

      {/* PROGRESS */}
      <div
        className="
          absolute
          bottom-16
          left-1/2
          z-30
          flex
          -translate-x-1/2
          items-center
          gap-3
        "
      >
        <div className="h-[3px] w-28 overflow-hidden rounded-full bg-white/10">
          <motion.div
            key={current.id}
            initial={{ width: 0 }}
            animate={{ width: "100%" }}
            transition={{
              duration: 120,
              ease: "linear",
            }}
            className="
              h-full
              rounded-full
              bg-gradient-to-r
              from-[#8B5CF6]
              to-[#22D3EE]
            "
          />
        </div>

        <span className="text-xs text-white/40">
          Next Trailer
        </span>
      </div>
    </section>
  )
}
