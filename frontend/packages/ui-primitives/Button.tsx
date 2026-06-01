/** @jsxImportSource react */
// src/components/Button.tsx
import type { ComponentPropsWithoutRef, ReactNode } from "react"
import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

/**
 * Clean Tailwind Utility Merging Engine
 * Prevents class collision bugs by ensuring the last declared rule always wins.
 */
function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export interface ButtonProps extends ComponentPropsWithoutRef<"button"> {
  children: ReactNode
  variant?: "primary" | "secondary" | "ghost"
  size?: "sm" | "md" | "lg"
}

export function Button({
  children,
  variant = "primary",
  size = "md",
  onClick,
  className,
  type = "button", // Explicit default type prevents accidental form submission bugs
  ...props
}: ButtonProps) {
  
  // Base structural classes matched exactly to your design language
  const baseStyles = "inline-flex items-center justify-center rounded-xl font-semibold transition-all duration-300 ease-exo-out active:scale-[0.98] select-none outline-none focus-visible:ring-2 focus-visible:ring-[#8B5CF6]/50 cursor-pointer"

  const variantStyles = {
    primary:
      "bg-gradient-to-r from-[#8B5CF6] via-[#7C3AED] to-[#22D3EE] text-white shadow-lg shadow-[#8B5CF6]/10 hover:shadow-[#8B5CF6]/20 hover:scale-[1.03] hover:brightness-110",
    secondary:
      "border border-zinc-800 bg-[#1a2332]/50 backdrop-blur-sm text-zinc-200 hover:bg-[#1a2332] hover:text-white hover:border-zinc-700",
    ghost: 
      "text-zinc-400 hover:text-white hover:bg-zinc-900/50",
  }

  const sizeStyles = {
    sm: "px-4 py-2 text-xs tracking-wide uppercase",
    md: "px-5 py-2.5 text-sm",
    lg: "px-7 py-3.5 text-base",
  }

  return (
    <button
      type={type}
      onClick={onClick}
      className={cn(baseStyles, variantStyles[variant], sizeStyles[size], className)}
      {...props}
    >
      {children}
    </button>
  )
}