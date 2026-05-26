<script lang="ts">
  import { api } from '../lib/api';

  interface Item {
    id: number;
    title: string;
    overview: string;
    backdrop_path: string;
    vote_average: number;
    release_date?: string;
    first_air_date?: string;
    media_type?: string;
  }

  let items = $state<Item[]>([]);
  let idx = $state(0);
  let hovering = $state(false);
  let loaded = $state(false);

  $effect(() => {
    loadItems();
  });

  async function loadItems() {
    try {
      const [movies, tv] = await Promise.all([
        api.get('/tmdb/trending/movie/week'),
        api.get('/tmdb/trending/tv/week'),
      ]);
      const all = [
        ...((movies?.results || []).filter((m: Item) => m.backdrop_path)),
        ...((tv?.results || []).filter((t: Item) => t.backdrop_path)),
      ];
      items = all.slice(0, 7);
      loaded = true;
    } catch (e) {
      console.error('hero load error:', e);
      loaded = true;
    }
  }

  $effect(() => {
    if (hovering || items.length < 2) return;
    const t = setInterval(() => idx = (idx + 1) % items.length, 6000);
    return () => clearInterval(t);
  });

  function go(i: number) { idx = i; }
  function next() { idx = (idx + 1) % items.length; }
  function prev() { idx = (idx - 1 + items.length) % items.length; }

  function meta(m: Item) {
    return {
      id: m.id,
      title: m.title || m.name || '',
      overview: m.overview || '',
      backdrop: `https://image.tmdb.org/t/p/original${m.backdrop_path}`,
      rating: m.vote_average || 0,
      year: (m.release_date || m.first_air_date || '').slice(0, 4),
      type: m.title ? 'movie' : 'tv',
    };
  }
</script>

<div
  class="relative w-full h-[75vh] min-h-[500px] max-h-[900px] bg-surface overflow-hidden"
  onmouseenter={() => hovering = true}
  onmouseleave={() => hovering = false}
>
  {#if !loaded}
    <div class="absolute inset-0 flex items-center justify-center bg-surface">
      <div class="text-center">
        <div class="w-12 h-12 border-4 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-4" />
        <p class="text-text-muted text-sm">Loading...</p>
      </div>
    </div>
  {:else if items.length === 0}
    <div class="absolute inset-0 flex items-center justify-center bg-surface">
      <p class="text-text-muted">No featured content available</p>
    </div>
  {:else}
    {#each items as item, i}
      {@const m = meta(item)}
      <div
        class="absolute inset-0 transition-opacity duration-700 ease-in-out"
        class:opacity-100={i === idx}
        class:opacity-0={i !== idx}
      >
        <img src={m.backdrop} alt={m.title} class="w-full h-full object-cover" />
        <div class="pointer-events-none absolute inset-0 bg-gradient-to-t from-surface-sunken via-surface-sunken/40 to-transparent" />
        <div class="pointer-events-none absolute inset-0 bg-gradient-to-r from-surface-sunken/90 via-surface-sunken/30 to-transparent" />
      </div>
    {/each}

    {@const cur = meta(items[idx])}
    <div class="absolute bottom-0 left-0 right-0 p-8 md:p-16 z-10">
      <div class="max-w-2xl">
        <div class="flex items-center gap-3 text-sm mb-3">
          {#if cur.rating > 0}
            <span class="flex items-center gap-1 text-yellow-400">
              <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20"><path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/></svg>
              {cur.rating.toFixed(1)}
            </span>
          {/if}
          {#if cur.year}
            <span class="text-text-muted">{cur.year}</span>
          {/if}
          <span class="uppercase text-xs tracking-wider px-2 py-0.5 rounded border border-primary/30 text-primary">
            {cur.type === 'movie' ? 'Movie' : 'TV Show'}
          </span>
        </div>

        <h2 class="text-4xl md:text-6xl font-black text-white mb-3 leading-tight line-clamp-2">{cur.title}</h2>
        <p class="text-text-secondary text-sm md:text-base line-clamp-2 mb-6 max-w-xl">{cur.overview}</p>

        <div class="flex items-center gap-3">
          <a
            href={`/watch/${cur.type}/${cur.id}`}
            class="inline-flex items-center gap-2 px-8 py-3 bg-primary text-white font-semibold rounded-lg hover:bg-primary-hover transition shadow-lg shadow-primary/30"
          >
            <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20"><path d="M6.423 4.167A1 1 0 005 5.035v9.93a1 1 0 001.423.868l8.5-4.965a1 1 0 000-1.736l-8.5-4.965z"/></svg>
            Play Now
          </a>
          <a
            href={`/${cur.type}/${cur.id}`}
            class="inline-flex items-center gap-2 px-6 py-3 bg-white/10 text-white font-medium rounded-lg hover:bg-white/20 backdrop-blur-sm transition border border-white/10"
          >
            More Info
          </a>
        </div>
      </div>
    </div>

    <div class="absolute bottom-4 right-8 md:right-16 z-10 flex items-center gap-2">
      {#each items as _, i}
        <button
          onclick={() => go(i)}
          class={'rounded-full transition-all duration-300 cursor-pointer h-2 ' + (i === idx ? 'bg-primary w-6' : 'bg-white/40 w-2')}
          aria-label={`Slide ${i + 1}`}
        />
      {/each}
    </div>

    <button
      onclick={prev}
      class={'absolute left-4 top-1/2 -translate-y-1/2 z-10 w-10 h-10 rounded-full bg-surface/60 hover:bg-surface/80 backdrop-blur-sm flex items-center justify-center text-white transition-opacity duration-300 cursor-pointer ' + (hovering ? 'opacity-100' : 'opacity-0')}
      aria-label="Previous"
    >
      <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7"/></svg>
    </button>
    <button
      onclick={next}
      class={'absolute right-4 top-1/2 -translate-y-1/2 z-10 w-10 h-10 rounded-full bg-surface/60 hover:bg-surface/80 backdrop-blur-sm flex items-center justify-center text-white transition-opacity duration-300 cursor-pointer ' + (hovering ? 'opacity-100' : 'opacity-0')}
      aria-label="Next"
    >
      <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7"/></svg>
    </button>
  {/if}
</div>
