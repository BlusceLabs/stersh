<script lang="ts">
  import { onMount } from 'svelte';
  import HLSPlayer from './HLSPlayer.svelte';
  import EpisodeSidebar from './EpisodeSidebar.svelte';
  import { tmdbApi, api } from '../lib/api';

  let { media = 'movie', id = '0', server = 'white' } = $props();

  let season = $state(1);
  let episode = $state(1);
  let showDetails: any = $state(null);
  let seasonEpisodes: any[] = $state([]);

  let mediaType = $derived(media === 'tv' ? 'tv' : 'movie');
  let currentSeasonData = $derived(
    showDetails?.seasons?.find((s: any) => s.season_number === season)
  );
  let totalEpisodes = $derived(currentSeasonData?.episode_count ?? 0);
  let hasNextEpisode = $derived(mediaType === 'tv' && showDetails && episode < totalEpisodes);
  let hasPrevEpisode = $derived(mediaType === 'tv' && showDetails && (episode > 1 || findPrevSeason() !== null));
  let streamUrl = $derived(api.getStreamSource(Number(id), mediaType, season, episode, server));
  let title = $derived(showDetails?.name || showDetails?.title || 'Now Playing');
  let year = $derived((showDetails?.release_date || '').split('-')[0]);
  let epBadge = $derived(mediaType === 'tv' ? `S${season}:E${episode}` : year);
  let seasonsList = $derived(
    (showDetails?.seasons || []).filter((s: any) => s.season_number > 0 && s.episode_count > 0)
  );

  function tmdbImg(path: string, size: string = 'w185'): string {
    if (!path) return '';
    return `https://image.tmdb.org/t/p/${size}${path}`;
  }

  onMount(() => {
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
  });

  function syncFromUrl() {
    const params = new URLSearchParams(window.location.search);
    season = parseInt(params.get('season') || '1');
    episode = parseInt(params.get('episode') || '1');
  }

  $effect(() => {
    if (mediaType !== 'tv' || !showDetails || !season) return;
    fetch(`/api/tmdb/tv/${id}/season/${season}`)
      .then(r => r.json())
      .then(data => {
        seasonEpisodes = data.episodes || [];
      })
      .catch(() => {});
  });

  function findNextSeason() {
    return showDetails?.seasons?.find(
      (s: any) => s.season_number > season && s.episode_count > 0
    );
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

  let resumeTime = $state(0);
  let episodeKey = $state(0);
  let _lastPostTs = 0;

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
          current_time: currentTime,
          duration: duration,
        }),
      });
    } catch {}
  }

  $effect(() => {
    (async () => {
      // First: check backend continue-watching for saved season/episode
      try {
        const token = localStorage.getItem('watchfy_token');
        console.log('[WatchUI] token:', !!token, 'id:', id, 'mediaType:', mediaType, 'season:', season, 'episode:', episode);
        if (token) {
          const res = await fetch('/continue-watching/', {
            headers: { 'Authorization': `Bearer ${token}` },
          });
          console.log('[WatchUI] continue-watching status:', res.status);
          if (res.ok) {
            const items = await res.json();
            console.log('[WatchUI] continue-watching items:', JSON.stringify(items));
            const match = items.find((i: any) => i.tmdb_id === Number(id));
            console.log('[WatchUI] match:', match ? JSON.stringify(match) : 'NOT FOUND');
            if (match && mediaType === 'tv' && (match.season || match.episode)) {
              // Navigate to the saved episode if different from current
              const savedSeason = match.season || 1;
              const savedEpisode = match.episode || 1;
              console.log(`[WatchUI] Navigating to saved S${savedSeason}E${savedEpisode}`);
              if (savedSeason !== season || savedEpisode !== episode) {
                season = savedSeason;
                episode = savedEpisode;
                resumeTime = match.current_time > 5 ? match.current_time : 0;
                episodeKey++;
                const url = new URL(window.location.href);
                url.searchParams.set('season', String(season));
                url.searchParams.set('episode', String(episode));
                window.history.replaceState({}, '', url.toString());
                console.log('[WatchUI] Navigated to', url.toString());
                return;
              }
              if (match.current_time > 5) {
                resumeTime = match.current_time;
                console.log('[WatchUI] Resuming at', resumeTime);
                return;
              }
            }
            if (match && mediaType === 'movie' && match.current_time > 5) {
              resumeTime = match.current_time;
              console.log('[WatchUI] Movie resume at', resumeTime);
              return;
            }
          }
        }
      } catch (e) {
        console.error('[WatchUI] continue-watching error:', e);
      }
      // Fallback: scan localStorage for the latest saved episode of this show
      try {
        const prefix = `watchfy:${mediaType}:${id}:`;
        let bestKey = '';
        let bestS = 0, bestE = 0;
        for (let i = 0; i < localStorage.length; i++) {
          const key = localStorage.key(i);
          if (!key || !key.startsWith(prefix)) continue;
          try {
            const parts = key.split(':');
            const s = Number(parts[3]);
            const e = Number(parts[4]);
            if (s > bestS || (s === bestS && e > bestE)) {
              const data = JSON.parse(localStorage.getItem(key) || '{}');
              if (data.currentTime && data.currentTime > 5) {
                bestKey = key;
                bestS = s;
                bestE = e;
              }
            }
          } catch {}
        }
        if (bestKey) {
          const data = JSON.parse(localStorage.getItem(bestKey) || '{}');
          console.log('[WatchUI] localStorage found:', bestS, 'x', bestE, 'time:', data.currentTime);
          if (bestS !== season || bestE !== episode) {
            season = bestS;
            episode = bestE;
            const url = new URL(window.location.href);
            url.searchParams.set('season', String(season));
            url.searchParams.set('episode', String(episode));
            window.history.replaceState({}, '', url.toString());
            episodeKey++;
            console.log('[WatchUI] Navigated to', url.toString());
          }
          resumeTime = data.currentTime || 0;
        }
      } catch (e) {
        console.error('[WatchUI] localStorage error:', e);
      }
    })();
  });

  let upnextItems: any[] = $state([]);

  $effect(() => {
    if (mediaType !== 'movie' || !showDetails) return;
    tmdbApi.recommendations('movie', id)
      .then((data: any) => { upnextItems = (data.results || []).slice(0, 6); })
      .catch(() => {});
  });

  // State mimicking YouTube interactive actions
  let likes = $state(4205);
  let liked = $state(false);
  let disliked = $state(false);
  let isSubscribed = $state(false);

  function toggleLike() {
    if (disliked) disliked = false;
    liked = !liked;
    likes += liked ? 1 : -1;
  }

  function toggleDislike() {
    if (liked) {
      liked = false;
      likes -= 1;
    }
    disliked = !disliked;
  }
