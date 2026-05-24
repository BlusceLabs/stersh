import { Link, useRouterState } from "@tanstack/react-router"
import { motion } from "framer-motion"
import type { LucideIcon } from "lucide-react"

interface NavItemProps {
  icon: LucideIcon
  label: string
  href: string
}

export function NavItem({ icon: Icon, label, href }: NavItemProps) {
  const pathname = useRouterState({
    select: (state) => state.location.pathname,
  })

  const active = pathname === href

  return (
    <Link to={href} className="relative">
      {active && (
        <motion.div
          layoutId="navbar-active"
          transition={{
            type: "spring",
            stiffness: 300,
            damping: 30,
          }}
          className="absolute inset-0 rounded-full bg-gradient-to-r from-[#8B5CF6] to-[#22D3EE]"
        />
      )}
      <motion.div
        whileHover={{ y: -4 }}
        whileTap={{ scale: 0.95 }}
        className={`relative z-10 flex min-w-[72px] flex-col items-center gap-2 rounded-full px-5 py-3 transition-all duration-300 ${
          active ? "text-white" : "text-white/45 hover:text-white/90"
        }`}
      >
        <Icon size={20} />
        <span className="text-[11px] font-medium tracking-wide">{label}</span>
      </motion.div>
    </Link>
  )
}
