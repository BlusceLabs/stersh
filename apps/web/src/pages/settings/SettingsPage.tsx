import {
  Palette,
  PlayCircle,
  Monitor,
  ChevronRight,
  Moon,
  Sun,
} from "lucide-react"

import { usePreferencesStore } from "@/stores/preferences.store"
import { useContinueWatching } from "@/stores/continue"
import { AmbientBackground } from "@/components/cinematic/AmbientBackground/AmbientBackground"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"

export default function SettingsPage() {
  const { theme, autoplay, quality, setTheme, setAutoplay, setQuality } =
    usePreferencesStore()

  const clearContinue = useContinueWatching((s) => s.clearAll)

  const clearAllData = () => {
    useContinueWatching.getState().clearAll()
    localStorage.removeItem("watchfy-watchlist")
    localStorage.removeItem("watchfy-liked")
    localStorage.removeItem("watchfy-preferences")
    window.location.reload()
  }

  return (
    <main className="relative min-h-screen bg-background text-foreground">
      <AmbientBackground />

      <div className="relative z-10 mx-auto max-w-xl px-6 pt-32 pb-40">
        <h1 className="text-4xl font-bold tracking-tight md:text-5xl">Settings</h1>

        {/* PLAYBACK */}
        <Card className="mt-8 border-border/50 bg-card/50 backdrop-blur-xl">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base font-semibold">
              <PlayCircle size={18} className="text-muted-foreground" />
              Playback
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* AUTOPLAY */}
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium">Autoplay</p>
                <p className="text-xs text-muted-foreground">
                  Automatically start playing videos
                </p>
              </div>
              <Button
                variant={autoplay ? "default" : "outline"}
                size="sm"
                className="rounded-full"
                onClick={() => setAutoplay(!autoplay)}
              >
                {autoplay ? "On" : "Off"}
              </Button>
            </div>

            <Separator className="bg-border/50" />

            {/* QUALITY */}
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium">Default Quality</p>
                <p className="text-xs text-muted-foreground">
                  Preferred streaming resolution
                </p>
              </div>
              <div className="flex gap-2">
                {(["auto", "1080p", "720p", "480p"] as const).map((q) => (
                  <Button
                    key={q}
                    variant={quality === q ? "default" : "outline"}
                    size="sm"
                    className="rounded-full text-xs px-3"
                    onClick={() => setQuality(q)}
                  >
                    {q === "auto" ? "Auto" : q}
                  </Button>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* APPEARANCE */}
        <Card className="mt-4 border-border/50 bg-card/50 backdrop-blur-xl">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base font-semibold">
              <Palette size={18} className="text-muted-foreground" />
              Appearance
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium">Theme</p>
                <p className="text-xs text-muted-foreground">
                  Light or dark mode
                </p>
              </div>
              <div className="flex gap-2">
                <Button
                  variant={theme === "dark" ? "default" : "outline"}
                  size="sm"
                  className="rounded-full gap-1.5"
                  onClick={() => setTheme("dark")}
                >
                  <Moon size={14} />
                  Dark
                </Button>
                <Button
                  variant={theme === "light" ? "default" : "outline"}
                  size="sm"
                  className="rounded-full gap-1.5"
                  onClick={() => setTheme("light")}
                >
                  <Sun size={14} />
                  Light
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* DATA */}
        <Card className="mt-4 border-border/50 bg-card/50 backdrop-blur-xl">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base font-semibold">
              <Monitor size={18} className="text-muted-foreground" />
              Data
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <Button
              variant="ghost"
              className="flex w-full items-center justify-between rounded-lg px-3 py-5 h-auto hover:bg-card/60"
              onClick={() => {
                if (confirm("Clear all continue watching progress?")) {
                  clearContinue()
                }
              }}
            >
              <div>
                <p className="text-sm font-medium">Clear Continue Watching</p>
                <p className="text-xs text-muted-foreground">
                  Remove all saved playback progress
                </p>
              </div>
              <ChevronRight size={16} className="text-muted-foreground/40" />
            </Button>

            <Separator className="bg-border/50" />

            <Button
              variant="ghost"
              className="flex w-full items-center justify-between rounded-lg px-3 py-5 h-auto hover:bg-destructive/10 hover:text-destructive text-destructive"
              onClick={() => {
                if (
                  confirm(
                    "This will clear ALL local data including watchlist, liked items, and preferences. This cannot be undone."
                  )
                ) {
                  clearAllData()
                }
              }}
            >
              <div>
                <p className="text-sm font-medium">Reset All Data</p>
                <p className="text-xs text-muted-foreground">
                  Clear everything and start fresh
                </p>
              </div>
              <ChevronRight size={16} className="text-muted-foreground/40" />
            </Button>
          </CardContent>
        </Card>
      </div>
    </main>
  )
}
