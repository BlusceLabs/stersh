import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createRootRoute, createRoute, createRouter, RouterProvider, Outlet, useMatchRoute } from "@tanstack/react-router";
import React from "react";
import UserProvider from "@/components/UserProvider";
import NavBar from "@/components/navbar/NavBar";
import Footer from "@/components/Footer";
import Landing from "@/app/pages/Landing";
import Home from "@/app/pages/Home";
import MovieList from "@/app/pages/MovieList";
import MovieDetail from "@/app/pages/MovieDetail";
import TVDetail from "@/app/pages/TVDetail";
import PlayerPage from "@/app/pages/PlayerPage";
import SearchPage from "@/app/pages/SearchPage";
import Login from "@/app/pages/Login";
import Register from "@/app/pages/Register";
import Profile from "@/app/pages/Profile";
import Downloads from "@/app/pages/Downloads";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,
      gcTime: 10 * 60 * 1000,
      retry: 2,
      refetchOnWindowFocus: false,
    },
  },
});

const Layout = () => {
  const matchRoute = useMatchRoute();
  const isLanding = matchRoute({ to: "/" }) !== false;
  const isWatchPage = matchRoute({ to: "/watch/$mediaType/$id" }) !== false || 
                     matchRoute({ to: "/player/$mediaType/$id" }) !== false;
  
  if (isLanding) {
    return (
      <QueryClientProvider client={queryClient}>
        <UserProvider>
          <div className="min-h-screen bg-black text-white">
            <Outlet />
          </div>
        </UserProvider>
      </QueryClientProvider>
    );
  }

  // Watch page - no navbar or footer
  if (isWatchPage) {
    return (
      <QueryClientProvider client={queryClient}>
        <UserProvider>
          <div className="min-h-screen bg-black text-white">
            <Outlet />
          </div>
        </UserProvider>
      </QueryClientProvider>
    );
  }
  
  return (
    <QueryClientProvider client={queryClient}>
      <UserProvider>
        <div className="min-h-screen flex flex-col bg-black text-white">
          <NavBar />
          <main className="flex-1 pt-16">
            <Outlet />
          </main>
          <Footer />
        </div>
      </UserProvider>
    </QueryClientProvider>
  );
};

const rootRoute = createRootRoute({
  component: Layout,
});

const landingRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/",
  component: Landing,
});

const routes = [
  createRoute({ getParentRoute: () => rootRoute, path: "/home", component: Home }),
  createRoute({ getParentRoute: () => rootRoute, path: "/movies", component: () => <MovieList type="movie" /> }),
  createRoute({ getParentRoute: () => rootRoute, path: "/tv", component: () => <MovieList type="tv" /> }),
  createRoute({ getParentRoute: () => rootRoute, path: "/details/movie/$id", component: MovieDetail }),
  createRoute({ getParentRoute: () => rootRoute, path: "/details/tv/$id", component: TVDetail }),
  createRoute({ getParentRoute: () => rootRoute, path: "/movie/$id", component: MovieDetail }),
  createRoute({ getParentRoute: () => rootRoute, path: "/tv/$id", component: TVDetail }),
  createRoute({ getParentRoute: () => rootRoute, path: "/watch/$mediaType/$id", component: PlayerPage }),
  createRoute({ getParentRoute: () => rootRoute, path: "/player/$mediaType/$id", component: PlayerPage }),
  createRoute({ getParentRoute: () => rootRoute, path: "/search", component: SearchPage }),
  createRoute({ getParentRoute: () => rootRoute, path: "/login", component: Login }),
  createRoute({ getParentRoute: () => rootRoute, path: "/signup", component: Register }),
  createRoute({ getParentRoute: () => rootRoute, path: "/profile", component: Profile }),
  createRoute({ getParentRoute: () => rootRoute, path: "/downloads", component: Downloads }),
];

const routeTree = rootRoute.addChildren([landingRoute, ...routes]);
const router = createRouter({ routeTree });

export default function App() {
  return <RouterProvider router={router} />;
}