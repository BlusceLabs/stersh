import React from "react"
import ReactDOM from "react-dom/client"

import {
  RouterProvider,
  createRouter,
} from "@tanstack/react-router"

import { routeTree } from "./routeTree.gen"

import "./styles/globals.css"

const router = createRouter({
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  routeTree: routeTree as any,
})

const root = ReactDOM.createRoot(
  document.getElementById("root")!
)

root.render(
  <React.StrictMode>
    <RouterProvider router={router} />
  </React.StrictMode>
)

// Webpack HMR
if (module.hot) {
  module.hot.accept("./routeTree.gen", () => {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const { routeTree: newRouteTree } = require("./routeTree.gen") as typeof import("./routeTree.gen")
    router.update({ routeTree: newRouteTree })
    root.render(
      <React.StrictMode>
        <RouterProvider router={router} />
      </React.StrictMode>
    )
  })
}
