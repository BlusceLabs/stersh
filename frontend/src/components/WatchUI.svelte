<script lang="ts">
  import { onDestroy, onMount } from 'svelte';
  import HLSPlayer from './HLSPlayer.svelte';
  import EpisodeSidebar from './EpisodeSidebar.svelte';
  import EmptyState from './EmptyState.svelte';
  import { tmdbApi, api } from '../lib/api';

  let { media = 'movie', id = '0', server = 'white' } = $props();

  let season = $state(1);
  let episode = $state(1);
  let showDetails: any = $state(null);
  let seasonEpisodes: any[] = $state([]);
  let activeServer = $state('white');
  let shareCopied = $state(false);

  let mediaType: 'movie' | 'tv' = $derived(media === 'tv' ? 'tv' : 'movie');
  let currentEpisodeData = $derived(
    mediaType === 'tv'
      ? seasonEpisodes.find((ep: any) => ep.episode_number === episode)
      : null
  );
  let currentSeasonData = $derived(
    showDetails?.seasons?.find((s: any) => s.season_number === season)
  );
  let totalEpisodes = $derived(currentSeasonData?.episode_count ?? 0);
  let hasNextEpisode = $derived(mediaType === 'tv' && showDetails && episode < totalEpisodes);
  let hasPrevEpisode = $derived(mediaType === 'tv' && showDetails && (episode > 1 || findPrevSeason() !== null));
  let streamUrl = $derived(api.getStreamSource(Number(id), mediaType, season, episode, activeServer));
  let title = $derived(showDetails?.name || showDetails?.title || 'Now Playing');
  let year = $derived((showDetails?.release_date || showDetails?.first_air_date || '').split('-')[0]);
  let epBadge = $derived(mediaType === 'tv' ? `S${season} E${episode}` : year);
  let watchHeading = $derived(mediaType === 'tv' && currentEpisodeData?.name ? currentEpisodeData.name : title);
  let backdropUrl = $derived(
    showDetails?.backdrop_path ? tmdbImg(showDetails.backdrop_path, 'w1280') : ''
  );
  let runtimeLabel = $derived(
    mediaType === 'tv'
      ? formatRuntime(currentEpisodeData?.runtime)
      : formatRuntime(showDetails?.runtime)
  );
  let matchLabel = $derived(
    showDetails?.vote_average ? `${Math.round(showDetails.vote_average * 10)}% match` : 'Watchfy pick'
  );
  let seasonsList = $derived(
    (showDetails?.seasons || []).filter((s: any) => s.season_number > 0 && s.episode_count > 0)
  );

  function tmdbImg(path: string, size: string = 'w185'): string {
    if (!path) return '';
    return `https://image.tmdb.org/t/p/${size}${path}`;
  }

  function formatRuntime(minutes: number | undefined | null): string {
    if (!minutes) return '';
    const h = Math.floor(minutes / 60);
    const m = minutes % 60;
    if (h > 0 && m > 0) return `${h}h ${m}m`;
    if (h > 0) return `${h}h`;
    return `${m}m`;
  }

  function syncFromUrl() {
    const params = new URLSearchParams(window.location.search);
    season = parseInt(params.get('season') || '1');
    episode = parseInt(params.get('episode') || '1');
  }

  $effect(() => {
    if (mediaType !== 'tv' || !showDetails || !season) return;
    const controller = new AbortController();
    fetch(`/api/tmdb/tv/${id}/season/${season}`, { signal: controller.signal })
      .then(r => r.json())
      .then(data => {
        seasonEpisodes = data.episodes || [];
      })
      .catch(() => {});
    return () => controller.abort();
  });

  function findNextSeason() {
    if (!showDetails?.seasons) return null;
    // TMDB can return seasons out of order (especially with specials and
    // newly-added seasons). Sort ascending by season_number so we
    // always pick the immediate successor (e.g. 1 → 2, not 1 → 5).
    const sorted = [...showDetails.seasons]
      .filter((s: any) => s.season_number > 0 && s.episode_count > 0)
      .sort((a: any, b: any) => a.season_number - b.season_number);
    return sorted.find((s: any) => s.season_number > season) ?? null;
  }

  function findPrevSeason() {
    if (!showDetails?.seasons) return null;
    const sorted = [...showDetails.seasons]
      .filter((s: any) => s.season_number > 0 && s.episode_count > 0)
      .sort((a: any, b: any) => b.season_number - a.season_number);
    return sorted.find((s: any) => s.season_number < season);
  }

  function getPrevEpisode() {
    if (episode > 1) return { season, episode: episode - 1 };
    const ps = findPrevSeason();
    if (ps) return { season: ps.season_number, episode: ps.episode_count };
    return null;
  }

  function goToPrevEpisode() {
    const prev = getPrevEpisode();
    if (!prev) return;
    season = prev.season;
    episode = prev.episode;
    resumeTime = 0;
    episodeKey++;
    const url = new URL(window.location.href);
    url.searchParams.set('season', String(season));
    url.searchParams.set('episode', String(episode));
    window.history.replaceState({}, '', url.toString());
    document.title = `${title} - Watchfy`;
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
    resumeTime = 0;
    episodeKey++;

    const url = new URL(window.location.href);
    url.searchParams.set('season', String(season));
    url.searchParams.set('episode', String(episode));
    window.history.replaceState({}, '', url.toString());
    document.title = `${title} - Watchfy`;
  }

  function navigateToEpisode(ep: number) {
    episode = ep;
    resumeTime = 0;
    episodeKey++;
    const url = new URL(window.location.href);
    url.searchParams.set('season', String(season));
    url.searchParams.set('episode', String(ep));
    window.history.replaceState({}, '', url.toString());
    document.title = `${title} - Watchfy`;
  }

  function navigateToSeason(s: number) {
    season = s;
    episode = 1;
    resumeTime = 0;
    episodeKey++;
    const url = new URL(window.location.href);
    url.searchParams.set('season', String(season));
    url.searchParams.set('episode', String(episode));
    window.history.replaceState({}, '', url.toString());
    document.title = `${title} - Watchfy`;
  }

  function switchServer(nextServer: string) {
    if (nextServer === activeServer) return;
    activeServer = nextServer;
    resumeTime = _lastKnownTime;
    episodeKey++;
    const url = new URL(window.location.href);
    url.searchParams.set('server', nextServer);
    window.history.replaceState({}, '', url.toString());
  }

  let _shareResetTimer: ReturnType<typeof setTimeout> | null = null;

  async function shareCurrentWatch() {
    try {
      await navigator.clipboard.writeText(window.location.href);
      shareCopied = true;
      if (_shareResetTimer) clearTimeout(_shareResetTimer);
      _shareResetTimer = setTimeout(() => {
        shareCopied = false;
        _shareResetTimer = null;
      }, 1800);
    } catch {
      shareCopied = false;
    }
  }

  let resumeTime = $state(0);
  let episodeKey = $state(0);
  let _lastPostTs = 0;
  let _initialized = $state(false);
  let _lastKnownTime = 0;

  async function saveProgressToBackend(currentTime: number, duration: number) {
    try {
      const token = localStorage.getItem('watchfy_token');
      if (!token) return;
      const now = Date.now();
      if (now - _lastPostTs < 5000) return; // debounce 5s
      _lastPostTs = now;
      await fetch('/continue-watching/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({
          tmdb_id: Number(id),
          media_type: mediaType,
          season,
          episode,
          current_time: currentTime,
          duration: duration,
        }),
      });
    } catch {}
  }

  // Tracks in-flight async work so we can abort it on unmount and so the
  // resume logic can cancel the prior fetch when a new mount starts.
  let _resumeAbort: AbortController | null = null;

  onMount(() => {
    activeServer = server;
    const params = new URLSearchParams(window.location.search);
    season = parseInt(params.get('season') || '1');
    episode = parseInt(params.get('episode') || '1');

    tmdbApi.details(mediaType, Number(id))
      .then((data: any) => {
        showDetails = data;
        document.title = `${data.name || data.title || 'Stream'} - Watchfy`;
      })
      .catch(() => {});

    window.addEventListener('popstate', syncFromUrl);

    // Resume-from-saved runs in the same onMount hook so its execution
    // order relative to the URL parse and showDetails fetch is explicit.
    (async () => {
      _resumeAbort?.abort();
      _resumeAbort = new AbortController();
      const signal = _resumeAbort.signal;

      // First: check backend continue-watching for saved season/episode
      try {
        const hasExplicitEpisode = params.has('season') || params.has('episode');
        const token = localStorage.getItem('watchfy_token');
        if (token) {
          const res = await fetch('/continue-watching/', {
            headers: { 'Authorization': `Bearer ${token}` },
            signal,
          });
          if (res.ok) {
            const items = await res.json();
            const match = items.find((i: any) => i.tmdb_id === Number(id));
            if (match && mediaType === 'tv' && (match.season || match.episode)) {
              const savedSeason = match.season || 1;
              const savedEpisode = match.episode || 1;
              if (!hasExplicitEpisode && (savedSeason !== season || savedEpisode !== episode)) {
                season = savedSeason;
                episode = savedEpisode;
                resumeTime = match.current_time > 5 ? match.current_time : 0;
                episodeKey++;
                const url = new URL(window.location.href);
                url.searchParams.set('season', String(season));
                url.searchParams.set('episode', String(episode));
                window.history.replaceState({}, '', url.toString());
              } else if (match.current_time > 5) {
                resumeTime = match.current_time;
              }
            } else if (match && mediaType === 'movie' && match.current_time > 5) {
              resumeTime = match.current_time;
            }
          }
        }
      } catch (err) {
        if ((err as { name?: string })?.name === 'AbortError') return;
      }
      // Fallback: scan localStorage for the latest saved episode of this show
      try {
        const hasExplicitEpisode = params.has('season') || params.has('episode');
        const prefix = `watchfy:${mediaType}:${id}:`;
        let bestKey = '';
        let bestS = 0, bestE = 0, bestTimestamp = 0;
        for (let i = 0; i < localStorage.length; i++) {
          const key = localStorage.key(i);
          if (!key || !key.startsWith(prefix)) continue;
          try {
            const parts = key.split(':');
            const s = Number(parts[3]);
            const e = Number(parts[4]);
            const data = JSON.parse(localStorage.getItem(key) || '{}');
            const timestamp = Number(data.timestamp || 0);
            if (data.currentTime && data.currentTime > 5 && timestamp >= bestTimestamp) {
              bestKey = key;
              bestS = s;
              bestE = e;
              bestTimestamp = timestamp;
            }
          } catch {}
        }
        if (bestKey) {
          const data = JSON.parse(localStorage.getItem(bestKey) || '{}');
          if (!hasExplicitEpisode && (bestS !== season || bestE !== episode)) {
            season = bestS;
            episode = bestE;
            const url = new URL(window.location.href);
            url.searchParams.set('season', String(season));
            url.searchParams.set('episode', String(episode));
            window.history.replaceState({}, '', url.toString());
            episodeKey++;
          }
          resumeTime = data.currentTime || 0;
        }
      } catch {}
      if (!signal.aborted) _initialized = true;
    })();
  });

  onDestroy(() => {
    if (typeof window !== 'undefined') {
      window.removeEventListener('popstate', syncFromUrl);
    }
    _resumeAbort?.abort();
    if (_shareResetTimer) {
      clearTimeout(_shareResetTimer);
      _shareResetTimer = null;
    }
  });

  let upnextItems: any[] = $state([]);

  $effect(() => {
    if (mediaType !== 'movie' || !showDetails) return;
    const controller = new AbortController();
    tmdbApi.recommendations('movie', id)
      .then((data: any) => { upnextItems = (data.results || []).slice(0, 6); })
      .catch(() => {});
    return () => controller.abort();
  });

  const servers = [
    { id: 'white', label: 'White' },
    { id: 'black', label: 'Black' },
  ];
