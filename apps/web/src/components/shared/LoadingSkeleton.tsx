function SkeletonBlock({ className = "" }: { className?: string }) {
  return (
    <div
      className={`animate-pulse rounded-lg bg-white/[0.06] ${className}`}
    />
  )
}

export function HomeSkeleton() {
  return (
    <main className="min-h-screen bg-[#070B14]">
      {/* Hero skeleton */}
      <section className="relative h-screen overflow-hidden">
        <SkeletonBlock className="absolute inset-0 h-full w-full rounded-none" />

        <div className="absolute inset-0 bg-gradient-to-r from-[#070B14] via-[#070B14]/50 to-transparent" />
        <div className="absolute inset-0 bg-gradient-to-t from-[#070B14] via-transparent to-transparent" />

        <div className="relative z-20 flex h-full items-end px-6 pb-44 md:px-16">
          <div className="max-w-2xl">
            {/* Logo skeleton */}
            <SkeletonBlock className="mb-8 h-28 w-[320px]" />
            {/* Overview skeleton */}
            <SkeletonBlock className="mb-3 h-5 w-full" />
            <SkeletonBlock className="mb-3 h-5 w-3/4" />
            <SkeletonBlock className="h-5 w-1/2" />
            {/* Buttons skeleton */}
            <div className="mt-10 flex gap-4">
              <SkeletonBlock className="h-14 w-40 rounded-full" />
              <SkeletonBlock className="h-14 w-36 rounded-full" />
            </div>
          </div>
        </div>
      </section>

      {/* Rows skeleton */}
      <section className="relative z-20 -mt-28 space-y-14 pb-40">
        {[1, 2, 3].map((row) => (
          <div key={row} className="px-6 md:px-16">
            <SkeletonBlock className="mb-6 h-6 w-48" />
            <div className="flex gap-4">
              {[1, 2, 3, 4, 5, 6].map((card) => (
                <SkeletonBlock
                  key={card}
                  className="aspect-[2/3] w-[180px] shrink-0 rounded-2xl"
                />
              ))}
            </div>
          </div>
        ))}
      </section>
    </main>
  )
}

export function DetailsSkeleton() {
  return (
    <main className="min-h-screen bg-[#070B14]">
      {/* Backdrop skeleton */}
      <div className="absolute inset-0">
        <SkeletonBlock className="h-full w-full rounded-none" />
      </div>

      {/* Content skeleton */}
      <section className="relative z-20 flex min-h-screen items-end px-6 pb-40 pt-32 md:px-16">
        <div className="grid w-full gap-12 lg:grid-cols-[320px_1fr]">
          {/* Poster skeleton */}
          <SkeletonBlock className="aspect-[2/3] w-full rounded-[32px]" />

          {/* Info skeleton */}
          <div className="max-w-3xl">
            <SkeletonBlock className="mb-8 h-20 w-[320px]" />

            {/* Meta chips */}
            <div className="mb-8 mt-6 flex flex-wrap items-center gap-4">
              <SkeletonBlock className="h-6 w-16 rounded-full" />
              <SkeletonBlock className="h-6 w-20 rounded-full" />
              <SkeletonBlock className="h-6 w-16 rounded-full" />
              <SkeletonBlock className="h-6 w-40 rounded-full" />
            </div>

            {/* Overview lines */}
            <SkeletonBlock className="mb-3 h-5 w-full" />
            <SkeletonBlock className="mb-3 h-5 w-5/6" />
            <SkeletonBlock className="mb-3 h-5 w-3/4" />
            <SkeletonBlock className="h-5 w-2/3" />

            {/* Buttons */}
            <div className="mt-12 flex gap-4">
              <SkeletonBlock className="h-14 w-40 rounded-full" />
              <SkeletonBlock className="h-14 w-36 rounded-full" />
            </div>
          </div>
        </div>
      </section>
    </main>
  )
}

export function WatchSkeleton() {
  return (
    <main className="flex h-screen items-center justify-center bg-black">
      <div className="text-center">
        <div className="mx-auto mb-6 h-16 w-16 animate-spin rounded-full border-2 border-white/10 border-t-[#8B5CF6]" />
        <p className="text-sm text-white/40">Loading stream...</p>
      </div>
    </main>
  )
}
