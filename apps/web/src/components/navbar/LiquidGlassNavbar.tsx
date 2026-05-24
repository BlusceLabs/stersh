import { motion } from "framer-motion"
import {
  Clapperboard,
  Compass,
  Home,
  Search,
  User2,
} from "lucide-react"

import { Link, useRouterState } from "@tanstack/react-router"

const navItems = [
  {
    icon: Home,
    label: "Home",
    href: "/home",
  },
  {
    icon: Compass,
    label: "Discover",
    href: "/discover",
  },
  {
    icon: Search,
    label: "Search",
    href: "/search",
  },
  {
    icon: Clapperboard,
    label: "Watchlist",
    href: "/watchlist",
  },
  {
    icon: User2,
    label: "Profile",
    href: "/profile",
  },
]

export function LiquidGlassNavbar() {
  const pathname = useRouterState({
    select: (state) => state.location.pathname,
  })

  return (
    <div
      className="
        pointer-events-none
        fixed
        bottom-8
        left-0
        right-0
        z-[999]
        flex
        justify-center
        px-4
      "
    >
      <motion.nav
        initial={{
          opacity: 0,
          y: 80,
        }}
        animate={{
          opacity: 1,
          y: 0,
        }}
        transition={{
          duration: 1,
          ease: [0.22, 1, 0.36, 1],
        }}
        className="
          pointer-events-auto
          relative
          overflow-hidden
          rounded-full
          border
          border-white/[0.08]
          bg-white/[0.06]
          px-4
          py-3
          shadow-[0_10px_60px_rgba(0,0,0,0.45)]
          backdrop-blur-[40px]
        "
      >
        {/* GLASS */}
        <div
          className="
            absolute
            inset-0
            bg-[linear-gradient(180deg,rgba(255,255,255,0.08),rgba(255,255,255,0.02))]
          "
        />

        {/* BLOOM */}
        <div
          className="
            absolute
            inset-0
            bg-[radial-gradient(circle_at_top,rgba(139,92,246,0.18),transparent_60%)]
          "
        />

        {/* ITEMS */}
        <div className="relative flex items-center gap-2">
          {navItems.map((item) => {
            const Icon = item.icon

            const active =
              pathname === item.href

            return (
              <Link
                key={item.href}
                to={item.href}
                className="relative"
              >
                {/* ACTIVE */}
                {active && (
                  <motion.div
                    layoutId="navbar-active"
                    transition={{
                      type: "spring",
                      stiffness: 300,
                      damping: 30,
                    }}
                    className="
                      absolute
                      inset-0
                      rounded-full
                      bg-gradient-to-r
                      from-[#8B5CF6]
                      to-[#22D3EE]
                    "
                  />
                )}

                <motion.div
                  whileHover={{
                    y: -4,
                  }}
                  whileTap={{
                    scale: 0.95,
                  }}
                  className={`
                    relative
                    z-10
                    flex
                    min-w-[72px]
                    flex-col
                    items-center
                    gap-2
                    rounded-full
                    px-5
                    py-3
                    transition-all
                    duration-300
                    ${
                      active
                        ? "text-white"
                        : "text-white/45 hover:text-white/90"
                    }
                  `}
                >
                  <Icon size={20} />

                  <span
                    className="
                      text-[11px]
                      font-medium
                      tracking-wide
                    "
                  >
                    {item.label}
                  </span>
                </motion.div>
              </Link>
            )
          })}
        </div>
      </motion.nav>
    </div>
  )
}
