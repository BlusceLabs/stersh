import { ReactNode } from "react"

interface ButtonProps {
  children: ReactNode
  variant?: "primary" | "secondary" | "ghost"
  size?: "sm" | "md" | "lg"
  onClick?: () => void
  className?: string
}

export function Button({
  children,
  variant = "primary",
  size = "md",
  onClick,
  className = "",
}: ButtonProps) {
  const base = "inline-flex items-center justify-center rounded-full font-semibold transition-all duration-300"

  const variants = {
    primary:
      "bg-gradient-to-r from-[#8B5CF6] to-[#22D3EE] text-white hover:scale-105",
    secondary:
      "border border-white/10 bg-white/5 text-white/80 hover:bg-white/10 hover:text-white",
    ghost: "text-white/60 hover:text-white hover:bg-white/5",
  }

  const sizes = {
    sm: "px-4 py-2 text-sm",
    md: "px-6 py-3 text-base",
    lg: "px-8 py-4 text-lg",
  }

  return (
    <button
      onClick={onClick}
      className={`${base} ${variants[variant]} ${sizes[size]} ${className}`}
    >
      {children}
    </button>
  )
}
