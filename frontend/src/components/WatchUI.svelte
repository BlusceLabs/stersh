<script lang="ts">
  import { onMount } from 'svelte';
  import HLSPlayer from './HLSPlayer.svelte';
  import { tmdbApi, api } from '../lib/api';

  let { media = 'movie', id = '0' } = $props();

  let season = $state(1);
  let episode = $state(1);
  let showDetails: any = $state(null);

  let mediaType = $derived(media === 'tv' ? 'tv' : 'movie');
  let currentSeason = $derived(
    showDetails?.seasons?.find((s: any) => s.season_number === season)
  );
  let totalEpisodes = $derived(currentSeason?.episode_count ?? 0);
  let hasNextEpisode = $derived(mediaType === 'tv' && showDetails && episode < totalEpisodes);
  let streamUrl = $derived(api.getStreamSource(Number(id), mediaType, season, episode));
  let title = $derived(showDetails?.name || showDetails?.title || 'Now Playing');
  let year = $derived((showDetails?.release_date || '').split('-')[0]);
  let epBadge = $derived(mediaType === 'tv' ? `S${season}:E${episode}` : year);

  let subtext = $derived(
    mediaType === 'tv'
      ? `You are watching Season ${season} Episode ${episode} of "${title}".`
      : showDetails?.overview || 'Streaming video file assets from localized provider arrays.'
  );

  onMount(() => {
    const params = new URLSearchParams(window.location.search);
    season = parseInt(params.get('season') || '1');
    episode = parseInt(params.get('episode') || '1');

    tmdbApi.details(mediaType, Number(id))
      .then((data: any) => {
        showDetails = data;
        document.title = `Watching: ${data.name || data.title || 'Stream'} - Watchfy`;
      })
      .catch(() => {});

    window.addEventListener('popstate', syncFromUrl);
  });

  function syncFromUrl() {
    const params = new URLSearchParams(window.location.search);
    season = parseInt(params.get('season') || '1');
    episode = parseInt(params.get('episode') || '1');
  }

  function findNextSeason() {
    return showDetails?.seasons?.find(
      (s: any) => s.season_number > season && s.episode_count > 0
    );
  }

  function getNextEpisode() {
    if (episode < totalEpisodes) return { season, episode: episode + 1 };
    const ns = findNextSeason();
    if (ns) return { season: ns.season_number, episode: 1 };
    return null;
  }

  function goToNextEpisode() {
    const next = getNextEpisode();
    if (!next) return;

    season = next.season;
    episode = next.episode;

    const url = new URL(window.location.href);
    url.searchParams.set('season', String(season));
    url.searchParams.set('episode', String(episode));
    window.history.pushState({}, '', url.toString());
    document.title = `Watching: ${title} - Watchfy`;
  }

  function prewarmNext() {
    const next = getNextEpisode();
    if (!next) return;
    const url = `/api/black/prewarm?tmdbId=${id}&mediaType=tv&season=${next.season}&episode=${next.episode}`;
    fetch(url).catch(() => {});
  }

  $effect(() => {
    if (!showDetails || mediaType !== 'tv' || !streamUrl) return;
    const timer = setTimeout(prewarmNext, 3000);
    return () => clearTimeout(timer);
  });
</script>

<div class="relative max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">

  <div class="w-full rounded-2xl overflow-hidden mb-8 border border-zinc-900/80 shadow-2xl shadow-black/90 bg-black">
    <HLSPlayer
      src={streamUrl}
      title={title}
      autoPlay={true}
    />
  </div>

  <div class="bg-zinc-900/20 backdrop-blur-md border border-zinc-800/40 rounded-2xl p-6 md:p-8 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-6 shadow-xl">
    <div class="space-y-2 flex-1">
      <div class="flex items-center gap-2">
        <span class="text-[10px] font-black tracking-widest uppercase px-2 py-0.5 rounded bg-zinc-800 text-zinc-400 border border-zinc-700/50">
          {mediaType === 'tv' ? 'TV Show' : 'Movie'}
        </span>
        {#if epBadge}
          <span class="text-xs font-bold text-red-400">{epBadge}</span>
        {/if}
      </div>

      <h1 class="text-2xl md:text-3xl font-black text-white tracking-tight leading-tight">
        {title}
      </h1>
      <p class="text-sm text-zinc-400 font-medium max-w-2xl">
        {subtext}
      </p>
    </div>

    <div class="flex-shrink-0 flex items-center gap-3">
      {#if hasNextEpisode}
        <button
          onclick={goToNextEpisode}
          class="inline-flex items-center gap-2 px-5 py-3 bg-red-600 hover:bg-red-500 text-white text-sm font-semibold rounded-xl transition-all active:scale-95 shadow-lg shadow-red-600/30"
        >
          Next Episode
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2.5" stroke="currentColor" class="w-4 h-4">
            <path stroke-linecap="round" stroke-linejoin="round" d="m9 12.75 3 3m0 0 3-3m-3 3v-7.5M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
          </svg>
        </button>
      {/if}
      <a
        href={`/${mediaType}/${id}`}
        class="inline-flex items-center gap-2 px-5 py-3 bg-zinc-900 border border-zinc-800 hover:border-zinc-700 hover:bg-zinc-800/80 text-zinc-200 hover:text-white text-sm font-semibold rounded-xl transition-all active:scale-95 shadow-lg shadow-black/40"
      >
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2.5" stroke="currentColor" class="w-4 h-4">
          <path stroke-linecap="round" stroke-linejoin="round" d="M9 15 3 9m0 0 6-6M3 9h12a6 6 0 0 1 0 12h-3" />
        </svg>
        Exit Player
      </a>
    </div>
  </div>

</div>
