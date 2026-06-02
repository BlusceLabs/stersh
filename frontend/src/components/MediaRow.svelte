<script lang="ts">
  import MovieCard from './MovieCard.svelte';

  /**
   * Generic horizontal media row.
   * Used for "Trending", "Popular", "Continue Watching", "My List", etc.
   *
   * Renders a header (label + optional "View All" link) and a horizontal
   * track with edge-fade gradients, snap scrolling, and hover-revealed
   * navigation chevrons.
   */
  interface MediaItem {
    id: number;
    title?: string;
    name?: string;
    poster_path: string | null;
    backdrop_path?: string | null;
    vote_average?: number;
    release_date?: string;
    first_air_date?: string;
    media_type?: 'movie' | 'tv' | string;
  }

  let {
    title = '',
    items = [] as MediaItem[],
    showViewAll = true,
    viewAllHref = '/search',
    showSkeleton = false,
    skeletonCount = 7,
  }: {
    title?: string;
    items?: MediaItem[];
    showViewAll?: boolean;
    viewAllHref?: string;
    showSkeleton?: boolean;
    skeletonCount?: number;
  } = $props();

  let scrollEl: HTMLDivElement | undefined = $state();
  let canScrollLeft = $state(false);
  let canScrollRight = $state(false);

  function updateScrollState() {
    if (!scrollEl) return;
    canScrollLeft = scrollEl.scrollLeft > 4;
    canScrollRight = scrollEl.scrollLeft + scrollEl.clientWidth < scrollEl.scrollWidth - 4;
  }

  function scrollSide(direction: 'left' | 'right') {
    if (!scrollEl) return;
    const scrollAmount = scrollEl.clientWidth * 0.78;
    scrollEl.scrollBy({
      left: direction === 'left' ? -scrollAmount : scrollAmount,
      behavior: 'smooth',
    });
  }

  $effect(() => {
    if (!scrollEl) return;
    updateScrollState();
    const onScroll = () => updateScrollState();
    scrollEl.addEventListener('scroll', onScroll, { passive: true });
    const onResize = () => updateScrollState();
    window.addEventListener('resize', onResize);
    return () => {
      scrollEl?.removeEventListener('scroll', onScroll);
      window.removeEventListener('resize', onResize);
    };
  });
</script>

{#if showSkeleton || items.length > 0}
  <section class="mb-8 sm:mb-10 relative select-none">
    <div class="flex items-end justify-between mb-4 px-4 md:px-12">
      <h2 class="text-lg md:text-2xl font-black text-ink tracking-tight">
        {title}
      </h2>
      {#if showViewAll && items.length > 0 && !showSkeleton}
        <a
          href={viewAllHref}
          class="text-[11px] sm:text-xs font-bold tracking-wider uppercase text-ink-muted hover:text-ink-secondary transition-colors duration-200 flex items-center gap-1 group/link"
        >
          View All
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2.5" stroke="currentColor" class="w-3 h-3 transform group-hover/link:translate-x-1 transition-transform duration-300 ease-exo-out" aria-hidden="true">
            <path stroke-linecap="round" stroke-linejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" />
          </svg>
        </a>
      {/if}
    </div>

    <div class="relative group/track px-4 md:px-12">
      {#if canScrollLeft && !showSkeleton}
        <button
          type="button"
          onclick={() => scrollSide('left')}
          aria-label={`Scroll ${title} left`}
          class="absolute left-2 md:left-6 top-1/2 -translate-y-1/2 z-30 w-10 h-10 sm:w-11 sm:h-11 rounded-full glass-strong text-ink hover:bg-brand-red/15 hover:text-ink flex items-center justify-center opacity-0 group-hover/track:opacity-100 focus-visible:opacity-100 transition-all duration-300 ease-exo-out transform -translate-x-2 group-hover/track:translate-x-0 shadow-4 hover:scale-105 active:scale-95"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24" aria-hidden="true">
            <path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7"/>
          </svg>
        </button>
      {/if}

      {#if canScrollRight && !showSkeleton}
        <button
          type="button"
          onclick={() => scrollSide('right')}
          aria-label={`Scroll ${title} right`}
          class="absolute right-2 md:right-6 top-1/2 -translate-y-1/2 z-30 w-10 h-10 sm:w-11 sm:h-11 rounded-full glass-strong text-ink hover:bg-brand-red/15 hover:text-ink flex items-center justify-center opacity-0 group-hover/track:opacity-100 focus-visible:opacity-100 transition-all duration-300 ease-exo-out transform translate-x-2 group-hover/track:translate-x-0 shadow-4 hover:scale-105 active:scale-95"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24" aria-hidden="true">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7"/>
          </svg>
        </button>
      {/if}

      <div class="absolute inset-y-0 left-0 w-12 bg-gradient-to-r from-surface-0 to-transparent z-20 pointer-events-none hidden md:block" aria-hidden="true"></div>
      <div class="absolute inset-y-0 right-0 w-12 bg-gradient-to-l from-surface-0 to-transparent z-20 pointer-events-none hidden md:block" aria-hidden="true"></div>

      <div
        bind:this={scrollEl}
        class="flex gap-4 overflow-x-auto scroll-x-clean pb-4 pt-1 snap-x snap-mandatory"
        role="list"
        aria-label={title}
      >
        {#if showSkeleton}
          {#each Array(skeletonCount) as _}
            <div class="flex-shrink-0 w-[140px] sm:w-[170px] space-y-3" role="presentation">
              <div class="skeleton aspect-[2/3] rounded-2xl border border-white/[0.04]"></div>
              <div class="space-y-2 px-1">
                <div class="skeleton h-3.5 rounded w-5/6"></div>
                <div class="skeleton h-2.5 rounded w-1/2"></div>
              </div>
            </div>
          {/each}
        {:else}
          {#each items as item, i (item.id)}
            <div
              class="flex-shrink-0 w-[140px] sm:w-[170px] snap-start rise-in"
              style="animation-delay: {Math.min(i * 40, 280)}ms"
              role="listitem"
            >
              <MovieCard movie={item} type={item.media_type === 'tv' ? 'tv' : 'movie'} />
            </div>
          {/each}
        {/if}
      </div>
    </div>
  </section>
{/if}
