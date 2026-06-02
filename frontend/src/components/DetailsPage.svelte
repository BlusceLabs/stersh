<script lang="ts">
  import { tmdbApi } from '../lib/api';
  import DetailSkeleton from './skeletons/DetailSkeleton.svelte';
  import EmptyState from './EmptyState.svelte';
  import MediaRow from './MediaRow.svelte';

  // Props (Svelte 5 Runes)
  let { media = 'movie', id = '0' } = $props<{ media?: string; id?: string }>();

  // Type Interfaces
  interface Genre { id: number; name: string; }
  interface CastMember { name: string; character: string; profile_path: string; }
  interface Episode { name: string; episode_number: number; still_path: string; overview: string; }
  interface Season { season_number: number; episode_count: number; }
  
  interface MediaDetails {
    title?: string;
    name?: string;
    release_date?: string;
    first_air_date?: string;
    vote_average?: number;
    vote_count?: number;
    runtime?: number;
    number_of_seasons?: number;
    seasons?: Season[];
    genres?: Genre[];
    backdrop_path?: string;
    poster_path?: string;
    status?: string;
    tagline?: string;
    overview?: string;
    credits?: { cast: CastMember[] };
    videos?: { results: any[] };
  }

  // Reactive States
  let data = $state<MediaDetails | null>(null);
  let loading = $state(true);
  let error = $state('');
  let selectedSeason = $state(1);
  let seasonEpisodes: Episode[] = $state([]);
  let recommendations: any[] = $state([]);
  let showTrailer = $state(false);
  let myListFlag = $state(false);

  $effect(() => {
    (async () => {
      try {
        const token = localStorage.getItem('watchfy_token');
        if (token) {
          const res = await fetch(`/user/watchlist/${mediaType}/${id}`, {
            headers: { 'Authorization': `Bearer ${token}` },
          });
          if (res.ok) { myListFlag = true; return; }
        }
      } catch {}
      try { myListFlag = localStorage.getItem(`watchfy:mylist:${mediaType}:${id}`) === 'true'; }
      catch { myListFlag = false; }
    })();
  });

  async function toggleMyList() {
    const key = `watchfy:mylist:${mediaType}:${id}`;
    const token = localStorage.getItem('watchfy_token');
    if (token) {
      try {
        if (myListFlag) {
          await fetch(`/user/watchlist/${mediaType}/${id}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` },
          });
          myListFlag = false;
        } else {
          await fetch(`/user/watchlist/${mediaType}/${id}`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` },
          });
          myListFlag = true;
        }
        return;
      } catch {}
    }
    // Fallback to localStorage
    try {
      if (myListFlag) {
        localStorage.removeItem(key);
        myListFlag = false;
      } else {
        localStorage.setItem(key, 'true');
        myListFlag = true;
      }
    } catch {}
  }

  let trailerKey = $derived(
    data?.videos?.results?.find(
      (v: any) => v.site === 'YouTube' && (v.type === 'Trailer' || v.type === 'Teaser')
    )?.key || data?.videos?.results?.[0]?.key || ''
  );

  // Derived Values
  let mediaType: 'movie' | 'tv' = $derived(media === 'tv' ? 'tv' : 'movie');
  let title = $derived(data?.title || data?.name || '');
  let year = $derived((data?.release_date || data?.first_air_date || '').split('-')[0]);
  let rating = $derived(data?.vote_average ? (data.vote_average / 2).toFixed(1) : null);
  let runtime = $derived(
    data?.runtime ? `${Math.floor(data.runtime / 60)}h ${data.runtime % 60}m` : null
  );
  let seasons = $derived(
    (data?.seasons || []).filter((s) => s.season_number > 0 && s.episode_count > 0)
  );
  let cast = $derived((data?.credits?.cast || []).slice(0, 16));
  let genres = $derived(data?.genres || []);
  let backdropUrl = $derived(
    data?.backdrop_path ? `https://image.tmdb.org/t/p/original${data.backdrop_path}` : ''
  );
  let posterUrl = $derived(
    data?.poster_path ? `https://image.tmdb.org/t/p/w500${data.poster_path}` : ''
  );
  let votes = $derived(data?.vote_count || 0);
  let tagline = $derived(data?.tagline || '');

  // Synchronized Data Pipeline
  $effect(() => {
    const currentId = Number(id);
    if (!currentId) return;

    loading = true;
    error = '';
    data = null;
    selectedSeason = 1;
    seasonEpisodes = [];

    tmdbApi.details(mediaType, currentId)
      .then((res: any) => {
        data = res;
        tmdbApi.recommendations(mediaType, currentId)
          .then((r: any) => {
            recommendations = (r.results || [])
              .filter((x: any) => x.poster_path)
              .slice(0, 12)
              .map((x: any) => ({ ...x, media_type: x.media_type || mediaType }));
          })
          .catch(() => {});
      })
      .catch(() => {
        error = 'Unable to synchronize title metadata.';
      })
      .finally(() => {
        loading = false;
      });
  });

  // Episodic Data Monitor
  $effect(() => {
    const currentId = Number(id);
    if (mediaType !== 'tv' || !data || !selectedSeason) return;

    tmdbApi.seasonEpisodes(currentId, selectedSeason)
      .then((res: any) => {
        seasonEpisodes = res.episodes || [];
      })
      .catch(() => {
        seasonEpisodes = [];
      });
  });

  function tmdbImg(path: string, size: string = 'w185'): string {
    return path ? `https://image.tmdb.org/t/p/${size}${path}` : '';
  }

  // Dynamic routing based on media type and context
  function watchUrl(episode?: number): string {
    if (mediaType === 'tv') {
      return `/watch/tv/${id}?season=${selectedSeason}&episode=${episode || 1}`;
    }
    return `/watch/movie/${id}`;
  }
</script>

<svelte:head>
  <title>{title ? `${title} — Watchfy` : 'Loading Details...'}</title>
</svelte:head>

{#if loading}
  <DetailSkeleton />
{:else if error}
  <div class="min-h-screen flex items-center justify-center bg-surface-0 px-4">
    <EmptyState
      variant="error"
      icon="alert"
      title="Something went wrong"
      message={error}
      ctaLabel="Try Again"
      oncTaClick={() => window.location.reload()}
    />
  </div>
{:else}
  <div class="relative min-h-screen bg-surface-0 text-ink overflow-hidden">

    {#if backdropUrl}
      <div class="absolute top-0 left-0 right-0 h-[85vh] w-full z-0 pointer-events-none overflow-hidden">
        <img src={backdropUrl} alt="" class="w-full h-full object-cover brightness-[0.22] scale-105 motion-safe:animate-[kenburns_25s_ease-out_infinite_alternate]" />
        <div class="absolute inset-0 bg-gradient-to-t from-surface-0 via-surface-0/80 to-transparent"></div>
        <div class="absolute inset-0 bg-gradient-to-r from-surface-0 via-surface-0/30 to-transparent"></div>
        <div class="absolute inset-0 bg-gradient-to-b from-surface-0/10 via-transparent to-surface-0"></div>
      </div>
    {/if}

    <div class="relative z-10 max-w-content mx-auto px-4 sm:px-6 lg:px-8 pt-[16vh] md:pt-[24vh] pb-32">
      <div class="grid grid-cols-1 md:grid-cols-[240px_1fr] lg:grid-cols-[300px_1fr] gap-8 lg:gap-14 items-start">

        <div class="w-44 sm:w-56 md:w-full mx-auto md:mx-0 flex-shrink-0 relative group">
          <div class="aspect-[2/3] rounded-2xl overflow-hidden shadow-4 border border-white/[0.06] bg-surface-1 transition-all duration-500 group-hover:border-white/10">
            {#if posterUrl}
              <img src={posterUrl} alt={title} class="w-full h-full object-cover select-none transition-transform duration-500 group-hover:scale-[1.02]" />
            {:else}
              <div class="w-full h-full flex flex-col items-center justify-center text-ink-faint gap-3 relative overflow-hidden">
                <div class="absolute inset-0 bg-gradient-to-br from-surface-1 via-surface-2 to-surface-0"></div>
                <div class="absolute -top-8 -right-8 w-32 h-32 rounded-full bg-brand-red/10 blur-2xl"></div>
                <div class="absolute -bottom-8 -left-8 w-32 h-32 rounded-full bg-brand-purple/10 blur-2xl"></div>
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.25" stroke="currentColor" class="w-12 h-12 relative z-10">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 10.5l4.72-4.72a.75.75 0 011.28.53v11.38a.75.75 0 01-1.28.53l-4.72-4.72M4.5 18.75h9a2.25 2.25 0 002.25-2.25v-9a2.25 2.25 0 00-2.25-2.25h-9A2.25 2.25 0 002.25 7.5v9a2.25 2.25 0 002.25 2.25z" />
                </svg>
                <span class="text-xs tracking-wider font-semibold uppercase opacity-60 relative z-10">No Media Poster</span>
              </div>
            {/if}
          </div>
        </div>

        <div class="text-center md:text-left mt-2 md:mt-0 flex flex-col">
          
          <div class="flex flex-wrap items-center justify-center md:justify-start gap-2 text-[11px] font-bold tracking-wide mb-4">
            <span class="bg-brand-red/[0.08] border border-brand-red/25 text-brand-red px-3 py-1 rounded-lg uppercase font-extrabold tracking-widest shadow-sm shadow-brand-red/5">
              {mediaType === 'tv' ? 'TV Series' : 'Movie'}
            </span>
            {#if year}
              <span class="glass-strong px-3 py-1 rounded-lg text-ink-secondary">{year}</span>
            {/if}
            {#if runtime}
              <span class="glass-strong px-3 py-1 rounded-lg text-ink-secondary">{runtime}</span>
            {/if}
            {#if mediaType === 'tv' && data?.number_of_seasons}
              <span class="glass-strong px-3 py-1 rounded-lg text-ink-secondary">
                {data.number_of_seasons} {data.number_of_seasons === 1 ? 'Season' : 'Seasons'}
              </span>
            {/if}
            {#if rating}
              <span class="glass-strong px-2.5 py-1 rounded-lg flex items-center gap-1.5 text-accent-warm">
                <svg class="w-3.5 h-3.5 fill-accent-warm" viewBox="0 0 20 20"><path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/></svg>
                {rating} <span class="text-ink-subtle text-[10px] font-medium">({votes.toLocaleString()})</span>
              </span>
            {/if}
          </div>

          <h1 class="text-3xl sm:text-4xl lg:text-5xl font-display font-extrabold text-ink tracking-tighter leading-[1.1] mb-2 text-cinematic">
            {title}
          </h1>

          {#if tagline}
            <p class="text-ink-muted text-sm md:text-base font-medium italic mb-5 opacity-90">"{tagline}"</p>
          {/if}

          <div class="flex flex-wrap items-center justify-center md:justify-start gap-1.5 mb-6">
            {#each genres as genre}
              <a href="/search?genre={genre.id}" class="text-[11px] font-semibold px-3 py-1 rounded-full bg-surface-1/40 hover:bg-surface-2/60 text-ink-muted hover:text-ink border border-white/[0.04] hover:border-white/10 transition-all duration-300">
                {genre.name}
              </a>
            {/each}
          </div>

          <div class="flex flex-wrap items-center justify-center md:justify-start gap-3 mb-8">
            <a
              href={watchUrl()}
              class="inline-flex items-center gap-2.5 px-7 py-3.5 bg-brand-gradient-cta text-white text-sm font-bold rounded-xl transition-all duration-300 ease-exo-out hover:brightness-110 active:scale-95 shadow-glow-red select-none"
            >
              <svg class="w-4 h-4 fill-white" viewBox="0 0 20 20"><path d="M6.423 4.167A1 1 0 005 5.035v9.93a1 1 0 001.423.868l8.5-4.965a1 1 0 000-1.736l-8.5-4.965z"/></svg>
              {mediaType === 'tv' ? `Play S${selectedSeason}:E1` : `Play`}
            </a>

            <button onclick={toggleMyList} class="inline-flex items-center gap-2 px-5 py-3.5 glass-strong text-ink-secondary hover:text-ink text-sm font-semibold rounded-xl hover:bg-white/[0.08] transition-all duration-300 ease-exo-out active:scale-95">
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2.2" stroke="currentColor" class="w-4 h-4 transition-transform duration-300 ease-exo-out" class:rotate-45={myListFlag}>
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 5v14m7-7H5" />
              </svg>
              {myListFlag ? 'In Your List' : 'My List'}
            </button>

            {#if trailerKey}
              <button onclick={() => showTrailer = true} class="inline-flex items-center gap-2 px-5 py-3.5 glass-strong text-ink-secondary hover:text-ink text-sm font-semibold rounded-xl hover:bg-white/[0.08] transition-all duration-300 ease-exo-out active:scale-95">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-4 h-4">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.347a1.125 1.125 0 0 1 0 1.972l-11.54 6.347a1.125 1.125 0 0 1-1.667-.986V5.653Z" />
                </svg>
                Trailer
              </button>
            {/if}
          </div>

          {#if data?.overview}
            <div class="max-w-2xl mb-8 group text-balance">
              <h3 class="text-[10px] font-bold uppercase tracking-[0.2em] text-ink-subtle mb-2.5 transition-colors group-hover:text-ink-muted">Overview</h3>
              <p class="text-ink-secondary text-sm leading-relaxed font-normal">
                {data.overview}
              </p>
            </div>
          {/if}

          {#if cast.length > 0}
            <div class="w-full">
              <h3 class="text-[10px] font-bold uppercase tracking-[0.2em] text-ink-subtle mb-3.5">Top Billed Cast</h3>
              <div class="flex gap-4 overflow-x-auto pb-3 -mx-4 px-4 scroll-x-clean select-none [mask-image:linear-gradient(to_right,black_85%,transparent_100%)] [-webkit-mask-image:linear-gradient(to_right,black_85%,transparent_100%)]">
                {#each cast as person}
                  <div class="flex-shrink-0 w-20 text-center group/cast">
                    <div class="w-16 h-16 mx-auto rounded-full overflow-hidden bg-surface-1 mb-2 ring-1 ring-white/[0.06] transition-all duration-300 ease-exo-out group-hover/cast:ring-white/20 group-hover/cast:scale-105 shadow-2">
                      {#if person.profile_path}
                        <img src={tmdbImg(person.profile_path, 'w185')} alt={person.name} class="w-full h-full object-cover transition-transform duration-300 ease-exo-out group-hover/cast:scale-110" loading="lazy" />
                      {:else}
                        <div class="w-full h-full flex items-center justify-center bg-surface-1 text-ink-subtle text-base font-bold">
                          {person.name.charAt(0)}
                        </div>
                      {/if}
                    </div>
                    <p class="text-[11px] text-ink font-semibold leading-tight truncate w-full">{person.name}</p>
                    <p class="text-[10px] text-ink-subtle truncate w-full mt-0.5">{person.character || ''}</p>
                  </div>
                {/each}
              </div>
            </div>
          {/if}
        </div>
      </div>

      {#if mediaType === 'tv' && seasons.length > 0}
        <div class="mt-16 border-t border-white/[0.06] pt-10">
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
            <div>
              <h2 class="text-xl font-display font-extrabold text-ink tracking-tight">Browse Episodes</h2>
              <p class="text-xs text-ink-muted mt-0.5">Select a season to view details and availability.</p>
            </div>

            <div class="relative min-w-[180px]">
              <select
                bind:value={selectedSeason}
                class="appearance-none w-full glass-strong text-ink text-xs font-bold pl-4 pr-10 py-2.5 rounded-xl hover:border-white/10 hover:text-ink transition-all cursor-pointer focus:outline-none focus:ring-2 focus:ring-brand-red/30"
              >
                {#each seasons as s}
                  <option value={s.season_number} class="bg-surface-0 text-ink-secondary">
                    Season {s.season_number} ({s.episode_count} eps)
                  </option>
                {/each}
              </select>
              <div class="absolute right-3.5 top-1/2 -translate-y-1/2 pointer-events-none text-ink-muted">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-4 h-4">
                  <path fill-rule="evenodd" d="M5.22 8.22a.75.75 0 0 1 1.06 0L10 11.94l3.72-3.72a.75.75 0 1 1 1.06 1.06l-4.25 4.25a.75.75 0 0 1-1.06 0L5.22 9.28a.75.75 0 0 1 0-1.06Z" clip-rule="evenodd" />
                </svg>
              </div>
            </div>
          </div>

          {#if seasonEpisodes.length > 0}
            <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {#each seasonEpisodes as ep}
                <a
                  href={watchUrl(ep.episode_number)}
                  class="group/ep flex flex-col rounded-2xl bg-surface-1/30 hover:bg-surface-1/60 border border-white/[0.04] hover:border-white/10 transition-all duration-300 ease-exo-out overflow-hidden shadow-2"
                >
                  <div class="relative aspect-video w-full bg-surface-1 overflow-hidden">
                    {#if ep.still_path}
                      <img src={tmdbImg(ep.still_path, 'w300')} alt={ep.name} class="w-full h-full object-cover transition-transform duration-500 ease-exo-out group-hover/ep:scale-[1.05]" loading="lazy" />
                    {:else}
                      <div class="w-full h-full flex items-center justify-center bg-surface-0/60">
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="w-6 h-6 text-ink-faint">
                          <path fill-rule="evenodd" d="M4.5 5.653c0-1.426 1.529-2.33 2.779-1.643l11.54 6.347c1.295.712 1.295 2.573 0 3.286L7.28 19.99c-1.25.687-2.779-.218-2.779-1.643V5.653Z" clip-rule="evenodd" />
                        </svg>
                      </div>
                    {/if}

                    <div class="absolute inset-0 bg-surface-0/0 group-hover/ep:bg-surface-0/30 transition-all duration-300 flex items-center justify-center backdrop-blur-[1px] opacity-0 group-hover/ep:opacity-100">
                      <div class="w-11 h-11 rounded-full bg-white/10 border border-white/20 flex items-center justify-center backdrop-blur-md shadow-4 text-ink transform scale-90 group-hover/ep:scale-100 transition-transform duration-300 ease-exo-out">
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="w-4 h-4 translate-x-[1px]">
                          <path fill-rule="evenodd" d="M4.5 5.653c0-1.426 1.529-2.33 2.779-1.643l11.54 6.347c1.295.712 1.295 2.573 0 3.286L7.28 19.99c-1.25.687-2.779-.218-2.779-1.643V5.653Z" clip-rule="evenodd" />
                        </svg>
                      </div>
                    </div>

                    <div class="absolute bottom-2 right-2 glass-strong text-ink-secondary text-[10px] font-bold px-2 py-0.5 rounded-md tracking-wider">
                      EP {String(ep.episode_number).padStart(2, '0')}
                    </div>
                  </div>

                  <div class="p-3.5 flex-1 flex flex-col min-w-0">
                    <p class="text-xs text-ink font-bold leading-snug line-clamp-1 transition-colors">
                      {ep.name || `Episode ${ep.episode_number}`}
                    </p>
                    {#if ep.overview}
                      <p class="text-[11px] text-ink-muted mt-1.5 line-clamp-2 leading-relaxed font-normal">{ep.overview}</p>
                    {/if}
                  </div>
                </a>
              {/each}
            </div>
          {:else}
            <div class="text-center py-16 surface-elevated rounded-2xl">
              <p class="text-xs text-ink-muted font-medium tracking-wide">Assembling episodic index…</p>
            </div>
          {/if}
        </div>
      {/if}

      {#if recommendations.length > 0}
        <div class="mt-16 border-t border-white/[0.06] pt-10">
          <MediaRow title="Recommendations" items={recommendations} showViewAll={false} />
        </div>
      {/if}
    </div>
  </div>
{/if}

{#if showTrailer && trailerKey}
  <div
    class="fixed inset-0 z-tooltip flex items-center justify-center bg-black/90 backdrop-blur-sm p-4"
    onclick={(event) => {
      if (event.currentTarget === event.target) showTrailer = false;
    }}
    onkeydown={(event) => {
      if (event.key === 'Escape' || event.key === 'Enter' || event.key === ' ') {
        showTrailer = false;
      }
    }}
    role="dialog"
    aria-modal="true"
    aria-label="Trailer"
    tabindex="-1"
  >
    <div class="relative w-full max-w-4xl aspect-video rounded-2xl overflow-hidden bg-black shadow-4 border border-white/[0.06]" role="document">
      <button
        onclick={() => showTrailer = false}
        class="absolute top-3 right-3 z-10 w-9 h-9 rounded-full bg-black/60 hover:bg-black/80 flex items-center justify-center text-ink transition-colors"
        aria-label="Close trailer"
      >
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-5 h-5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
        </svg>
      </button>
      <iframe
        src={`https://www.youtube-nocookie.com/embed/${trailerKey}?autoplay=1&rel=0`}
        class="w-full h-full"
        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
        allowfullscreen
        title="Trailer"
      ></iframe>
    </div>
  </div>
{/if}
