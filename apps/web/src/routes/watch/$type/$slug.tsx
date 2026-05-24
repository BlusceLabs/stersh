import { createRoute } from "@tanstack/react-router"
import { lazy, Suspense } from "react"

import { Route as rootRoute } from "../../__root"
import { WatchSkeleton } from "@/components/shared/LoadingSkeleton"

const Page = lazy(() => import("@/pages/watch/WatchPage"))

function LazyPage() {
  return (
    <Suspense fallback={<WatchSkeleton />}>
      <Page />
    </Suspense>
  )
}

export const Route = createRoute({
  getParentRoute: () => rootRoute,
  path: "/watch/$type/$slug",
  component: LazyPage,
})
