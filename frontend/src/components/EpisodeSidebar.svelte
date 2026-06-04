<script lang="ts">
  import EmptyState from './EmptyState.svelte';

  let {
    seasons = [],
    selectedSeason = 1,
    episodes = [],
    currentEpisode = { season: 1, episode: 1 },
    onSeasonChange = (_s: number) => {},
    onEpisodeClick = (_ep: number) => {},
  } = $props();

  let scrollContainer: HTMLDivElement | undefined = $state();

  function tmdbImg(path: string, size: string = 'w185'): string {
    return path ? `https://image.tmdb.org/t/p/${size}${path}` : '';
  }

  function formatDuration(minutes: number | undefined | null): string {
    if (!minutes) return '';
    const h = Math.floor(minutes / 60);
    const m = minutes % 60;
    if (h > 0 && m > 0) return `${h}h ${m}m`;
    if (h > 0) return `${h}h`;
    return `${m}m`;
  }

  let selected = $state(1);
  $effect(() => {
    selected = selectedSeason;
  });

  $effect(() => {
    if (!scrollContainer || episodes.length === 0) return;
    const currentEl = scrollContainer.querySelector<HTMLElement>('[data-current="true"]');
    if (currentEl) currentEl.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  });
</script>

<div class="w-full bg-base">
  <div class="p-3 border-b border-white/10 flex flex-col gap-3 shrink-0">
    <div class="flex items-center justify-between">
      <h3 class="text-base font-medium text-ink">
        {selectedSeason > 0 ? `Season ${selectedSeason}` : 'Episodes'}
      </h3>
      {#if seasons.length > 1}
        <select
          aria-label="Select season"
          bind:value={selected}
          onchange={() => onSeasonChange(selected)}
          class="bg-base-2 border border-white/10 text-sm text-ink rounded-full px-3 py-1.5 focus:outline-none focus:border-yt-blue"
        >
          {#each seasons as s}
            <option value={s.season_number} class="bg-base">Season {s.season_number}</option>
          {/each}
        </select>
      {/if}
    </div>
  </div>

  <div bind:this={scrollContainer} class="overflow-y-auto no-scrollbar p-1 space-y-1 max-h-[calc(100vh-14rem)]">
    {#if episodes.length > 0}
      {#each episodes as ep (ep.episode_number)}
        {@const isCurrent = ep.episode_number === currentEpisode.episode && selectedSeason === currentEpisode.season}
        <button
          onclick={() => onEpisodeClick(ep.episode_number)}
          data-current={isCurrent ? 'true' : undefined}
          class="w-full flex items-start gap-3 p-2 rounded-lg text-left {isCurrent ? 'bg-base-2' : 'hover:bg-base-2'}"
        >
          <div class="flex-shrink-0 w-6 text-center text-xs text-ink-muted pt-1">
            {isCurrent ? '▶' : ep.episode_number}
          </div>
          <div class="flex-shrink-0 w-40 aspect-video rounded-md overflow-hidden bg-base-3">
            {#if ep.still_path}
              <img src={tmdbImg(ep.still_path, 'w185')} alt={ep.name} class="w-full h-full object-cover" loading="lazy" />
            {:else}
              <div class="w-full h-full flex items-center justify-center text-ink-faint text-[10px]">E{String(ep.episode_number).padStart(2, '0')}</div>
            {/if}
          </div>
          <div class="flex-1 min-w-0 py-1">
            <h4 class="text-sm font-medium leading-tight line-clamp-2 {isCurrent ? 'text-ink' : 'text-ink'}">
              {ep.name || `Episode ${ep.episode_number}`}
            </h4>
            <p class="text-xs text-ink-muted mt-1">
              {#if ep.runtime}{formatDuration(ep.runtime)}{/if}
              {#if ep.overview}<span class="line-clamp-2 block mt-0.5">{ep.overview}</span>{/if}
            </p>
          </div>
        </button>
      {/each}
    {:else}
      <div class="p-3">
        <EmptyState
          compact
          icon="episode"
          title="No episodes found"
          message="Try a different season."
        />
      </div>
    {/if}
  </div>
</div>
