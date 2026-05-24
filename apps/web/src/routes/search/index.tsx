import { createRoute } from "@tanstack/react-router"
import { lazy, Suspense } from "react"

import { Route as rootRoute } from "../__root"

const Page = lazy(() => import("@/pages/search/SearchPage"))

function LazyPage() {
  return (
    <Suspense>
      <Page />
    </Suspense>
  )
}

export const Route = createRoute({
  getParentRoute: () => rootRoute,
  path: "/search",
  component: LazyPage,
})
