<script lang="ts">
  let { id, seasons = [1, 2, 3], selectedSeason = 1, episodes = [] } = $props();
  
  let selected = $state(selectedSeason);
</script>

<div class="w-full max-w-sm bg-zinc-900/40 border border-zinc-800/80 rounded-2xl p-5 backdrop-blur-xl shadow-2xl flex flex-col h-[500px]">
  
  <div class="mb-5 flex-shrink-0">
    <label for="season-select" class="text-zinc-400 text-xs font-bold tracking-widest uppercase block mb-2.5">
      Select Season
    </label>
    
    <div class="relative group">
      <select 
        id="season-select"
        bind:value={selected} 
        class="w-full appearance-none bg-zinc-950 text-zinc-200 hover:text-white px-4 py-3 pr-10 rounded-xl border border-zinc-800 hover:border-zinc-700 transition-all duration-300 font-semibold text-sm cursor-pointer focus:outline-none focus:ring-2 focus:ring-red-500/40"
      >
        {#each seasons as season}
          <option value={season} class="bg-zinc-950 text-zinc-300">Season {season.toString().padStart(2, '0')}</option>
        {/each}
      </select>
      
      <div class="absolute right-4 top-1/2 -translate-y-1/2 pointer-events-none text-zinc-500 group-hover:text-zinc-300 transition-colors">
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2.5" stroke="currentColor" class="w-4 h-4">
          <path stroke-linecap="round" stroke-linejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" />
        </svg>
      </div>
    </div>
  </div>
  
  {#if episodes.length > 0}
    <div class="flex-1 overflow-y-auto pr-1 space-y-2 custom-scrollbar mask-gradient">
      {#each episodes as ep}
        <a 
          href={`/watch/tv/${id}?season=${selected}&episode=${ep.number}`} 
          class="flex items-center gap-4 p-2.5 rounded-xl bg-zinc-950/30 hover:bg-zinc-800/50 border border-transparent hover:border-zinc-800/60 group transition-all duration-300 transform active:scale-[0.99]"
        >
          <div class="w-16 h-10 rounded-lg bg-zinc-900 border border-zinc-800 flex items-center justify-center relative overflow-hidden flex-shrink-0 shadow-inner group-hover:border-red-500/30 transition-colors">
            <span class="text-zinc-500 group-hover:text-red-400 font-black text-xs transition-colors">
              E{ep.number.toString().padStart(2, '0')}
            </span>
            <div class="absolute bottom-0 left-0 w-0 h-[2px] bg-red-500 group-hover:w-full transition-all duration-300"></div>
          </div>
          
          <div class="flex-1 min-w-0">
            <p class="text-zinc-200 group-hover:text-white font-medium text-sm truncate transition-colors">
              {ep.title}
            </p>
            {#if ep.duration}
              <p class="text-zinc-500 text-xs font-medium mt-0.5 flex items-center gap-1">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-3 h-3 text-zinc-600">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
                </svg>
                {ep.duration}
              </p>
            {/if}
          </div>

          <div class="opacity-0 group-hover:opacity-100 text-red-500 transition-all duration-300 pr-1 transform translate-x-2 group-hover:translate-x-0">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="w-5 h-5">
              <path fill-rule="evenodd" d="M4.5 5.653c0-1.426 1.529-2.33 2.779-1.643l11.54 6.348c1.295.712 1.295 2.573 0 3.285L7.28 19.991c-1.25.687-2.779-.217-2.779-1.643V5.653z" clip-rule="evenodd" />
            </svg>
          </div>
        </a>
      {/each}
    </div>
  {:else}
    <div class="flex-1 flex flex-col items-center justify-center text-center p-6 text-zinc-500">
      <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-8 h-8 mb-2 text-zinc-600">
        <path stroke-linecap="round" stroke-linejoin="round" d="M6 20.25h12m-12-3h12m-12-3h12m-12-3h12m-12-3h12m-12-3h12M3.75 20.25h16.5c.621 0 1.125-.504 1.125-1.125V4.125c0-.621-.504-1.125-1.125-1.125H3.75c-.621 0-1.125.504-1.125 1.125v15c0 .621.504 1.125 1.125 1.125Z" />
      </svg>
      <p class="text-xs font-semibold uppercase tracking-wider">No Episodes Loaded</p>
    </div>
  {/if}
</div>

<style>
  /* Custom scrollbar layout configuration */
  .custom-scrollbar::-webkit-scrollbar {
    width: 4px;
  }
  .custom-scrollbar::-webkit-scrollbar-track {
    background: transparent;
  }
  .custom-scrollbar::-webkit-scrollbar-thumb {
    background: #27272a;
    border-radius: 9999px;
  }
  .custom-scrollbar::-webkit-scrollbar-thumb:hover {
    background: #3f3f46;
  }
</style>