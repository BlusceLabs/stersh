import { createRoute } from "@tanstack/react-router"
import { lazy, Suspense } from "react"

import { Route as rootRoute } from "@/routes/__root"
import { HomeSkeleton } from "@/components/shared/LoadingSkeleton"

const Page = lazy(() => import("@/pages/settings/SettingsPage"))

function LazyPage() {
  return (
    <Suspense fallback={<HomeSkeleton />}>
      <Page />
    </Suspense>
  )
}

export const Route = createRoute({
  getParentRoute: () => rootRoute,
  path: "/settings",
  component: LazyPage,
})
