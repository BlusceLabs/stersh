<script lang="ts">
  import { onDestroy, onMount } from 'svelte';
  import HLSPlayer from './HLSPlayer.svelte';
  import EpisodeSidebar from './EpisodeSidebar.svelte';
  import { tmdbApi, api } from '../lib/api';
  import { getToken, authFetch } from '../lib/auth';

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
  let descriptionExpanded = $state(false);

  async function saveProgressToBackend(currentTime: number, duration: number) {
    try {
      const token = getToken();
      if (!token) return;
      const now = Date.now();
      if (now - _lastPostTs < 5000) return;
      _lastPostTs = now;
      await authFetch('/continue-watching/', {
        method: 'POST',
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
        const token = getToken();
        if (token) {
          const res = await authFetch('/continue-watching/', { signal });
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

<div class="min-h-screen bg-base text-ink font-sans antialiased">
  <div class="max-w-[1800px] mx-auto px-3 sm:px-4 lg:px-6 py-4 lg:py-6">
    <div class="grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,1fr)_402px]">
      <section class="min-w-0 space-y-4">
        <!-- Player -->
        <div class="overflow-hidden rounded-xl bg-black">
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
            <div class="aspect-video w-full flex flex-col items-center justify-center bg-base text-sm font-medium">
              <div class="w-10 h-10 border-2 border-white/20 border-t-white rounded-full animate-spin mb-3"></div>
              <span class="text-ink">Loading...</span>
            </div>
          {/if}
        </div>

        <!-- Title + actions row -->
        <div class="flex flex-col gap-3">
          <h1 class="text-xl md:text-2xl font-bold text-ink leading-tight">
            {watchHeading}
          </h1>

          <div class="flex flex-wrap items-center justify-between gap-3">
            <div class="flex items-center gap-3 min-w-0">
              {#if mediaType === 'tv'}
                <a href={`/${mediaType}/${id}`} class="flex items-center gap-3 min-w-0 group">
                  <div class="w-10 h-10 rounded-full bg-base-3 flex-shrink-0 flex items-center justify-center text-sm font-medium text-ink">
                    {title.charAt(0).toUpperCase()}
                  </div>
                  <div class="min-w-0">
                    <p class="text-sm font-medium text-ink group-hover:text-white truncate">{title}</p>
                    <p class="text-xs text-ink-muted">{epBadge} · {matchLabel}</p>
                  </div>
                </a>
              {:else}
                <div>
                  <p class="text-sm text-ink-muted">{matchLabel} · {year || ''} {runtimeLabel ? `· ${runtimeLabel}` : ''}</p>
                </div>
              {/if}
            </div>

            <div class="flex flex-wrap items-center gap-2">
              <div class="inline-flex bg-base-2 rounded-full p-0.5">
                {#each servers as option}
                  <button
                    onclick={() => switchServer(option.id)}
                    class="h-8 rounded-full px-3 text-xs font-medium transition-colors duration-100
                      {activeServer === option.id
                        ? 'bg-white text-base'
                        : 'text-ink-secondary hover:text-ink'}"
                    aria-pressed={activeServer === option.id}
                  >
                    {option.label}
                  </button>
                {/each}
              </div>
              <button onclick={shareCurrentWatch} class="yt-icon-btn" aria-label="Share" title="Share">
                <svg viewBox="0 0 24 24" class="w-5 h-5" fill="currentColor" aria-hidden="true">
                  <path d="M15 8a3 3 0 1 0-2.83-4H15L12 1 9 4h.83A3 3 0 0 0 12 10a3 3 0 0 0 3-2zM4 13a3 3 0 0 1 2-2.83V13l-2 1l-1-1H4zm11 4a3 3 0 1 0-2.83 4h.83l-3-3l1-1l1 1v-.83A3 3 0 0 0 15 17zm6-4h-1l-1 1l-2-1v-2.83A3 3 0 0 1 21 13z" />
                </svg>
              </button>
            </div>
          </div>
        </div>

        <!-- Description -->
        <div class="p-3 bg-base-2 rounded-xl text-sm text-ink leading-relaxed">
          <p class={descriptionExpanded ? '' : 'line-clamp-3'}>
            {currentEpisodeData?.overview || showDetails?.overview || 'No description available.'}
          </p>
          {#if (currentEpisodeData?.overview || showDetails?.overview || '').length > 200}
            <button onclick={() => descriptionExpanded = !descriptionExpanded} class="text-ink-secondary hover:text-ink text-sm font-medium mt-1">
              {descriptionExpanded ? 'Show less' : '...more'}
            </button>
          {/if}
        </div>
      </section>

      <aside class="min-w-0">
        {#if mediaType === 'tv'}
          <div class="bg-base-1 border border-white/10 rounded-xl overflow-hidden">
            <EpisodeSidebar
              seasons={seasonsList}
              selectedSeason={season}
              episodes={seasonEpisodes}
              currentEpisode={{ season, episode }}
              onSeasonChange={(s: number) => navigateToSeason(s)}
              onEpisodeClick={(ep: number) => navigateToEpisode(ep)}
            />
          </div>
        {:else}
          <div>
            <h2 class="text-base font-medium text-ink mb-3">Up next</h2>
            <div class="flex flex-col gap-2">
              {#each upnextItems as item}
                <a href={`/movie/${item.id}`} class="flex items-start gap-3 p-1 rounded-lg hover:bg-base-2">
                  <div class="relative aspect-video w-40 shrink-0 overflow-hidden rounded-lg bg-base-2">
                    {#if item.backdrop_path || item.poster_path}
                      <img src={tmdbImg(item.backdrop_path || item.poster_path, item.backdrop_path ? 'w300' : 'w185')} alt={item.title || item.name} class="h-full w-full object-cover" loading="lazy" />
                    {/if}
                  </div>
                  <div class="min-w-0 flex-1 py-1">
                    <h3 class="line-clamp-2 text-sm font-medium leading-snug text-ink">
                      {item.title || item.name}
                    </h3>
                    <p class="mt-1 text-xs text-ink-muted">
                      {(item.release_date || item.first_air_date || '').split('-')[0] || ''}
                      {#if item.vote_average} · {Math.round(item.vote_average * 10)}% match{/if}
                    </p>
                  </div>
                </a>
              {/each}
            </div>
            {#if upnextItems.length === 0}
              <p class="text-sm text-ink-muted py-4 text-center">No recommendations yet.</p>
            {/if}
          </div>
        {/if}
      </aside>
    </div>
  </div>
</div>