</script>

<div class="relative min-h-screen overflow-hidden bg-surface-0 text-ink font-sans antialiased">
  {#if backdropUrl}
    <div class="pointer-events-none absolute inset-x-0 top-0 h-[520px] opacity-30">
      <img src={backdropUrl} alt="" class="h-full w-full object-cover blur-sm scale-105" />
      <div class="absolute inset-0 bg-gradient-to-b from-surface-0/40 via-surface-0/90 to-surface-0"></div>
      <div class="absolute inset-0 bg-gradient-to-r from-surface-0 via-transparent to-surface-0"></div>
    </div>
  {/if}

  <div class="relative mx-auto max-w-[1800px] px-3 py-4 sm:px-5 lg:px-8 lg:py-6">
    <div class="grid grid-cols-1 gap-5 xl:grid-cols-[minmax(0,1fr)_420px] 2xl:grid-cols-[minmax(0,1fr)_460px]">
      <section class="min-w-0 space-y-5">
        <div class="overflow-hidden rounded-2xl border border-white/[0.06] bg-black shadow-4">
          {#if _initialized}
            <HLSPlayer
              src={streamUrl}
              title={mediaType === 'tv' ? `${title} - ${epBadge}` : title}
              autoPlay={true}
              server={activeServer}
              startTime={resumeTime}
              onPrev={hasPrevEpisode ? goToPrevEpisode : undefined}
              onNext={hasNextEpisode ? goToNextEpisode : undefined}
              onProgress={(data) => {
                _lastKnownTime = data.currentTime;
                const watchKey = `watchfy:${mediaType}:${id}:${season}:${episode}`;
                try {
                  localStorage.setItem(watchKey, JSON.stringify({
                    currentTime: data.currentTime,
                    duration: data.duration,
                    timestamp: Date.now(),
                    title: showDetails?.title || showDetails?.name || title,
                    poster: showDetails?.poster_path,
                    mediaType,
                    tmdbId: id,
                    season,
                    episode,
                  }));
                } catch {}
                saveProgressToBackend(data.currentTime, data.duration);
              }}
            />
          {:else}
            <div class="aspect-video w-full flex flex-col items-center justify-center bg-surface-0 text-sm font-medium text-ink-muted">
              <div class="w-10 h-10 rounded-2xl border-2 border-white/[0.08] border-t-brand-red animate-spin mb-3"></div>
              Preparing playback…
            </div>
          {/if}
        </div>

        <div class="grid gap-4 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-start">
          <div class="min-w-0">
            <div class="mb-3 flex flex-wrap items-center gap-2 text-[11px] font-bold uppercase tracking-wide text-ink-muted">
              {#if mediaType === 'tv'}
                <span class="rounded-md border border-brand-red/25 bg-brand-red/[0.08] px-2 py-1 text-brand-red">{epBadge}</span>
              {/if}
              <span class="rounded-md border border-white/[0.06] bg-white/[0.04] px-2 py-1 text-ink-secondary">{matchLabel}</span>
              {#if year}<span class="rounded-md border border-white/[0.06] bg-white/[0.04] px-2 py-1 text-ink-secondary">{year}</span>{/if}
              {#if runtimeLabel}<span class="rounded-md border border-white/[0.06] bg-white/[0.04] px-2 py-1 text-ink-secondary">{runtimeLabel}</span>{/if}
            </div>

            <h1 class="text-2xl font-display font-black tracking-tighter text-ink sm:text-3xl lg:text-4xl">
              {watchHeading}
            </h1>

            {#if mediaType === 'tv'}
              <a href={`/${mediaType}/${id}`} class="mt-2 inline-flex max-w-full text-sm font-semibold text-ink-muted hover:text-ink transition-colors">
                <span class="truncate">{title}</span>
              </a>
            {/if}
          </div>

          <div class="flex flex-wrap items-center gap-2 lg:justify-end">
            <div class="inline-flex rounded-xl border border-white/[0.06] bg-white/[0.04] p-1">
              {#each servers as option}
                <button
                  onclick={() => switchServer(option.id)}
                  class="h-9 rounded-lg px-3 text-xs font-bold transition-all duration-200 ease-exo-out {activeServer === option.id ? 'bg-ink text-surface-0 shadow-2' : 'text-ink-muted hover:bg-white/[0.06] hover:text-ink'}"
                  aria-pressed={activeServer === option.id}
                >
                  {option.label}
                </button>
              {/each}
            </div>

            <button onclick={shareCurrentWatch} class="inline-flex h-10 items-center gap-2 rounded-xl border border-white/[0.06] bg-white/[0.04] px-4 text-sm font-bold text-ink transition-all duration-200 ease-exo-out hover:bg-white/[0.08] hover:border-white/10 active:scale-95">
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="h-4 w-4">
                <path stroke-linecap="round" stroke-linejoin="round" d="M7.217 10.907a2.25 2.25 0 1 0 0 2.186m0-2.186c.18.324.283.696.283 1.093s-.103.77-.283 1.093m0-2.186 9.566-5.314m-9.566 7.5 9.566 5.314" />
              </svg>
              {shareCopied ? 'Copied' : 'Share'}
            </button>
          </div>
        </div>

        <div class="rounded-2xl border border-white/[0.06] bg-white/[0.03] backdrop-blur-md p-4 sm:p-5">
          <p class="max-w-4xl text-sm leading-6 text-ink-secondary">
            {currentEpisodeData?.overview || showDetails?.overview || 'No description available.'}
          </p>
        </div>
      </section>

      <aside class="min-w-0 xl:sticky xl:top-5 xl:max-h-[calc(100vh-2.5rem)]">
        {#if mediaType === 'tv'}
          <EpisodeSidebar
            {id}
            seasons={seasonsList}
            selectedSeason={season}
            episodes={seasonEpisodes}
            currentEpisode={{ season, episode }}
            onSeasonChange={(s: number) => navigateToSeason(s)}
            onEpisodeClick={(ep: number) => navigateToEpisode(ep)}
          />
        {:else}
          <div class="surface-elevated rounded-2xl p-3">
            <div class="mb-3 flex items-center justify-between px-1">
              <h2 class="text-sm font-black uppercase tracking-wide text-ink">Up Next</h2>
              <a href={`/${mediaType}/${id}`} class="text-xs font-semibold text-ink-muted hover:text-ink transition-colors">Details</a>
            </div>
            <div class="flex flex-col gap-2">
              {#each upnextItems as item}
                <a href={`/movie/${item.id}`} class="group flex gap-3 rounded-xl p-2 transition-all duration-200 ease-exo-out hover:bg-white/[0.04]">
                  <div class="relative aspect-video w-36 shrink-0 overflow-hidden rounded-lg bg-surface-1">
                    {#if item.backdrop_path || item.poster_path}
                      <img src={tmdbImg(item.backdrop_path || item.poster_path, item.backdrop_path ? 'w300' : 'w185')} alt={item.title || item.name} class="h-full w-full object-cover transition-transform duration-300 ease-exo-out group-hover:scale-105" loading="lazy" />
                    {/if}
                    <div class="absolute bottom-1 right-1 rounded bg-black/80 px-1.5 py-0.5 text-[10px] font-bold text-ink">
                      {item.vote_average ? Math.round(item.vote_average * 10) + '%' : '--'}
                    </div>
                  </div>
                  <div class="min-w-0 flex-1 pt-0.5">
                    <h3 class="line-clamp-2 text-sm font-bold leading-snug text-ink-secondary group-hover:text-ink transition-colors">
                      {item.title || item.name}
                    </h3>
                    <p class="mt-1 truncate text-xs font-medium text-ink-subtle">
                      {(item.release_date || item.first_air_date || '').split('-')[0] || 'Watchfy'}
                    </p>
                    <p class="mt-1 text-xs text-ink-muted">Recommended after this</p>
                  </div>
                </a>
              {/each}
            </div>
            {#if upnextItems.length === 0}
              <div class="px-1 pt-2">
                <EmptyState
                  compact
                  icon="film"
                  title="No recommendations yet"
                  message="TMDB hasn't suggested similar titles for this one yet."
                />
              </div>
            {/if}
          </div>
        {/if}
      </aside>
    </div>
  </div>
</div>
