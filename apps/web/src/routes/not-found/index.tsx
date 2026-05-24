import { createRoute } from "@tanstack/react-router"

import NotFoundPage from "@/pages/not-found/NotFoundPage"
import { Route as rootRoute } from "../__root"

export const Route = createRoute({
  getParentRoute: () => rootRoute,
  path: "/not-found",
  component: NotFoundPage,
})
