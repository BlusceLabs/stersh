import { createRoute } from "@tanstack/react-router"
import { lazy, Suspense } from "react"

import { Route as rootRoute } from "../../__root"
import { DetailsSkeleton } from "@/components/shared/LoadingSkeleton"

const Page = lazy(() => import("@/pages/details/DetailsPage"))

function LazyPage() {
  return (
    <Suspense fallback={<DetailsSkeleton />}>
      <Page />
    </Suspense>
  )
}

export const Route = createRoute({
  getParentRoute: () => rootRoute,
  path: "/details/$type/$slug",
  component: LazyPage,
})