</script>

<div class="min-h-screen bg-[#0f0f0f] text-[#f1f1f1] font-sans antialiased selection:bg-white/20">
  <div class="py-6">
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
      
      <div class="lg:col-span-2 space-y-3">
        <div class="w-full aspect-video rounded-xl overflow-hidden bg-black shadow-lg relative group">
          <HLSPlayer
            key={String(episodeKey)}
            src={streamUrl}
            title={title}
            autoPlay={true}
            {server}
            startTime={resumeTime}
            onPrev={hasPrevEpisode ? goToPrevEpisode : undefined}
            onNext={hasNextEpisode ? goToNextEpisode : undefined}
            onProgress={(data) => {
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
        </div>

        <div>
          <h1 class="text-xl font-bold tracking-tight leading-7 break-words line-clamp-2 pt-1 text-white">
            {#if mediaType === 'tv'}<span class="text-zinc-400 font-normal mr-1">[{epBadge}]</span>{/if}{title}
          </h1>
          
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mt-2 pb-1">
            <div class="flex items-center space-x-3">
              <a href={`/${mediaType}/${id}`} class="flex-shrink-0">
                <img
                  src={tmdbImg(showDetails?.poster_path, 'w92')}
                  alt={title}
                  class="w-10 h-10 rounded-full object-cover bg-zinc-800 border border-zinc-800"
                />
              </a>
              <div class="flex flex-col min-w-0 pr-2">
                <a href={`/${mediaType}/${id}`} class="text-[16px] font-bold text-white hover:text-zinc-200 truncate leading-snug">
                  {title}
                </a>
                <span class="text-xs text-[#aaa] truncate leading-none mt-1">
                  {showDetails?.number_of_seasons ? `${showDetails.number_of_seasons} Seasons` : 'Movie'} • Verified
                </span>
              </div>
              <button 
                onclick={() => isSubscribed = !isSubscribed}
                class="h-9 px-4 rounded-full text-sm font-semibold transition-all duration-200 active:scale-95 ml-2 shrink-0
                  {isSubscribed ? 'bg-white/10 hover:bg-white/20 text-white' : 'bg-[#f1f1f1] hover:bg-[#d9d9d9] text-black'}"
              >
                {isSubscribed ? 'Subscribed' : 'Subscribe'}
              </button>
            </div>

            <div class="flex items-center gap-2 overflow-x-auto no-scrollbar sm:ml-auto">
              <div class="inline-flex items-center bg-white/10 hover:bg-white/15 rounded-full h-9 transition-colors overflow-hidden">
                <button onclick={toggleLike} class="flex items-center gap-2 h-full pl-4 pr-3 border-r border-white/10 hover:bg-white/5 transition-colors text-sm font-semibold text-white active:scale-95">
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill={liked ? 'currentColor' : 'none'} stroke="currentColor" stroke-width="2" class="w-5 h-5">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M6.633 10.25c.806 0 1.533-.446 2.031-1.08a9.041 9.041 0 0 1 2.861-2.4c.723-.384 1.35-.956 1.653-1.715a4.498 4.498 0 0 0 .322-1.672V2.75a.75.75 0 0 1 .75-.75 2.25 2.25 0 0 1 2.25 2.25c0 1.152-.26 2.243-.723 3.218-.266.558.107 1.282.725 1.282m0 0h3.126c1.026 0 1.945.694 2.054 1.715.045.422.068.85.068 1.285a11.95 11.95 0 0 1-2.649 7.521c-.388.482-.987.729-1.605.729H14.23c-.483 0-.964-.078-1.423-.23l-3.114-1.04a4.501 4.501 0 0 0-1.423-.23H5.904m10.598-9.75H14.25M5.904 18.5c.083.205.173.405.27.602.197.4-.078.898-.523.898h-.908c-.889 0-1.713-.518-1.972-1.368a12 12 0 0 1-.521-3.507c0-1.553.295-3.036.831-4.398C3.387 9.953 4.167 9.5 5 9.5h1.053c.472 0 .745.556.5.96a8.958 8.958 0 0 0-1.302 4.665c0 1.194.232 2.333.654 3.375Z" />
                  </svg>
                  <span>{likes.toLocaleString()}</span>
                </button>
                <button onclick={toggleDislike} class="flex items-center h-full px-3.5 hover:bg-white/5 transition-colors text-white active:scale-95" aria-label="Dislike video">
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill={disliked ? 'currentColor' : 'none'} stroke="currentColor" stroke-width="2" class="w-5 h-5 transform rotate-180">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M6.633 10.25c.806 0 1.533-.446 2.031-1.08a9.041 9.041 0 0 1 2.861-2.4c.723-.384 1.35-.956 1.653-1.715a4.498 4.498 0 0 0 .322-1.672V2.75a.75.75 0 0 1 .75-.75 2.25 2.25 0 0 1 2.25 2.25c0 1.152-.26 2.243-.723 3.218-.266.558.107 1.282.725 1.282m0 0h3.126c1.026 0 1.945.694 2.054 1.715.045.422.068.85.068 1.285a11.95 11.95 0 0 1-2.649 7.521c-.388.482-.987.729-1.605.729H14.23c-.483 0-.964-.078-1.423-.23l-3.114-1.04a4.501 4.501 0 0 0-1.423-.23H5.904m10.598-9.75H14.25M5.904 18.5c.083.205.173.405.27.602.197.4-.078.898-.523.898h-.908c-.889 0-1.713-.518-1.972-1.368a12 12 0 0 1-.521-3.507c0-1.553.295-3.036.831-4.398C3.387 9.953 4.167 9.5 5 9.5h1.053c.472 0 .745.556.5.96a8.958 8.958 0 0 0-1.302 4.665c0 1.194.232 2.333.654 3.375Z" />
                  </svg>
                </button>
              </div>
              <button onclick={() => navigator.clipboard.writeText(window.location.href)} class="flex items-center gap-2 h-9 px-4 rounded-full bg-white/10 hover:bg-white/15 text-sm font-semibold text-white transition-colors active:scale-95 shrink-0">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-5 h-5">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M7.217 10.907a2.25 2.25 0 1 0 0 2.186m0-2.186c.18.324.283.696.283 1.093s-.103.77-.283 1.093m0-2.186 9.566-5.314m-9.566 7.5 9.566 5.314m0 0a2.25 2.25 0 1 0 3.935 2.186 2.25 2.25 0 0 0-3.935-2.186Zm0-12.814a2.25 2.25 0 1 0 3.933-2.185 2.25 2.25 0 0 0-3.933 2.185Z" />
                </svg>
                <span>Share</span>
              </button>
              <button class="flex items-center justify-center w-9 h-9 rounded-full bg-white/10 hover:bg-white/15 text-white active:scale-95 shrink-0">
                <svg xmlns="http://www.w3.org/2000/svg" fill="currentColor" viewBox="0 0 24 24" class="w-5 h-5">
                  <path d="M12 8c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2zm0 2c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2zm0 6c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2z"/>
                </svg>
              </button>
            </div>
          </div>
        </div>

        <div class="bg-white/10 hover:bg-white/[0.15] cursor-pointer rounded-xl p-3 text-sm text-[#f1f1f1] transition-colors leading-relaxed">
          <div class="flex flex-wrap items-center gap-x-2.5 font-bold text-white mb-1.5">
            <span>{showDetails?.vote_average ? `${(showDetails.vote_average * 10).toFixed(0)}% Match` : '98% Rating'}</span>
            <span>•</span>
            <span>{showDetails?.release_date?.split('-')[0] || showDetails?.first_air_date?.split('-')[0] || '2026'}</span>
            <span>•</span>
            <span class="text-zinc-400 font-normal">#StreamingTrend #Watchfy</span>
          </div>
          <p class="text-[#f1f1f1] whitespace-pre-line break-words text-sm font-normal">
            {showDetails?.overview || 'No description available.'}
          </p>
        </div>
      </div>

      <div class="w-full space-y-4">
        {#if mediaType === 'tv'}
          <div class="rounded-xl overflow-hidden bg-transparent">
            <EpisodeSidebar
              {id}
              seasons={seasonsList}
              bind:selectedSeason={season}
              episodes={seasonEpisodes}
              currentEpisode={{ season, episode }}
              onSeasonChange={(s: number) => navigateToSeason(s)}
              onEpisodeClick={(ep: number) => navigateToEpisode(ep)}
            />
          </div>
        {:else}
          <div class="space-y-3">
            <p class="text-sm font-bold text-white tracking-wide">Up Next</p>
            <div class="flex flex-col gap-2">
              {#each upnextItems as item}
                <a href={`/movie/${item.id}`} class="flex gap-2 group cursor-pointer rounded-lg hover:bg-white/5 p-1 -mx-1 transition-colors">
                  <div class="w-40 h-24 rounded-lg flex-shrink-0 relative overflow-hidden bg-zinc-800">
                    {#if item.poster_path}
                      <img src={tmdbImg(item.poster_path, 'w185')} alt={item.title} class="w-full h-full object-cover" loading="lazy" />
                    {/if}
                    <div class="absolute bottom-1 right-1 bg-black/80 px-1 text-[10px] font-bold rounded text-white tracking-widest">
                      {item.vote_average ? (item.vote_average * 10).toFixed(0) + '%' : '--'}
                    </div>
                  </div>
                  <div class="flex flex-col min-w-0 flex-1">
                    <h4 class="text-sm font-bold text-white line-clamp-2 leading-tight group-hover:text-zinc-200 transition-colors">
                      {item.title || item.name}
                    </h4>
                    <p class="text-xs text-zinc-400 mt-1 truncate">
                      {(item.release_date || item.first_air_date || '').split('-')[0] || 'Watchfy'}
                    </p>
                    <p class="text-xs text-zinc-500 mt-0.5">
                      {(item.vote_average * 10).toFixed(0)}% match
                    </p>
                  </div>
                </a>
              {:else}
                <div class="flex flex-col items-center justify-center text-center py-8 text-zinc-500">
                  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6 mb-2 text-zinc-600">
                    <path stroke-linecap="round" stroke-linejoin="round" d="m15.75 10.5 4.72-4.72a.75.75 0 0 1 1.28.53v11.38a.75.75 0 0 1-1.28.53l-4.72-4.72M4.5 18.75h9a2.25 2.25 0 0 0 2.25-2.25v-9a2.25 2.25 0 0 0-2.25-2.25h-9A2.25 2.25 0 0 0 2.25 7.5v9a2.25 2.25 0 0 0 2.25 2.25Z" />
                  </svg>
                  <p class="text-xs font-medium">No recommendations available</p>
                </div>
              {/each}
            </div>
          </div>
        {/if}
      </div>

    </div>
  </div>
</div>

<style>
  :global(.no-scrollbar::-webkit-scrollbar) {
    display: none;
  }
  :global(.no-scrollbar) {
    -ms-overflow-style: none;
    scrollbar-width: none;
  }
</style>