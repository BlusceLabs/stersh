<script lang="ts">
  import MovieCard from './MovieCard.svelte';

  let items = $state<any[]>([]);
  let loaded = $state(false);

  async function loadFromAPI() {
    try {
      const token = localStorage.getItem('watchfy_token');
      const headers: Record<string, string> = { 'Content-Type': 'application/json' };
      if (token) headers['Authorization'] = `Bearer ${token}`;
      const res = await fetch('/continue-watching/', { headers });
      if (res.ok) {
        const data = await res.json();
        items = (data || []).map((item: any) => ({
          id: item.tmdb_id,
          title: item.title,
          name: item.title,
          poster_path: item.poster_path,
          vote_average: item.vote_average || 0,
          release_date: item.release_date || '',
          first_air_date: item.first_air_date || '',
          media_type: item.media_type,
          _progress: {
            currentTime: item.current_time || 0,
            duration: item.duration || 0,
            timestamp: item.updated_at || item.created_at || 0,
          },
        }));
        loaded = true;
        return;
      }
    } catch {}
    // Fallback to localStorage if API fails
    loadFromStorage();
  }

  function loadFromStorage() {
    const result: any[] = [];
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (!key || !key.startsWith('watchfy:')) continue;
      try {
        const data = JSON.parse(localStorage.getItem(key) || '');
        result.push({
          id: data.tmdbId,
          title: data.title,
          name: data.title,
          poster_path: data.poster,
          vote_average: 0,
          release_date: '',
          first_air_date: '',
          media_type: data.mediaType,
          _progress: data,
        });
      } catch {}
    }
    result.sort((a, b) => (b._progress.timestamp || 0) - (a._progress.timestamp || 0));
    items = result.slice(0, 10);
    loaded = true;
  }

  let scrollEl: HTMLDivElement;

  function scrollSide(direction: 'left' | 'right') {
    if (!scrollEl) return;
    const scrollAmount = scrollEl.clientWidth * 0.75;
    scrollEl.scrollBy({
      left: direction === 'left' ? -scrollAmount : scrollAmount,
      behavior: 'smooth'
    });
  }

  $effect(() => {
    loadFromAPI();
  });
</script>

{#if items.length > 0}
  <div class="mb-10 relative select-none">
    <div class="flex items-end justify-between mb-4 px-4 md:px-12">
      <h2 class="text-lg md:text-2xl font-black text-white tracking-tight drop-shadow-sm">
        Continue Watching
      </h2>
    </div>

    <div class="relative group/track px-4 md:px-12">
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

      <div class="absolute inset-y-0 left-0 w-12 bg-gradient-to-r from-[#09090b] to-transparent z-20 pointer-events-none hidden md:block"></div>
      <div class="absolute inset-y-0 right-0 w-12 bg-gradient-to-l from-[#09090b] to-transparent z-20 pointer-events-none hidden md:block"></div>

      <div
        bind:this={scrollEl}
        class="flex gap-4 overflow-x-auto scroll-smooth pb-4 pt-1 snap-x snap-mandatory mask-scrollbar"
      >
        {#each items as item}
          <div class="flex-shrink-0 w-[140px] sm:w-[170px] snap-start transition-transform duration-300 transform hover:scale-[1.02] hover:z-10">
            <MovieCard movie={item} type={item.media_type === 'tv' ? 'tv' : 'movie'} progress={item._progress?.duration > 0 ? item._progress.currentTime / item._progress.duration : 0} />
          </div>
        {/each}
      </div>
    </div>
  </div>
{/if}

<style>
  .mask-scrollbar::-webkit-scrollbar { display: none; }
  .mask-scrollbar { scrollbar-width: none; -ms-overflow-style: none; }
</style>
