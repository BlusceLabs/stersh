<script lang="ts">
  import { api } from '../lib/api';
  import MovieCard from './MovieCard.svelte';

  interface Item {
    id: number;
    title?: string;
    name?: string;
    poster_path: string | null;
    backdrop_path: string | null;
    vote_average: number;
    release_date?: string;
    first_air_date?: string;
    media_type?: string;
  }

  let { title = '', endpoint = '' } = $props();
  let items = $state<Item[]>([]);
  let loaded = $state(false);
  let scrollEl: HTMLDivElement | undefined = $state();

  $effect(() => {
    if (endpoint) loadItems();
  });

  async function loadItems() {
    try {
      const data = await api.get(`/api/tmdb/${endpoint}`);
      items = data?.results || [];
    } catch (e) {
      console.error(`row "${title}" error:`, e);
    }
    loaded = true;
  }

  function scrollSide(direction: 'left' | 'right') {
    if (!scrollEl) return;
    const scrollAmount = scrollEl.clientWidth * 0.75;
    scrollEl.scrollBy({ 
      left: direction === 'left' ? -scrollAmount : scrollAmount, 
      behavior: 'smooth' 
    });
  }
</script>

<div class="mb-10 relative select-none">
  <div class="flex items-end justify-between mb-4 px-4 md:px-12">
    <h2 class="text-lg md:text-2xl font-black text-white tracking-tight drop-shadow-sm">
      {title}
    </h2>
    {#if items.length > 0}
      <a 
        href="/search" 
        class="text-xs font-bold tracking-wider uppercase text-zinc-400 hover:text-red-400 transition-colors duration-200 flex items-center gap-1 group/link"
      >
        View All 
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2.5" stroke="currentColor" class="w-3 h-3 transform group-hover/link:translate-x-1 transition-transform">
          <path stroke-linecap="round" stroke-linejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" />
        </svg>
      </a>
    {/if}
  </div>

  <div class="relative group/track px-4 md:px-12">
    {#if items.length > 0}
      <button
        onclick={() => scrollSide('left')}
        class="absolute left-6 md:left-14 top-1/2 -translate-y-1/2 z-30 w-10 h-10 rounded-full bg-zinc-950/70 border border-zinc-800 text-white hover:bg-zinc-900 flex items-center justify-center backdrop-blur-md opacity-0 group-hover/track:opacity-100 transition-all duration-300 transform -translate-x-2 group-hover/track:translate-x-0 shadow-2xl hover:scale-105 active:scale-95 cursor-pointer"
        aria-label="Scroll Carousel Left"
      >
        <svg class="w-5 h-5 stroke-[2.5]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7"/></svg>
      </button>

      <button
        onclick={() => scrollSide('right')}
        class="absolute right-6 md:right-14 top-1/2 -translate-y-1/2 z-30 w-10 h-10 rounded-full bg-zinc-950/70 border border-zinc-800 text-white hover:bg-zinc-900 flex items-center justify-center backdrop-blur-md opacity-0 group-hover/track:opacity-100 transition-all duration-300 transform translate-x-2 group-hover/track:translate-x-0 shadow-2xl hover:scale-105 active:scale-95 cursor-pointer"
        aria-label="Scroll Carousel Right"
      >
        <svg class="w-5 h-5 stroke-[2.5]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7"/></svg>
      </button>
    {/if}

    <div class="absolute inset-y-0 left-0 w-12 bg-gradient-to-r from-[#09090b] to-transparent z-20 pointer-events-none hidden md:block"></div>
    <div class="absolute inset-y-0 right-0 w-12 bg-gradient-to-l from-[#09090b] to-transparent z-20 pointer-events-none hidden md:block"></div>

    <div
      bind:this={scrollEl}
      class="flex gap-4 overflow-x-auto scroll-smooth pb-4 pt-1 snap-x snap-mandatory mask-scrollbar"
    >
      {#if !loaded}
        {#each { length: 7 } as _}
          <div class="flex-shrink-0 w-[140px] sm:w-[170px] space-y-3">
            <div class="aspect-[2/3] bg-gradient-to-br from-zinc-900 via-zinc-800/50 to-zinc-900 rounded-xl animate-pulse border border-zinc-800/40 relative overflow-hidden">
              <div class="absolute inset-0 -translate-x-full bg-gradient-to-r from-transparent via-white/5 to-transparent shimmer-line"></div>
            </div>
            <div class="space-y-1.5 px-1">
              <div class="h-3.5 bg-zinc-800 rounded w-5/6 animate-pulse" />
              <div class="h-2.5 bg-zinc-900 rounded w-1/2 animate-pulse" />
            </div>
          </div>
        {/each}
      {:else}
        {#each items as item}
          <div class="flex-shrink-0 w-[140px] sm:w-[170px] snap-start transition-transform duration-300 transform hover:scale-[1.02] hover:z-10">
            <MovieCard movie={item} type={item.media_type === 'tv' ? 'tv' : 'movie'} />
          </div>
        {/each}
      {/if}
    </div>
  </div>
</div>

<style>
  /* Strip default native desktop navigation controls safely */
  .mask-scrollbar::-webkit-scrollbar {
    display: none;
  }
  .mask-scrollbar {
    scrollbar-width: none;
    -ms-overflow-style: none;
  }

  /* Shimmer gradient animation wave style configuration */
  @keyframes shimmer {
    100% { transform: translateX(100%); }
  }
  .shimmer-line {
    animation: shimmer 1.8s infinite linear;
  }
</style>