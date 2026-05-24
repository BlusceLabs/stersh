import { useNavigate } from "@tanstack/react-router"
import { User2, Clapperboard, Heart, Settings, LogOut, ChevronRight } from "lucide-react"
import { useWatchlist } from "@/stores/watchlist"
import { useLiked } from "@/stores/liked"
import { AmbientBackground } from "@/components/cinematic/AmbientBackground/AmbientBackground"

import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"

export default function ProfilePage() {
  const navigate = useNavigate()
  const watchlistCount = useWatchlist((s) => s.items.length)
  const likedCount = useLiked((s) => s.items.length)

  const menuItems = [
    {
      icon: Clapperboard,
      label: "Watchlist",
      count: watchlistCount,
      onClick: () => navigate({ to: "/watchlist" }),
    },
    {
      icon: Heart,
      label: "Liked",
      count: likedCount,
      onClick: () => navigate({ to: "/liked" }),
    },
    {
      icon: Settings,
      label: "Settings",
      onClick: () => navigate({ to: "/settings" }),
    },
  ]

  return (
    <main className="relative min-h-screen bg-background text-foreground">
      <AmbientBackground />

      <div className="relative z-10 mx-auto max-w-xl px-6 pt-32 pb-40">
        {/* AVATAR */}
        <div className="flex flex-col items-center">
          <div className="flex h-24 w-24 items-center justify-center rounded-full bg-gradient-to-br from-primary to-cyan-500">
            <User2 size={40} className="text-primary-foreground" />
          </div>
          <h1 className="mt-4 text-2xl font-bold">Guest</h1>
          <p className="text-sm text-muted-foreground">Free plan</p>
        </div>

        {/* STATS */}
        <div className="mt-8 grid grid-cols-3 gap-4">
          <Card className="border-border/50 bg-card/50 backdrop-blur-xl">
            <CardContent className="p-4 text-center">
              <p className="text-xl font-bold">{watchlistCount}</p>
              <p className="text-xs text-muted-foreground">Watchlist</p>
            </CardContent>
          </Card>
          <Card className="border-border/50 bg-card/50 backdrop-blur-xl">
            <CardContent className="p-4 text-center">
              <p className="text-xl font-bold">{likedCount}</p>
              <p className="text-xs text-muted-foreground">Liked</p>
            </CardContent>
          </Card>
          <Card className="border-border/50 bg-card/50 backdrop-blur-xl">
            <CardContent className="p-4 text-center">
              <p className="text-xl font-bold">0</p>
              <p className="text-xs text-muted-foreground">Watched</p>
            </CardContent>
          </Card>
        </div>

        {/* MENU */}
        <div className="mt-8 space-y-2">
          {menuItems.map((item) => (
            <Button
              key={item.label}
              variant="ghost"
              className="flex w-full items-center justify-between rounded-xl border border-border/50 bg-card/30 px-4 py-6 h-auto hover:bg-card/60"
              onClick={item.onClick}
            >
              <div className="flex items-center gap-3">
                <item.icon size={18} className="text-muted-foreground" />
                <span className="text-sm font-medium">{item.label}</span>
              </div>
              <div className="flex items-center gap-2">
                {item.count !== undefined && item.count > 0 && (
                  <Badge variant="secondary" className="rounded-full">
                    {item.count}
                  </Badge>
                )}
                <ChevronRight size={16} className="text-muted-foreground/40" />
              </div>
            </Button>
          ))}

          <Separator className="my-2 bg-border/50" />

          <Button
            variant="ghost"
            className="flex w-full items-center gap-3 rounded-xl border border-destructive/20 bg-destructive/5 px-4 py-6 h-auto hover:bg-destructive/10 hover:text-destructive text-destructive"
          >
            <LogOut size={18} />
            <span className="text-sm font-medium">Sign Out</span>
          </Button>
        </div>
      </div>
    </main>
  )
}
