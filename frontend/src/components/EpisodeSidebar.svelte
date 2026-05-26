<script lang="ts">
  let { id, seasons = [1, 2, 3], selectedSeason = 1, episodes = [] } = $props();
  
  let selected = $state(selectedSeason);
</script>

<div class="bg-surface rounded-lg p-4 w-80 border border-border/50">
  <div class="mb-4">
    <label class="text-text text-sm font-medium mb-2 block">Season</label>
    <select bind:value={selected} class="w-full bg-surface-raised text-text px-3 py-2 rounded border border-border/50">
      {#each seasons as season}
        <option value={season}>Season {season}</option>
      {/each}
    </select>
  </div>
  
  {#if episodes.length > 0}
    <div class="max-h-96 overflow-y-auto">
      {#each episodes as ep}
        <a href={`/watch/tv/${id}`} class="flex items-center gap-3 p-2 rounded hover:bg-surface transition">
          <span class="text-primary font-bold text-sm w-8">E{ep.number}</span>
          <div class="flex-1 min-w-0">
            <p class="text-text text-sm truncate">{ep.title}</p>
            {#if ep.duration}
              <p class="text-text-muted text-xs">{ep.duration}</p>
            {/if}
          </div>
        </a>
      {/each}
    </div>
  {/if}
</div>