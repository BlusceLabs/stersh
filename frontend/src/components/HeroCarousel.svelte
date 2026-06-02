<script lang="ts">
  import { onDestroy, onMount } from 'svelte';
  import { api } from '../lib/api';

  interface Item {
    id: number;
    title?: string;
    name?: string;
    overview: string;
    backdrop_path: string;
    vote_average: number;
    release_date?: string;
    first_air_date?: string;
    media_type?: string;
  }

  const ROTATE_MS = 6500;
  const FADE_MS = 700;

  let items = $state<Item[]>([]);
  let idx = $state(0);
  let hovering = $state(false);
  let loaded = $state(false);
  let containerEl: HTMLElement | undefined;
  let inView = $state(true);
  let progress = $state(0);

  onMount(() => {
    if (!containerEl || typeof IntersectionObserver === 'undefined') return;
    const io = new IntersectionObserver(
      ([entry]) => { inView = entry.isIntersecting; },
      { threshold: 0.25 },
    );
    io.observe(containerEl);
    return () => io.disconnect();
  });

  onDestroy(() => {
    inView = false;
  });

  let loadAbort: AbortController | null = null;

  $effect(() => {
    loadAbort?.abort();
    loadAbort = new AbortController();
    const signal = loadAbort.signal;
    (async () => {
      try {
        const [movies, tv] = await Promise.all([
          api.get('/api/tmdb/trending/movie/week'),
          api.get('/api/tmdb/trending/tv/week'),
        ]);
        if (signal.aborted) return;
        const all = [
          ...((movies?.results || []).filter((m: Item) => m.backdrop_path)),
          ...((tv?.results || []).filter((t: Item) => t.backdrop_path)),
        ];
        items = all.slice(0, 7);
        loaded = true;
      } catch (e) {
        if (signal.aborted) return;
        console.error('hero load error:', e);
        loaded = true;
      }
    })();
    return () => loadAbort?.abort();
  });

  $effect(() => {
    if (hovering || items.length < 2 || !inView) {
      progress = 0;
      return;
    }
    progress = 0;
    const start = performance.now();
    let raf = 0;
    const tick = (now: number) => {
      const elapsed = now - start;
      progress = Math.min(elapsed / ROTATE_MS, 1);
      if (progress < 1) {
        raf = requestAnimationFrame(tick);
      } else {
        idx = (idx + 1) % items.length;
      }
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  });

  function go(i: number) { idx = i; }
  function next() { idx = (idx + 1) % items.length; }
  function prev() { idx = (idx - 1 + items.length) % items.length; }

  function onKey(e: KeyboardEvent) {
    if (!items.length) return;
    if (e.key === 'ArrowRight') { e.preventDefault(); next(); }
    else if (e.key === 'ArrowLeft') { e.preventDefault(); prev(); }
  }

  function meta(m: Item) {
    return {
      id: m.id,
      title: m.title || m.name || 'Untitled Feature',
      overview: m.overview || 'No description available.',
      backdrop: `https://image.tmdb.org/t/p/original${m.backdrop_path}`,
      rating: m.vote_average || 0,
      year: (m.release_date || m.first_air_date || '').slice(0, 4),
      type: m.title ? 'movie' : 'tv',
    };
  }
</script>

<!--
  WAI-ARIA Carousel Pattern: the slide container is a focusable region
  (tabindex=0) with keyboard navigation (ArrowLeft/ArrowRight). The
  svelte-ignore comments below acknowledge the WAI-ARIA Authoring
  Practices carousel pattern, which svelte's a11y rules do not yet
  recognize. See: https://www.w3.org/WAI/ARIA/apg/patterns/carousel/
-->
<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
<div
  bind:this={containerEl}
  class="relative w-full h-[80vh] min-h-[550px] max-h-[850px] bg-surface-0 overflow-hidden group select-none"
  onmouseenter={() => hovering = true}
  onmouseleave={() => hovering = false}
  onkeydown={onKey}
  tabindex="0"
  role="group"
  aria-roledescription="carousel"
  aria-label="Featured content slider"
>
  {#if !loaded}
    <div class="absolute inset-0 bg-surface-0">
      <div class="absolute inset-0 bg-gradient-to-r from-surface-1 via-surface-2/40 to-surface-1 animate-pulse"></div>
      <div class="absolute bottom-16 left-8 md:left-16 lg:left-24 space-y-4 max-w-2xl">
        <div class="flex gap-2 mb-4">
          <div class="skeleton h-6 rounded w-16"></div>
          <div class="skeleton h-6 rounded w-20"></div>
        </div>
        <div class="skeleton h-12 rounded w-3/4"></div>
        <div class="skeleton h-12 rounded w-1/2"></div>
        <div class="space-y-2 pt-2">
          <div class="skeleton h-4 rounded w-full"></div>
          <div class="skeleton h-4 rounded w-5/6"></div>
        </div>
      </div>
    </div>
  {:else if items.length === 0}
    <div class="absolute inset-0 flex flex-col items-center justify-center bg-surface-0 text-ink-muted">
      <div class="w-16 h-16 mb-4 rounded-2xl bg-surface-1 border border-white/[0.06] flex items-center justify-center">
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.25" stroke="currentColor" class="w-7 h-7 text-ink-faint" aria-hidden="true">
          <path stroke-linecap="round" stroke-linejoin="round" d="M3.375 19.5h17.25m-17.25 0a1.125 1.125 0 0 1-1.125-1.125M3.375 19.5h7.5c.621 0 1.125-.504 1.125-1.125m-9.75 0V5.625m0 12.75v-1.5c0-.621.504-1.125 1.125-1.125m18.375 2.625V5.625m0 12.75c0 .621-.504 1.125-1.125 1.125m1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125m0 3.75h-7.5A1.125 1.125 0 0 1 12 18.375m9.75-12.75c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125m19.5 0v1.5c0 .621-.504 1.125-1.125 1.125M2.25 5.625v1.5c0 .621.504 1.125 1.125 1.125m0 0h17.25m-17.25 0h7.5c.621 0 1.125.504 1.125 1.125M3.375 8.25c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125m17.25-3.75h-7.5c-.621 0-1.125.504-1.125 1.125m8.625-1.125c.621 0 1.125.504 1.125 1.125v1.5c0 .621-.504 1.125-1.125 1.125m-17.25 0h7.5m-7.5 0c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125M12 10.875v-1.5m0 1.5c0 .621-.504 1.125-1.125 1.125M12 10.875c0 .621.504 1.125 1.125 1.125m-2.25 0c.621 0 1.125.504 1.125 1.125M13.125 12h7.5m-7.5 0c-.621 0-1.125.504-1.125 1.125M20.625 12c.621 0 1.125.504 1.125 1.125v1.5c0 .621-.504 1.125-1.125 1.125m-17.25 0h7.5M12 14.625v-1.5" />
        </svg>
      </div>
      <p class="text-sm font-bold tracking-wider uppercase text-ink-muted">No featured content available</p>
    </div>
  {:else}
    {#each items as item, i (item.id)}
      {@const m = meta(item)}
      <a
        href={`/watch/${m.type}/${m.id}`}
        class="absolute inset-0 block cursor-pointer focus:outline-none"
        aria-label={`Watch ${m.title}`}
        aria-hidden={i !== idx}
        tabindex={i === idx ? 0 : -1}
        style="opacity: {i === idx ? 1 : 0}; transition: opacity {FADE_MS}ms var(--ease-exo-out);"
      >
        <div
          class="absolute inset-0"
          style="transform: {i === idx ? 'scale(1)' : 'scale(1.05)'}; transition: transform 9s linear;"
          aria-hidden="true"
        >
          <img
            src={m.backdrop}
            alt=""
            class="w-full h-full object-cover brightness-[0.45]"
            loading={i === 0 ? 'eager' : 'lazy'}
          />
        </div>
        <div class="absolute inset-0 bg-gradient-to-t from-surface-0 via-surface-0/40 to-transparent" aria-hidden="true"></div>
        <div class="absolute inset-0 bg-gradient-to-r from-surface-0/95 via-surface-0/30 to-transparent" aria-hidden="true"></div>
        <div class="absolute inset-0 bg-gradient-to-b from-surface-0/20 via-transparent to-surface-0" aria-hidden="true"></div>
      </a>
    {/each}

    {@const cur = meta(items[idx])}
    <div class="absolute bottom-0 left-0 right-0 p-8 md:p-16 lg:px-24 pb-20 md:pb-28 z-10 pointer-events-none">
      <div class="max-w-3xl pointer-events-auto" aria-live="polite">

        <div class="flex items-center gap-2 text-xs md:text-sm font-bold mb-4 text-ink-secondary">
          {#if cur.rating > 0}
            <span class="flex items-center gap-1.5 glass-strong text-accent-warm px-2.5 py-1 rounded-md">
              <svg class="w-3.5 h-3.5 fill-accent-warm" viewBox="0 0 20 20" aria-hidden="true">
                <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/>
              </svg>
              {cur.rating.toFixed(1)}
            </span>
          {/if}
          {#if cur.year}
            <span class="glass-strong text-ink-secondary px-2.5 py-1 rounded-md">{cur.year}</span>
          {/if}
          <span class="uppercase text-[11px] tracking-wider px-2.5 py-1 rounded-md bg-brand-red/[0.08] border border-brand-red/25 text-brand-red">
            {cur.type === 'movie' ? 'Movie' : 'TV Series'}
          </span>
        </div>

        <h2 class="text-4xl md:text-6xl font-display font-black text-ink mb-4 tracking-tighter leading-[1.05] text-cinematic-lg">
          {cur.title}
        </h2>

        <p class="text-ink-secondary text-sm md:text-base leading-relaxed line-clamp-3 mb-8 max-w-2xl">
          {cur.overview}
        </p>

        <div class="flex flex-wrap items-center gap-3">
          <a
            href={`/watch/${cur.type}/${cur.id}`}
            class="inline-flex items-center gap-2.5 px-7 py-3.5 bg-brand-gradient-cta text-white font-bold rounded-xl hover:brightness-110 active:scale-95 transition-all duration-300 ease-exo-out shadow-glow-red"
          >
            <svg class="w-5 h-5 fill-white" viewBox="0 0 20 20" aria-hidden="true">
              <path d="M6.423 4.167A1 1 0 005 5.035v9.93a1 1 0 001.423.868l8.5-4.965a1 1 0 000-1.736l-8.5-4.965z"/>
            </svg>
            Play Now
          </a>
          <a
            href={`/${cur.type}/${cur.id}`}
            class="inline-flex items-center gap-2.5 px-6 py-3.5 glass-strong text-ink font-semibold rounded-xl hover:bg-white/[0.08] transition-all duration-300 ease-exo-out active:scale-95"
          >
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-4 h-4" aria-hidden="true">
              <path stroke-linecap="round" stroke-linejoin="round" d="m11.25 11.25.041-.02a.75.75 0 0 1 1.063.852l-.708 2.836a.75.75 0 0 0 1.063.853l.041-.021M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9-3.75h.008v.008H12V8.25Z" />
            </svg>
            More Info
          </a>
        </div>
      </div>
    </div>

    <div class="absolute bottom-6 right-6 md:right-12 lg:right-20 z-20 flex items-center gap-2 glass-strong px-3 py-2.5 rounded-full" role="tablist" aria-label="Featured content slides">
      {#each items as _, mIndex (mIndex)}
        <button
          type="button"
          onclick={() => go(mIndex)}
          role="tab"
          aria-label={`Go to slide ${mIndex + 1} of ${items.length}`}
          aria-current={mIndex === idx ? 'true' : undefined}
          class="group/dot relative h-1.5 rounded-full overflow-hidden transition-all duration-500 ease-exo-out cursor-pointer
            {mIndex === idx ? 'w-12 bg-white/20' : 'w-1.5 bg-white/30 hover:bg-white/50'}"
        >
          {#if mIndex === idx}
            <span
              class="absolute inset-y-0 left-0 bg-brand-gradient-cta rounded-full"
              style="width: {progress * 100}%; transition: width 100ms linear;"
              aria-hidden="true"
            ></span>
          {/if}
        </button>
      {/each}
    </div>

    <button
      type="button"
      onclick={prev}
      aria-label="Previous featured slide"
      class="absolute left-4 md:left-8 top-1/2 -translate-y-1/2 z-20 w-12 h-12 rounded-full glass-strong text-ink hover:bg-white/[0.08] flex items-center justify-center transition-all duration-300 ease-exo-out hover:scale-110 active:scale-95
        {hovering ? 'opacity-100 translate-x-0' : 'opacity-0 -translate-x-4'}"
    >
      <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24" aria-hidden="true">
        <path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7"/>
      </svg>
    </button>

    <button
      type="button"
      onclick={next}
      aria-label="Next featured slide"
      class="absolute right-4 md:right-8 top-1/2 -translate-y-1/2 z-20 w-12 h-12 rounded-full glass-strong text-ink hover:bg-white/[0.08] flex items-center justify-center transition-all duration-300 ease-exo-out hover:scale-110 active:scale-95
        {hovering ? 'opacity-100 translate-x-0' : 'opacity-0 translate-x-4'}"
    >
      <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24" aria-hidden="true">
        <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7"/>
      </svg>
    </button>
  {/if}
</div>
