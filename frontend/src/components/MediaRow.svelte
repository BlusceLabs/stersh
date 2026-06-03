<script lang="ts">
  import MovieCard from './MovieCard.svelte';

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
  let scrollProgress = $state(0);
  let hoveredIndex = $state(-1);

  function updateScrollState() {
    if (!scrollEl) return;
    canScrollLeft = scrollEl.scrollLeft > 4;
    canScrollRight = scrollEl.scrollLeft + scrollEl.clientWidth < scrollEl.scrollWidth - 4;
    const maxScroll = scrollEl.scrollWidth - scrollEl.clientWidth;
    scrollProgress = maxScroll > 0 ? scrollEl.scrollLeft / maxScroll : 0;
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
  <section class="mb-8 sm:mb-10 relative select-none group/section">
    <div class="flex items-end justify-between mb-4 px-4 md:px-12">
      <h2 class="text-lg md:text-2xl font-black text-ink tracking-tight">
        {title}
      </h2>
      <div class="flex items-center gap-3">
        {#if canScrollLeft || canScrollRight}
          <div class="hidden md:flex items-center gap-1">
            <button
              type="button"
              onclick={() => scrollSide('left')}
              disabled={!canScrollLeft}
              class="w-7 h-7 rounded-full flex items-center justify-center transition-all duration-200
                {canScrollLeft ? 'text-ink-muted hover:text-ink hover:bg-white/[0.06]' : 'text-ink-faint cursor-default'}"
              aria-label="Scroll left"
            >
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7"/></svg>
            </button>
            <button
              type="button"
              onclick={() => scrollSide('right')}
              disabled={!canScrollRight}
              class="w-7 h-7 rounded-full flex items-center justify-center transition-all duration-200
                {canScrollRight ? 'text-ink-muted hover:text-ink hover:bg-white/[0.06]' : 'text-ink-faint cursor-default'}"
              aria-label="Scroll right"
            >
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7"/></svg>
            </button>
          </div>
          <div class="hidden md:block w-12 h-0.5 rounded-full bg-surface-2 overflow-hidden">
            <div class="h-full bg-brand-gradient-cta rounded-full transition-all duration-300 ease-exo-out" style="width: {scrollProgress * 100}%"></div>
          </div>
        {/if}
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
    </div>

    <div class="relative px-4 md:px-12 group/track">
      {#if canScrollLeft && !showSkeleton}
        <button
          type="button"
          onclick={() => scrollSide('left')}
          aria-label={`Scroll ${title} left`}
          class="absolute left-1 md:left-4 top-1/2 -translate-y-1/2 z-30 w-10 h-10 sm:w-11 sm:h-11 rounded-full glass-strong text-ink hover:bg-brand-red/15 hover:text-ink flex items-center justify-center opacity-0 group-hover/track:opacity-100 focus-visible:opacity-100 transition-all duration-300 ease-exo-out transform -translate-x-2 group-hover/track:translate-x-0 shadow-4 hover:scale-110 active:scale-95"
        >
          <svg class="w-5 h-5 transition-transform duration-200" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24" aria-hidden="true">
            <path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7"/>
          </svg>
        </button>
      {/if}

      {#if canScrollRight && !showSkeleton}
        <button
          type="button"
          onclick={() => scrollSide('right')}
          aria-label={`Scroll ${title} right`}
          class="absolute right-1 md:right-4 top-1/2 -translate-y-1/2 z-30 w-10 h-10 sm:w-11 sm:h-11 rounded-full glass-strong text-ink hover:bg-brand-red/15 hover:text-ink flex items-center justify-center opacity-0 group-hover/track:opacity-100 focus-visible:opacity-100 transition-all duration-300 ease-exo-out transform translate-x-2 group-hover/track:translate-x-0 shadow-4 hover:scale-110 active:scale-95"
        >
          <svg class="w-5 h-5 transition-transform duration-200" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24" aria-hidden="true">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7"/>
          </svg>
        </button>
      {/if}

      <div class="absolute inset-y-0 left-0 w-12 md:w-20 bg-gradient-to-r from-surface-0 via-surface-0/80 to-transparent z-20 pointer-events-none" aria-hidden="true"></div>
      <div class="absolute inset-y-0 right-0 w-12 md:w-20 bg-gradient-to-l from-surface-0 via-surface-0/80 to-transparent z-20 pointer-events-none" aria-hidden="true"></div>

      <div
        bind:this={scrollEl}
        class="flex gap-3.5 sm:gap-4 overflow-x-auto scroll-x-clean pb-4 pt-1 snap-x snap-mandatory"
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
              onmouseenter={() => hoveredIndex = i}
              onmouseleave={() => hoveredIndex = -1}
            >
              <div
                class="transition-transform duration-500 ease-exo-out"
                style="transform: scale({hoveredIndex === i ? 1.04 : 1});"
              >
                <MovieCard movie={item} type={item.media_type === 'tv' ? 'tv' : 'movie'} />
              </div>
            </div>
          {/each}
        {/if}
      </div>

      <div class="md:hidden px-1 pt-1 flex items-center gap-1">
        {#each Array(5) as _, dotI}
          {@const dotStart = dotI / 5}
          {@const dotEnd = (dotI + 1) / 5}
          <div
            class="h-0.5 flex-1 rounded-full transition-all duration-300 ease-exo-out
              {scrollProgress >= dotStart && scrollProgress < dotEnd ? 'bg-brand-gradient-cta' : scrollProgress >= dotEnd ? 'bg-ink-muted' : 'bg-surface-2'}"
            aria-hidden="true"
          ></div>
        {/each}
      </div>
    </div>
  </section>
{/if}