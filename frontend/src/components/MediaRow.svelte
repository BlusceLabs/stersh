<script lang="ts">
  import { api } from '../lib/api';
  import MovieCard from './MovieCard.svelte';
  import RowSkeleton from './skeletons/RowSkeleton.svelte';

  interface MediaItem {
    id: number;
    title?: string;
    name?: string;
    poster_path: string | null;
    backdrop_path?: string | null;
    vote_average?: number;
    vote_count?: number;
    release_date?: string;
    first_air_date?: string;
    media_type?: 'movie' | 'tv' | string;
    production_companies?: { name: string }[];
    credits?: { crew?: { job: string; name: string }[] };
    _progress?: number;
    _season?: number;
    _episode?: number;
    _startTime?: number;
  }

  let {
    title = '',
    items = [] as MediaItem[],
    endpoint = '',
    showViewAll = true,
    viewAllHref = '/search',
    showSkeleton = false,
    skeletonCount = 7,
  }: {
    title?: string;
    items?: MediaItem[];
    endpoint?: string;
    showViewAll?: boolean;
    viewAllHref?: string;
    showSkeleton?: boolean;
    skeletonCount?: number;
  } = $props();

  let fetchedItems = $state<MediaItem[]>([]);
  let fetching = $state(false);

  let displayItems = $derived(items.length > 0 ? items : fetchedItems);
  let isLoading = $derived(showSkeleton || (fetching && displayItems.length === 0));

  $effect(() => {
    if (items.length > 0 || !endpoint) return;
    fetching = true;
    // Endpoint can be either:
    //   "trending/movie/week"        → /api/tmdb/trending/movie/week  (default, prefixed)
    //   "discover/movie?with_genres=18"  → /api/tmdb/discover/movie?with_genres=18
    // We detect the discover shape by the leading "discover/" segment.
    const url = endpoint.startsWith('discover/')
      ? `/api/tmdb/${endpoint}`
      : `/api/tmdb/${endpoint}`;
    api.get(url)
      .then((data: any) => {
        fetchedItems = (data?.results || []).filter((item: MediaItem) => item.backdrop_path || item.poster_path).map((item: MediaItem) => ({
          ...item,
          media_type: item.media_type || (endpoint.includes('/tv') ? 'tv' : 'movie'),
        }));
      })
      .catch(() => {})
      .finally(() => { fetching = false; });
  });

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

{#if isLoading}
  <section class="mb-6 sm:mb-8">
    <div class="flex items-end justify-between mb-3 px-4 md:px-6">
      <h2 class="text-lg md:text-xl font-bold text-ink">{title}</h2>
    </div>
    <div class="px-4 md:px-6">
      <RowSkeleton count={skeletonCount} />
    </div>
  </section>
{:else if displayItems.length > 0}
  <section class="mb-6 sm:mb-8 group/section">
    <div class="flex items-end justify-between mb-3 px-4 md:px-6">
      <h2 class="text-lg md:text-xl font-bold text-ink">
        {title}
      </h2>
      {#if showViewAll}
        <a
          href={viewAllHref}
          class="text-sm text-yt-blue font-medium hover:text-yt-blue/80 flex items-center gap-1"
        >
          <svg viewBox="0 0 24 24" class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <path stroke-linecap="round" stroke-linejoin="round" d="M5 15l7-7 7 7" />
          </svg>
          Show more
        </a>
      {/if}
    </div>

    <div class="relative group/track px-4 md:px-6">
      {#if canScrollLeft}
        <button
          type="button"
          onclick={() => scrollSide('left')}
          aria-label={`Scroll ${title} left`}
          class="hidden md:flex absolute left-4 top-1/3 -translate-y-1/2 z-30 w-10 h-10 rounded-full bg-base-1/90 text-ink items-center justify-center hover:bg-base-1"
        >
          <svg viewBox="0 0 24 24" class="w-6 h-6" fill="currentColor" aria-hidden="true">
            <path d="M15 6l-6 6 6 6V6z" />
          </svg>
        </button>
      {/if}

      {#if canScrollRight}
        <button
          type="button"
          onclick={() => scrollSide('right')}
          aria-label={`Scroll ${title} right`}
          class="hidden md:flex absolute right-4 top-1/3 -translate-y-1/2 z-30 w-10 h-10 rounded-full bg-base-1/90 text-ink items-center justify-center hover:bg-base-1"
        >
          <svg viewBox="0 0 24 24" class="w-6 h-6" fill="currentColor" aria-hidden="true">
            <path d="M9 6v12l6-6-6-6z" />
          </svg>
        </button>
      {/if}

      <div
        bind:this={scrollEl}
        class="flex gap-4 overflow-x-auto no-scrollbar pb-1"
        role="list"
        aria-label={title}
      >
        {#each displayItems as item (item.id)}
          <div
            class="flex-shrink-0 w-[280px] sm:w-[320px] md:w-[340px]"
            role="listitem"
          >
            <MovieCard
              movie={item}
              type={item.media_type === 'tv' ? 'tv' : 'movie'}
              progress={item._progress}
              season={item._season}
              episode={item._episode}
              startTime={item._startTime}
            />
          </div>
        {/each}
      </div>
    </div>
  </section>
{/if}
