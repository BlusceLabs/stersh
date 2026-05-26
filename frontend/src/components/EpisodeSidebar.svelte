<script lang="ts">
  export let id: number;
  export let seasons: number[] = [1, 2, 3];
  export let selectedSeason = 1;
  export let episodes: { number: number; title: string; duration?: string }[] = [];
</script>

<div class="bg-zinc-900 rounded-lg p-4 w-80">
  <div class="mb-4">
    <label class="text-white text-sm font-medium mb-2 block">Season</label>
    <select bind:value={selectedSeason} class="w-full bg-zinc-800 text-white px-3 py-2 rounded">
      {#each seasons as season}
        <option value={season}>Season {season}</option>
      {/each}
    </select>
  </div>
  
  {#if episodes.length > 0}
    <div class="max-h-96 overflow-y-auto">
      {#each episodes as ep}
        <a href={`/watch/tv/${id}/${selectedSeason}/${ep.number}`} class="flex items-center gap-3 p-2 rounded hover:bg-zinc-800 transition">
          <span class="text-yellow-500 font-bold text-sm w-8">E{ep.number}</span>
          <div class="flex-1 min-w-0">
            <p class="text-white text-sm truncate">{ep.title}</p>
            {#if ep.duration}
              <p class="text-gray-400 text-xs">{ep.duration}</p>
            {/if}
          </div>
        </a>
      {/each}
    </div>
  {/if}
</div>