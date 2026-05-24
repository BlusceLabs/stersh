import { Link } from "@tanstack/react-router"
import { Home } from "lucide-react"

import { Button } from "@/components/ui/button"

export default function NotFoundPage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-background text-foreground">
      <div className="text-center">
        <h1 className="text-9xl font-bold text-primary">404</h1>
        <h2 className="mt-4 text-3xl font-semibold">Page Not Found</h2>
        <p className="mt-4 text-lg text-muted-foreground">
          The page you're looking for doesn't exist.
        </p>
        <Link to="/">
          <Button className="mt-8 rounded-full gap-2 px-8">
            <Home size={18} />
            Back to Home
          </Button>
        </Link>
      </div>
    </main>
  )
}
