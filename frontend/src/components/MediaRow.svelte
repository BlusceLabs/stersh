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
      const data = await api.get(`/tmdb/${endpoint}`);
      items = data?.results || [];
    } catch (e) {
      console.error(`row "${title}" error:`, e);
    }
    loaded = true;
  }

  function scrollBy(amount: number) {
    scrollEl?.scrollBy({ left: amount, behavior: 'smooth' });
  }
</script>

<div class="mb-8">
  <div class="flex items-center justify-between mb-4">
    <h2 class="text-xl md:text-2xl font-bold text-text">{title}</h2>
    {#if items.length > 0}
      <a href="/search" class="text-sm text-primary hover:text-primary-hover transition">View All</a>
    {/if}
  </div>

  <div class="relative group">
    {#if items.length > 0}
      <button
        onclick={() => scrollBy(-800)}
        class="absolute left-0 top-0 bottom-0 z-10 w-12 flex items-center justify-center bg-gradient-to-r from-surface-sunken/80 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 cursor-pointer"
        aria-label="Scroll left"
      >
        <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7"/></svg>
      </button>
      <button
        onclick={() => scrollBy(800)}
        class="absolute right-0 top-0 bottom-0 z-10 w-12 flex items-center justify-center bg-gradient-to-l from-surface-sunken/80 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 cursor-pointer"
        aria-label="Scroll right"
      >
        <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7"/></svg>
      </button>
    {/if}

    <div
      bind:this={scrollEl}
      class="flex gap-3 overflow-x-auto scroll-smooth pb-2"
    >
      {#if !loaded}
        {#each { length: 8 } as _}
          <div class="flex-shrink-0 w-[160px]">
            <div class="aspect-[2/3] bg-surface-raised rounded-lg animate-pulse" />
            <div class="mt-2 h-4 bg-surface-raised rounded animate-pulse" />
            <div class="mt-1 h-3 bg-surface-raised rounded w-2/3 animate-pulse" />
          </div>
        {/each}
      {:else}
        {#each items as item}
          <div class="flex-shrink-0 w-[160px] sm:w-[180px]">
            <MovieCard movie={item} type={item.media_type === 'tv' ? 'tv' : 'movie'} />
          </div>
        {/each}
      {/if}
    </div>
  </div>
</div>

<style>
  div::-webkit-scrollbar { display: none; }
  div { scrollbar-width: none; }
</style>
