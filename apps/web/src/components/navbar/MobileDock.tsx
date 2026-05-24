import { Link, useRouterState } from "@tanstack/react-router"
import {
  Home,
  Compass,
  Search,
  Clapperboard,
  User2,
} from "lucide-react"

const items = [
  { icon: Home, label: "Home", href: "/home" },
  { icon: Compass, label: "Discover", href: "/discover" },
  { icon: Search, label: "Search", href: "/search" },
  { icon: Clapperboard, label: "Watchlist", href: "/watchlist" },
  { icon: User2, label: "Profile", href: "/profile" },
]

export function MobileDock() {
  const pathname = useRouterState({
    select: (state) => state.location.pathname,
  })

  return (
    <div className="fixed bottom-0 left-0 right-0 z-[999] flex justify-center px-4 pb-4 md:hidden">
      <nav className="flex items-center gap-2 rounded-full border border-white/[0.08] bg-white/[0.06] px-4 py-3 backdrop-blur-[40px]">
        {items.map((item) => {
          const Icon = item.icon
          const active = pathname === item.href
          return (
            <Link
              key={item.href}
              to={item.href}
              className={`relative flex min-w-[72px] flex-col items-center gap-2 rounded-full px-5 py-3 text-[11px] font-medium transition-all duration-300 ${
                active
                  ? "text-white"
                  : "text-white/45 hover:text-white/90"
              }`}
            >
              {active && (
                <div className="absolute inset-0 rounded-full bg-gradient-to-r from-[#8B5CF6] to-[#22D3EE]" />
              )}
              <Icon size={20} className="relative z-10" />
              <span className="relative z-10">{item.label}</span>
            </Link>
          )
        })}
      </nav>
    </div>
  )
}
