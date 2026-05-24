import { useEffect, useState } from "react"
import { motion } from "framer-motion"
import { ArrowRight } from "lucide-react"
import { Link } from "@tanstack/react-router"

import { AmbientBackground } from "@/components/cinematic/AmbientBackground/AmbientBackground"
import { Button } from "@/components/ui/button"

const API_URL = "http://localhost:8080/api"

export default function LandingPage() {
  const [backdrops, setBackdrops] = useState<string[]>([])
  const [index, setIndex] = useState(0)

  useEffect(() => {
    fetch(`${API_URL}/movies/trending`)
      .then((r) => r.json())
      .then((data: { results?: { backdropPath: string }[] }) => {
        const images = (data.results ?? [])
          .map((m) => m.backdropPath)
          .filter(Boolean)
        if (images.length > 0) setBackdrops(images)
      })
      .catch(() => {})
  }, [])

  useEffect(() => {
    if (backdrops.length < 2) return
    const timer = setInterval(() => {
      setIndex((i) => (i + 1) % backdrops.length)
    }, 17000)
    return () => clearInterval(timer)
  }, [backdrops])

  return (
    <main className="relative min-h-screen overflow-hidden bg-background text-foreground">
      <AmbientBackground />

      {/* ROTATING TRENDING BACKDROPS */}
      <div className="absolute inset-0 overflow-hidden">
        {backdrops.map((url, i) => (
          <img
            key={url}
            src={url}
            alt=""
            loading="lazy"
            decoding="async"
            className="absolute inset-0 h-full w-full scale-[1.08] object-cover transition-opacity duration-1000"
            style={{ opacity: i === index ? 0.16 : 0 }}
          />
        ))}

        <div className="absolute inset-0 bg-gradient-to-b from-black/20 via-background/50 to-background" />

        <div className="absolute left-[-15%] top-[5%] h-[40rem] w-[40rem] rounded-full bg-primary/20 blur-[180px]" />
        <div className="absolute bottom-[-10%] right-[-10%] h-[35rem] w-[35rem] rounded-full bg-cyan-500/15 blur-[180px]" />
        <div className="absolute inset-0 bg-[radial-gradient(circle,transparent_40%,rgba(0,0,0,0.75)_100%)]" />
      </div>

      {/* HERO */}
      <section className="relative z-20 flex min-h-screen flex-col items-center justify-center px-6 text-center">
        <motion.div
          initial={{ opacity: 0, y: 35 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15, duration: 1, ease: [0.22, 1, 0.36, 1] }}
          className="relative"
        >
          <h1 className="relative text-center text-6xl font-semibold tracking-tighter md:text-8xl lg:text-[9rem]">
            <span className="text-foreground">watch</span>
            <span className="bg-gradient-to-r from-primary via-purple-400 to-cyan-400 bg-clip-text text-transparent">
              !fy
            </span>
          </h1>
          <div className="absolute inset-0 bg-primary/10 blur-[100px]" />
        </motion.div>

        <motion.h2
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.35, duration: 0.9 }}
          className="mt-10 max-w-5xl text-center text-4xl font-medium leading-[1] tracking-tight text-foreground/95 md:text-6xl"
        >
          Streaming Reimagined
          <br />
          <span className="text-foreground/55">for Movies, TV & Anime</span>
        </motion.h2>

        <motion.p
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5, duration: 0.8 }}
          className="mt-8 max-w-2xl text-center text-base leading-8 text-muted-foreground md:text-lg"
        >
          Immerse yourself in a futuristic cinematic universe
          crafted for premium entertainment experiences.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.7, duration: 0.8 }}
          className="mt-14 flex flex-col items-center gap-4 sm:flex-row"
        >
          <Link to="/home">
            <Button
              size="lg"
              className="rounded-full bg-gradient-to-r from-primary to-cyan-500 text-primary-foreground hover:opacity-90 px-8"
            >
              Home
            </Button>
          </Link>

          <Link to="/search">
            <Button
              size="lg"
              variant="outline"
              className="rounded-full gap-2 px-8 group"
            >
              Browse
              <ArrowRight
                size={16}
                className="transition-transform duration-300 group-hover:translate-x-1"
              />
            </Button>
          </Link>
        </motion.div>

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1, duration: 1 }}
          className="mt-24 flex flex-wrap items-center justify-center gap-10 text-center"
        >
          {[
            ["10K+", "Movies & Shows"],
            ["4K HDR", "Ultra Cinematic"],
            ["Anime", "Sub & Dub"],
          ].map(([title, subtitle]) => (
            <div key={title}>
              <div className="text-2xl font-semibold tracking-tight">{title}</div>
              <div className="mt-1 text-sm text-muted-foreground">{subtitle}</div>
            </div>
          ))}
        </motion.div>
      </section>

      {/* BOTTOM CINEMATIC FADE */}
      <div className="pointer-events-none absolute inset-x-0 bottom-0 h-56 bg-gradient-to-t from-background to-transparent" />
    </main>
  )
}
