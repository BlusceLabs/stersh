<script lang="ts">
  let {
    id,
    seasons = [],
    selectedSeason = 1,
    episodes = [],
    currentEpisode = { season: 1, episode: 1 },
    onSeasonChange = (_s: number) => {},
    onEpisodeClick = (_ep: number) => {},
  } = $props();

  let scrollContainer: HTMLDivElement;

  function tmdbImg(path: string, size: string = 'w185'): string {
    if (!path) return '';
    return `https://image.tmdb.org/t/p/${size}${path}`;
  }

  function formatDuration(minutes: number | undefined | null): string {
    if (!minutes) return '';
    const h = Math.floor(minutes / 60);
    const m = minutes % 60;
    if (h > 0 && m > 0) return `${h}h ${m}m`;
    if (h > 0) return `${h}h`;
    return `${m}m`;
  }

  let selected = $state(selectedSeason);
  $effect(() => {
    if (selected !== selectedSeason) {
      onSeasonChange(selected);
    }
  });

  $effect(() => {
    if (!scrollContainer || episodes.length === 0) return;
    const currentEl = scrollContainer.querySelector<HTMLButtonElement>('[data-current="true"]');
    if (currentEl) {
      currentEl.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    }
  });
</script>

<div class="w-full bg-[#1f1f1f] border border-white/10 rounded-xl overflow-hidden flex flex-col max-h-[75vh] lg:max-h-[800px]">
  
  <div class="p-4 bg-white/5 border-b border-white/10 flex flex-col gap-2 shrink-0">
    <div class="flex items-center justify-between">
      <div class="min-w-0">
        <h3 class="text-[16px] font-bold text-white truncate leading-snug">
          {selectedSeason > 0 ? `Season ${selectedSeason}` : 'Episodes Feed'}
        </h3>
        <p class="text-xs text-[#aaa] mt-0.5 font-normal">
          Watchfy Queue • <span class="font-medium text-white">{episodes.length} episodes</span>
        </p>
      </div>
      
      {#if seasons.length > 1}
        <div class="relative">
          <select
            bind:value={selected}
            class="appearance-none bg-white/10 hover:bg-white/15 text-xs font-semibold px-3 py-1.5 pr-8 rounded-full border border-transparent transition-colors cursor-pointer text-white focus:outline-none"
          >
            {#each seasons as s}
              <option value={s.season_number} class="bg-[#1f1f1f] text-white">
                Season {s.season_number}
              </option>
            {/each}
          </select>
          <div class="absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none text-white shrink-0">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-4 h-4">
              <path fill-rule="evenodd" d="M5.22 8.22a.75.75 0 0 1 1.06 0L10 11.94l3.72-3.72a.75.75 0 1 1 1.06 1.06l-4.25 4.25a.75.75 0 0 1-1.06 0L5.22 9.28a.75.75 0 0 1 0-1.06Z" clip-rule="evenodd" />
            </svg>
          </div>
        </div>
      {/if}
    </div>
  </div>

  <div bind:this={scrollContainer} class="flex-1 overflow-y-auto no-scrollbar divide-y divide-white/[0.04] p-1.5 space-y-0.5">
    {#if episodes.length > 0}
      {#each episodes as ep, index (ep.episode_number)}
        {@const isCurrent = ep.episode_number === currentEpisode.episode && selectedSeason === currentEpisode.season}
        
        <button
          onclick={() => onEpisodeClick(ep.episode_number)}
          data-current={isCurrent ? 'true' : undefined}
          class="w-full flex items-center gap-2 p-2 rounded-lg transition-colors text-left relative group
            {isCurrent ? 'bg-white/10' : 'hover:bg-white/5'}"
        >
          
          <div class="w-6 flex items-center justify-center shrink-0">
            {#if isCurrent}
              <div class="flex items-end gap-[2px] h-3 w-3 mb-0.5" aria-hidden="true">
                <div class="bg-[#f00] w-[2px] h-full rounded-sm animate-[bounce_1s_infinite_100ms]"></div>
                <div class="bg-[#f00] w-[2px] h-[60%] rounded-sm animate-[bounce_1s_infinite_300ms]"></div>
                <div class="bg-[#f00] w-[2px] h-[85%] rounded-sm animate-[bounce_1s_infinite_200ms]"></div>
              </div>
            {:else}
              <span class="text-xs font-medium text-zinc-400 group-hover:hidden">{index + 1}</span>
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="w-3.5 h-3.5 text-white hidden group-hover:block">
                <path fill-rule="evenodd" d="M4.5 5.653c0-1.426 1.529-2.33 2.779-1.643l11.54 6.347c1.295.712 1.295 2.573 0 3.286L7.28 19.99c-1.25.687-2.779-.218-2.779-1.643V5.653Z" clip-rule="evenodd" />
              </svg>
            {/if}
          </div>

          <div class="relative shrink-0 w-[100px] aspect-video rounded-md overflow-hidden bg-zinc-900 border border-white/5 shadow-inner">
            {#if ep.still_path}
              <img src={tmdbImg(ep.still_path, 'w185')} alt={ep.name} class="w-full h-full object-cover" loading="lazy" />
            {:else}
              <div class="w-full h-full flex items-center justify-center bg-zinc-900">
                <span class="text-zinc-600 text-[10px] font-bold">E{String(ep.episode_number).padStart(2, '0')}</span>
              </div>
            {/if}
            
            {#if ep.runtime}
              <div class="absolute bottom-1 right-1 bg-black/80 text-white text-[10px] font-medium px-1 rounded-[2px] tracking-wide">
                {formatDuration(ep.runtime)}
              </div>
            {/if}
          </div>

          <div class="flex-1 min-w-0 pr-1">
            <h4 class="text-sm font-bold leading-tight line-clamp-2 transition-colors 
              {isCurrent ? 'text-white' : 'text-[#f1f1f1]'}"
            >
              {ep.name || 'Episode ' + ep.episode_number}
            </h4>
            <p class="text-xs text-[#aaa] mt-1 truncate font-normal">
              Episode {ep.episode_number} {#if isCurrent}• <span class="text-[#f00] font-semibold">Now Playing</span>{/if}
            </p>
          </div>

        </button>
      {/each}
    {:else}
      <div class="flex flex-col items-center justify-center text-center py-12 text-zinc-500">
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6 mb-2 text-zinc-600">
          <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 12h16.5m-16.5 5.25h16.5m-16.5-10.5h16.5" />
        </svg>
        <p class="text-xs font-bold uppercase tracking-widest text-zinc-400">No episodes found for this season</p>
      </div>
    {/if}
  </div>
</div>

<style>
  /* Hidden Scrollbar configuration layer for embedded feed tracking components */
  :global(.no-scrollbar::-webkit-scrollbar) {
    display: none;
  }
  :global(.no-scrollbar) {
    -ms-overflow-style: none;
    scrollbar-width: none;
  }
</style>