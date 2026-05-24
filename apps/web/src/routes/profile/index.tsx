import { createRoute } from "@tanstack/react-router"
import { lazy, Suspense } from "react"

import { Route as rootRoute } from "../__root"
import { HomeSkeleton } from "@/components/shared/LoadingSkeleton"

const Page = lazy(() => import("@/pages/profile/ProfilePage"))

function LazyPage() {
  return (
    <Suspense fallback={<HomeSkeleton />}>
      <Page />
    </Suspense>
  )
}

export const Route = createRoute({
  getParentRoute: () => rootRoute,
  path: "/profile",
  component: LazyPage,
})
