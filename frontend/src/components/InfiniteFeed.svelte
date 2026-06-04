<script lang="ts">
  /**
   * Infinite-scrolling vertical feed of MediaRow shelves.
   *
   * - Renders an initial set of shelves immediately (from `initialShelves`)
   * - Watches a sentinel at the bottom; when it scrolls into view,
   *   dynamically appends the next shelf from `pool`
   * - Tracks which pool entries have already been used so the same shelf
   *   never appears twice
   * - Stops once the pool is exhausted (renders an "end of feed" notice)
   */
  import { onMount } from 'svelte';
  import MediaRow from './MediaRow.svelte';

  interface Shelf {
    title: string;
    endpoint: string;
    viewAllHref?: string;
  }

  let {
    initialShelves = [] as Shelf[],
    pool = [] as Shelf[],
    sentinelDistance = '600px',
  }: {
    initialShelves?: Shelf[];
    pool?: Shelf[];
    sentinelDistance?: string;
  } = $props();

  let mounted = $state<Shelf[]>([...initialShelves]);
  let cursor = $state(0);
  let exhausted = $state(false);
  let sentinel: HTMLDivElement | undefined = $state();
  let observer: IntersectionObserver | null = null;

  function nextShelf(): Shelf | null {
    if (cursor >= pool.length) return null;
    return pool[cursor++];
  }

  function loadMore() {
    if (exhausted) return;
    const shelf = nextShelf();
    if (!shelf) { exhausted = true; return; }
    mounted = [...mounted, shelf];
  }

  onMount(() => {
    if (!sentinel) return;
    observer = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          if (e.isIntersecting) loadMore();
        }
      },
      { rootMargin: `0px 0px ${sentinelDistance} 0px` },
    );
    observer.observe(sentinel);
    return () => observer?.disconnect();
  });
</script>

{#each mounted as shelf, i (i + '-' + shelf.endpoint)}
  <MediaRow
    title={shelf.title}
    endpoint={shelf.endpoint}
    viewAllHref={shelf.viewAllHref ?? '/trending'}
    showViewAll={true}
  />
{/each}

<div bind:this={sentinel} class="h-4" aria-hidden="true"></div>

{#if !exhausted && cursor < pool.length}
  <div class="flex justify-center py-6">
    <button
      type="button"
      onclick={loadMore}
      class="h-9 px-5 bg-base-2 text-ink rounded-full text-sm font-medium hover:bg-base-3 border border-white/10"
    >
      Load more
    </button>
  </div>
{:else if exhausted}
  <div class="flex flex-col items-center justify-center py-10 text-ink-muted">
    <svg viewBox="0 0 24 24" class="w-6 h-6 mb-2" fill="currentColor" aria-hidden="true">
      <path d="M5 12h14M12 5l-7 7 7 7" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" />
    </svg>
    <p class="text-sm">That's all for now — try a new filter or refresh to reload.</p>
  </div>
{/if}
