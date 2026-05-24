import {
  Outlet,
  createRootRoute,
  useMatchRoute,
} from "@tanstack/react-router"
import { lazy, Suspense } from "react"

import { ErrorBoundary } from "@/components/shared/ErrorBoundary"
import { LiquidGlassNavbar } from "@/components/navbar/LiquidGlassNavbar"

const NotFoundPage = lazy(() => import("@/pages/not-found/NotFoundPage"))

function LazyNotFound() {
  return (
    <Suspense>
      <NotFoundPage />
    </Suspense>
  )
}

export const Route = createRootRoute({
  component: RootLayout,
  notFoundComponent: LazyNotFound,
})

function RootLayout() {
  const matchRoute = useMatchRoute()
  const isLanding = matchRoute({ to: "/", fuzzy: true })
  const isWatch = matchRoute({ to: "/watch/$type/$slug" }) || matchRoute({ to: "/watch/$type/$slug/$season/$episode" })

  return (
    <ErrorBoundary>
      {!isLanding && !isWatch && <LiquidGlassNavbar />}
      <Outlet />
    </ErrorBoundary>
  )
}
