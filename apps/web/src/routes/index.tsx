import { createRoute } from "@tanstack/react-router"
import { lazy, Suspense } from "react"

import { Route as parentRoute } from "./__root"

const Page = lazy(() => import("@/pages/landing/LandingPage"))

function LazyPage() {
  return (
    <Suspense>
      <Page />
    </Suspense>
  )
}

export const Route = createRoute({
  getParentRoute: () => parentRoute,
  path: "/",
  component: LazyPage,
})
