<script lang="ts">
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
        api.get('/api/tmdb/trending/movie/week'),
        api.get('/api/tmdb/trending/tv/week'),
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
    const t = setInterval(() => idx = (idx + 1) % items.length, 6500);
    return () => clearInterval(t);
  });

  function go(i: number) { idx = i; }
  function next() { idx = (idx + 1) % items.length; }
  function prev() { idx = (idx - 1 + items.length) % items.length; }

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

<div
  class="relative w-full h-[80vh] min-h-[550px] max-h-[850px] bg-[#09090b] overflow-hidden group select-none"
  onmouseenter={() => hovering = true}
  onmouseleave={() => hovering = false}
  role="region"
  aria-label="Featured content slider"
>
  {#if !loaded}
    <div class="absolute inset-0 bg-[#09090b] flex items-center justify-center">
      <div class="w-full h-full bg-gradient-to-r from-zinc-900 via-zinc-800/40 to-zinc-900 animate-pulse relative">
        <div class="absolute bottom-16 left-8 md:left-16 space-y-4 max-w-xl">
          <div class="h-4 bg-zinc-800 rounded w-1/3"></div>
          <div class="h-12 bg-zinc-800 rounded w-full"></div>
          <div class="h-6 bg-zinc-800 rounded w-3/4"></div>
        </div>
      </div>
    </div>
  {:else if items.length === 0}
    <div class="absolute inset-0 flex flex-col items-center justify-center bg-[#09090b] text-zinc-500">
      <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-10 h-10 mb-2 text-zinc-700">
        <path stroke-linecap="round" stroke-linejoin="round" d="m15.75 10.5 4.72-4.72a.75.75 0 0 1 1.28.53v11.38a.75.75 0 0 1-1.28.53l-4.72-4.72M4.5 18.75h9a2.25 2.25 0 0 0 2.25-2.25v-9a2.25 2.25 0 0 0-2.25-2.25h-9A2.25 2.25 0 0 0 2.25 7.5v9a2.25 2.25 0 0 0 2.25 2.25Z" />
      </svg>
      <p class="text-sm font-semibold tracking-wider uppercase">No featured content available</p>
    </div>
  {:else}
    {#each items as item, i}
      {@const m = meta(item)}
      <div
        class="absolute inset-0 transition-all duration-1000 ease-in-out transform"
        class:opacity-100={i === idx}
        class:opacity-0={i !== idx}
        class:scale-100={i === idx}
        class:scale-105={i !== idx}
      >
        <img src={m.backdrop} alt={m.title} class="w-full h-full object-cover brightness-[0.55]" loading={i === 0 ? "eager" : "lazy"} />
        
        <div class="absolute inset-0 bg-gradient-to-t from-[#09090b] via-[#09090b]/30 to-transparent z-[1]" />
        <div class="absolute inset-0 bg-gradient-to-r from-[#09090b]/90 via-[#09090b]/20 to-transparent z-[1]" />
      </div>
    {/each}

    {@const cur = meta(items[idx])}
    <div class="absolute bottom-0 left-0 right-0 p-8 md:p-16 lg:px-24 pb-16 md:pb-24 z-10 pointer-events-none">
      <div class="max-w-3xl pointer-events-auto transform transition-all duration-500">
        
        <div class="flex items-center gap-3 text-xs md:text-sm font-semibold mb-4 text-zinc-300">
          {#if cur.rating > 0}
            <span class="flex items-center gap-1 bg-zinc-950/60 backdrop-blur-md px-2.5 py-1 rounded-md text-amber-400 border border-zinc-800/60">
              <svg class="w-4 h-4 fill-amber-400" viewBox="0 0 20 20"><path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/></svg>
              {cur.rating.toFixed(1)}
            </span>
          {/if}
          {#if cur.year}
            <span class="bg-zinc-950/60 backdrop-blur-md px-2.5 py-1 rounded-md border border-zinc-800/60">{cur.year}</span>
          {/if}
          <span class="uppercase text-xs tracking-wider px-2.5 py-1 rounded-md bg-red-500/10 border border-red-500/30 text-red-400">
            {cur.type === 'movie' ? 'Movie' : 'TV Series'}
          </span>
        </div>

        <h2 class="text-4xl md:text-6xl font-black text-white mb-4 tracking-tighter leading-[1.1] drop-shadow-[0_4px_12px_rgba(0,0,0,0.5)]">
          {cur.title}
        </h2>
        
        <p class="text-zinc-300 text-sm md:text-base leading-relaxed line-clamp-3 mb-8 max-w-2xl drop-shadow-[0_2px_4px_rgba(0,0,0,0.4)]">
          {cur.overview}
        </p>

        <div class="flex flex-wrap items-center gap-4">
          <a
            href={`/watch/${cur.type}/${cur.id}`}
            class="inline-flex items-center gap-2.5 px-8 py-3.5 bg-gradient-to-r from-red-600 to-pink-600 text-white font-bold rounded-xl hover:brightness-110 active:scale-95 transition shadow-xl shadow-red-600/20 group/btn"
          >
            <svg class="w-5 h-5 fill-white transition-transform group-hover/btn:scale-110" viewBox="0 0 20 20"><path d="M6.423 4.167A1 1 0 005 5.035v9.93a1 1 0 001.423.868l8.5-4.965a1 1 0 000-1.736l-8.5-4.965z"/></svg>
            Play Now
          </a>
          <a
            href={`/${cur.type}/${cur.id}`}
            class="inline-flex items-center gap-2.5 px-7 py-3.5 bg-zinc-900/40 text-white font-semibold rounded-xl hover:bg-zinc-800/80 backdrop-blur-md transition border border-zinc-800/80 active:scale-95"
          >
            More Info
          </a>
        </div>
      </div>
    </div>

    <div class="absolute bottom-6 right-8 md:right-16 z-20 flex items-center gap-2.5 bg-zinc-950/30 backdrop-blur-sm px-3 py-2 rounded-full border border-zinc-800/30">
      {#each items as _, mIndex}
        <button
          onclick={() => go(mIndex)}
          class={'rounded-full transition-all duration-500 cursor-pointer h-1.5 ' + (mIndex === idx ? 'bg-red-500 w-8' : 'bg-zinc-600/60 hover:bg-zinc-400 w-1.5')}
          aria-label={`Go to slide ${mIndex + 1}`}
        />
      {/each}
    </div>

    <button
      onclick={prev}
      class={'absolute left-6 top-1/2 -translate-y-1/2 z-20 w-12 h-12 rounded-xl bg-zinc-950/40 border border-zinc-800/50 text-white hover:bg-zinc-900 flex items-center justify-center transition-all duration-300 backdrop-blur-md transform hover:scale-105 active:scale-95 cursor-pointer ' + (hovering ? 'opacity-100 translate-x-0' : 'opacity-0 -translate-x-4')}
      aria-label="Previous Featured Slide"
    >
      <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7"/></svg>
    </button>
    
    <button
      onclick={next}
      class={'absolute right-6 top-1/2 -translate-y-1/2 z-20 w-12 h-12 rounded-xl bg-zinc-950/40 border border-zinc-800/50 text-white hover:bg-zinc-900 flex items-center justify-center transition-all duration-300 backdrop-blur-md transform hover:scale-105 active:scale-95 cursor-pointer ' + (hovering ? 'opacity-100 translate-x-0' : 'opacity-0 translate-x-4')}
      aria-label="Next Featured Slide"
    >
      <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7"/></svg>
    </button>
  {/if}
</div>