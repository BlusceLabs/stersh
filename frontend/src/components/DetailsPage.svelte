<script lang="ts">
  import { tmdbApi } from '../lib/api';

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
  let data: MediaDetails | null = $state(null);
  let loading = $state(true);
  let error = $state('');
  let selectedSeason = $state(1);
  let seasonEpisodes: Episode[] = $state([]);
  let recommendations: any[] = $state([]);

  // Derived Values
  let mediaType = $derived(media === 'tv' ? 'tv' : 'movie');
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
          .then((r: any) => { recommendations = (r.results || []).filter((x: any) => x.poster_path).slice(0, 12); })
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
  <div class="min-h-screen bg-[#09090b] flex items-center justify-center px-4 sm:px-6 lg:px-8">
    <div class="max-w-7xl w-full mx-auto grid grid-cols-1 md:grid-cols-[280px_1fr] lg:grid-cols-[340px_1fr] gap-10 lg:gap-16 items-center animate-pulse pt-24">
      <div class="w-full aspect-[2/3] bg-zinc-900/60 rounded-2xl border border-zinc-800/40 hidden md:block"></div>
      <div class="space-y-6">
        <div class="flex gap-2"><div class="h-6 bg-zinc-900/80 rounded-md w-20"></div><div class="h-6 bg-zinc-900/80 rounded-md w-16"></div></div>
        <div class="h-12 bg-zinc-900/80 rounded-xl w-3/4"></div>
        <div class="h-4 bg-zinc-900/40 rounded w-1/2 italic"></div>
        <div class="space-y-2 pt-4">
          <div class="h-4 bg-zinc-900/60 rounded w-full"></div>
          <div class="h-4 bg-zinc-900/60 rounded w-5/6"></div>
        </div>
      </div>
    </div>
  </div>
{:else if error}
  <div class="min-h-screen flex items-center justify-center bg-[#09090b] px-4">
    <div class="text-center max-w-sm">
      <div class="w-14 h-14 rounded-2xl bg-red-500/10 border border-red-500/20 flex items-center justify-center text-red-500 mx-auto mb-4 backdrop-blur-xl shadow-xl shadow-red-500/5">
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.75" stroke="currentColor" class="w-6 h-6">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z" />
        </svg>
      </div>
      <h3 class="text-white font-bold text-lg mb-1">Something went wrong</h3>
      <p class="text-zinc-500 text-sm">{error}</p>
    </div>
  </div>
{:else}
  <div class="relative min-h-screen bg-[#09090b] text-zinc-100 overflow-hidden">
    
    {#if backdropUrl}
      <div class="absolute top-0 left-0 right-0 h-[85vh] w-full z-0 pointer-events-none overflow-hidden">
        <img src={backdropUrl} alt="" class="w-full h-full object-cover brightness-[0.22] scale-105 transition-transform duration-1000 motion-safe:scale-100" />
        <div class="absolute inset-0 bg-gradient-to-t from-[#09090b] via-[#09090b]/80 to-transparent"></div>
        <div class="absolute inset-0 bg-gradient-to-r from-[#09090b] via-[#09090b]/30 to-transparent"></div>
        <div class="absolute inset-0 bg-gradient-to-b from-[#09090b]/10 via-transparent to-[#09090b]"></div>
      </div>
    {/if}

    <div class="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-[16vh] md:pt-[24vh] pb-32">
      <div class="grid grid-cols-1 md:grid-cols-[240px_1fr] lg:grid-cols-[300px_1fr] gap-8 lg:gap-14 items-start">
        
        <div class="w-44 sm:w-56 md:w-full mx-auto md:mx-0 flex-shrink-0 relative group">
          <div class="aspect-[2/3] rounded-2xl overflow-hidden shadow-[0_25px_60px_-15px_rgba(0,0,0,0.9)] border border-zinc-800/60 bg-zinc-900 transition-all duration-500 group-hover:border-zinc-700/80 group-hover:shadow-black/100">
            {#if posterUrl}
              <img src={posterUrl} alt={title} class="w-full h-full object-cover select-none transition-transform duration-500 group-hover:scale-[1.02]" />
            {:else}
              <div class="w-full h-full flex flex-col items-center justify-center text-zinc-700 gap-3">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.25" stroke="currentColor" class="w-12 h-12">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 10.5l4.72-4.72a.75.75 0 011.28.53v11.38a.75.75 0 01-1.28.53l-4.72-4.72M4.5 18.75h9a2.25 2.25 0 002.25-2.25v-9a2.25 2.25 0 00-2.25-2.25h-9A2.25 2.25 0 002.25 7.5v9a2.25 2.25 0 002.25 2.25z" />
                </svg>
                <span class="text-xs tracking-wider font-semibold uppercase opacity-60">No Media Poster</span>
              </div>
            {/if}
          </div>
        </div>

        <div class="text-center md:text-left mt-2 md:mt-0 flex flex-col">
          
          <div class="flex flex-wrap items-center justify-center md:justify-start gap-2 text-[11px] font-bold tracking-wide mb-4">
            <span class="bg-red-500/10 border border-red-500/30 text-red-400 px-3 py-1 rounded-lg uppercase font-extrabold tracking-widest shadow-sm shadow-red-500/5">
              {mediaType === 'tv' ? 'TV Series' : 'Movie'}
            </span>
            {#if year}
              <span class="bg-zinc-900/40 backdrop-blur-md px-3 py-1 rounded-lg border border-zinc-800/50 text-zinc-300">{year}</span>
            {/if}
            {#if runtime}
              <span class="bg-zinc-900/40 backdrop-blur-md px-3 py-1 rounded-lg border border-zinc-800/50 text-zinc-300">{runtime}</span>
            {/if}
            {#if mediaType === 'tv' && data?.number_of_seasons}
              <span class="bg-zinc-900/40 backdrop-blur-md px-3 py-1 rounded-lg border border-zinc-800/50 text-zinc-300">
                {data.number_of_seasons} {data.number_of_seasons === 1 ? 'Season' : 'Seasons'}
              </span>
            {/if}
            {#if rating}
              <span class="bg-zinc-900/40 backdrop-blur-md px-2.5 py-1 rounded-lg border border-zinc-800/50 flex items-center gap-1.5 text-amber-400">
                <svg class="w-3.5 h-3.5 fill-amber-400 drop-shadow-[0_0_4px_rgba(251,191,36,0.2)]" viewBox="0 0 20 20"><path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/></svg>
                {rating} <span class="text-zinc-500 text-[10px] font-medium">({votes.toLocaleString()})</span>
              </span>
            {/if}
          </div>

          <h1 class="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-white tracking-tight leading-[1.1] mb-2 drop-shadow-md">
            {title}
          </h1>

          {#if tagline}
            <p class="text-zinc-400 text-sm md:text-base font-medium italic mb-5 opacity-90">"{tagline}"</p>
          {/if}

          <div class="flex flex-wrap items-center justify-center md:justify-start gap-1.5 mb-6">
            {#each genres as genre}
              <a href="/search?genre={genre.id}" class="text-[11px] font-semibold px-3 py-1 rounded-full bg-zinc-900/30 hover:bg-zinc-800/60 text-zinc-400 hover:text-white border border-zinc-800/40 hover:border-zinc-700 transition-all duration-300">
                {genre.name}
              </a>
            {/each}
          </div>

          <div class="flex flex-wrap items-center justify-center md:justify-start gap-3 mb-8">
            <a
              href={watchUrl()}
              class="inline-flex items-center gap-2.5 px-8 py-3.5 bg-red-600 hover:bg-red-500 text-white text-sm font-bold rounded-xl transition-all duration-300 active:scale-95 shadow-xl shadow-red-600/20 hover:shadow-red-600/30 select-none"
            >
              <svg class="w-4 h-4 fill-white" viewBox="0 0 20 20"><path d="M6.423 4.167A1 1 0 005 5.035v9.93a1 1 0 001.423.868l8.5-4.965a1 1 0 000-1.736l-8.5-4.965z"/></svg>
              {mediaType === 'tv' ? `Play S${selectedSeason}:E1` : 'Play Title'}
            </a>
            
            <button class="inline-flex items-center gap-2 px-5 py-3.5 bg-zinc-900/40 backdrop-blur-md text-zinc-300 hover:text-white text-sm font-semibold rounded-xl border border-zinc-800/60 hover:bg-zinc-800/60 hover:border-zinc-700 transition-all duration-300 active:scale-95 cursor-pointer select-none">
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2.2" stroke="currentColor" class="w-4 h-4">
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
              </svg>
              My List
            </button>

            {#if data?.videos?.results?.length}
              <button class="inline-flex items-center gap-2 px-5 py-3.5 bg-zinc-900/40 backdrop-blur-md text-zinc-300 hover:text-white text-sm font-semibold rounded-xl border border-zinc-800/60 hover:bg-zinc-800/60 hover:border-zinc-700 transition-all duration-300 active:scale-95 cursor-pointer select-none">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-4 h-4">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.347a1.125 1.125 0 0 1 0 1.972l-11.54 6.347a1.125 1.125 0 0 1-1.667-.986V5.653Z" />
                </svg>
                Trailer
              </button>
            {/if}
          </div>

          {#if data?.overview}
            <div class="max-w-2xl mb-8 group text-balance">
              <h3 class="text-[10px] font-bold uppercase tracking-widest text-zinc-500 mb-2.5 transition-colors group-hover:text-zinc-400">Overview</h3>
              <p class="text-zinc-300/90 text-sm leading-relaxed font-normal">
                {data.overview}
              </p>
            </div>
          {/if}

          {#if cast.length > 0}
            <div class="w-full">
              <h3 class="text-[10px] font-bold uppercase tracking-widest text-zinc-500 mb-3.5">Top Billed Cast</h3>
              <div class="flex gap-4 overflow-x-auto pb-3 -mx-4 px-4 scrollbar-none select-none mask-image-r">
                {#each cast as person}
                  <div class="flex-shrink-0 w-20 text-center group/cast">
                    <div class="w-16 h-16 mx-auto rounded-full overflow-hidden bg-zinc-900 mb-2 ring-1 ring-zinc-800/80 transition-all duration-300 group-hover/cast:ring-zinc-600 group-hover/cast:scale-105 shadow-md">
                      {#if person.profile_path}
                        <img src={tmdbImg(person.profile_path, 'w185')} alt={person.name} class="w-full h-full object-cover transition-transform duration-300 group-hover/cast:scale-105" loading="lazy" />
                      {:else}
                        <div class="w-full h-full flex items-center justify-center bg-zinc-900 text-zinc-500 text-base font-bold">
                          {person.name.charAt(0)}
                        </div>
                      {/if}
                    </div>
                    <p class="text-[11px] text-zinc-200 font-semibold leading-tight truncate w-full group-hover/cast:text-white">{person.name}</p>
                    <p class="text-[10px] text-zinc-500 truncate w-full mt-0.5">{person.character || ''}</p>
                  </div>
                {/each}
              </div>
            </div>
          {/if}
        </div>
      </div>

      {#if mediaType === 'tv' && seasons.length > 0}
        <div class="mt-16 border-t border-zinc-900 pt-10">
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
            <div>
              <h2 class="text-xl font-extrabold text-white tracking-tight">Browse Episodes</h2>
              <p class="text-xs text-zinc-500 mt-0.5">Select a season to view details and availability.</p>
            </div>
            
            <div class="relative min-w-[160px]">
              <select
                bind:value={selectedSeason}
                class="appearance-none w-full bg-zinc-900/50 backdrop-blur-md text-zinc-200 text-xs font-bold px-4 py-2.5 pr-10 rounded-xl border border-zinc-800/60 hover:border-zinc-700 hover:text-white transition-all cursor-pointer focus:outline-none focus:ring-2 focus:ring-red-500/20"
              >
                {#each seasons as s}
                  <option value={s.season_number} class="bg-[#09090b] text-zinc-300">
                    Season {s.season_number} ({s.episode_count} eps)
                  </option>
                {/each}
              </select>
              <div class="absolute right-3.5 top-1/2 -translate-y-1/2 pointer-events-none text-zinc-500">
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
                  class="group/ep flex flex-col rounded-2xl bg-zinc-900/20 hover:bg-zinc-900/40 border border-zinc-900/60 hover:border-zinc-800/80 transition-all duration-300 overflow-hidden shadow-sm"
                >
                  <div class="relative aspect-video w-full bg-zinc-900 overflow-hidden border-b border-zinc-950/40">
                    {#if ep.still_path}
                      <img src={tmdbImg(ep.still_path, 'w300')} alt={ep.name} class="w-full h-full object-cover transition-transform duration-500 group-hover/ep:scale-[1.03]" loading="lazy" />
                    {:else}
                      <div class="w-full h-full flex items-center justify-center bg-zinc-950/50">
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="w-6 h-6 text-zinc-700">
                          <path fill-rule="evenodd" d="M4.5 5.653c0-1.426 1.529-2.33 2.779-1.643l11.54 6.347c1.295.712 1.295 2.573 0 3.286L7.28 19.99c-1.25.687-2.779-.218-2.779-1.643V5.653Z" clip-rule="evenodd" />
                        </svg>
                      </div>
                    {/if}
                    
                    <div class="absolute inset-0 bg-zinc-950/0 group-hover/ep:bg-zinc-950/30 transition-all duration-300 flex items-center justify-center backdrop-blur-[1px] opacity-0 group-hover/ep:opacity-100">
                      <div class="w-10 h-10 rounded-full bg-white/10 border border-white/20 flex items-center justify-center backdrop-blur-md shadow-xl text-white transform scale-90 group-hover/ep:scale-100 transition-transform duration-300">
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="w-4 h-4 translate-x-[1px]">
                          <path fill-rule="evenodd" d="M4.5 5.653c0-1.426 1.529-2.33 2.779-1.643l11.54 6.347c1.295.712 1.295 2.573 0 3.286L7.28 19.99c-1.25.687-2.779-.218-2.779-1.643V5.653Z" clip-rule="evenodd" />
                        </svg>
                      </div>
                    </div>
                    
                    <div class="absolute bottom-2 right-2 bg-black/75 backdrop-blur-md text-zinc-300 text-[10px] font-bold px-2 py-0.5 rounded-md border border-zinc-800/40 tracking-wider">
                      EP {String(ep.episode_number).padStart(2, '0')}
                    </div>
                  </div>

                  <div class="p-3.5 flex-1 flex flex-col min-w-0 bg-gradient-to-b from-transparent to-zinc-950/10">
                    <p class="text-xs text-zinc-200 group-hover/ep:text-white font-bold leading-snug line-clamp-1 transition-colors">
                      {ep.name || `Episode ${ep.episode_number}`}
                    </p>
                    {#if ep.overview}
                      <p class="text-[11px] text-zinc-500 mt-1.5 line-clamp-2 leading-relaxed font-normal">{ep.overview}</p>
                    {/if}
                  </div>
                </a>
              {/each}
            </div>
          {:else}
            <div class="text-center py-16 bg-zinc-900/10 rounded-2xl border border-zinc-900/50">
              <p class="text-xs text-zinc-500 animate-pulse font-medium tracking-wide">Assembling episodic index...</p>
            </div>
          {/if}
        </div>
      {/if}

      {#if recommendations.length > 0}
        <div class="mt-16 border-t border-zinc-900 pt-10">
          <h2 class="text-xl font-extrabold text-white tracking-tight mb-6">Recommendations</h2>
          <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-x-4 gap-y-6">
            {#each recommendations as rec}
              <a
                href="/{mediaType}/{rec.id}"
                class="group/rec block focus:outline-none"
              >
                <div class="aspect-[2/3] rounded-xl overflow-hidden bg-zinc-900 border border-zinc-800/40 transition-all duration-300 group-hover/rec:-translate-y-1 group-hover/rec:border-zinc-700/60 group-hover/rec:shadow-xl">
                  <img
                    src={rec.poster_path ? `https://image.tmdb.org/t/p/w500${rec.poster_path}` : ''}
                    alt={rec.title || rec.name}
                    class="w-full h-full object-cover transition-transform duration-300 group-hover/rec:scale-105"
                    loading="lazy"
                  />
                </div>
                <p class="text-xs text-zinc-300 group-hover/rec:text-white font-semibold mt-2 line-clamp-1 transition-colors">
                  {rec.title || rec.name}
                </p>
                <p class="text-[10px] text-zinc-500">
                  {((rec.release_date || rec.first_air_date || '').split('-')[0]) || ''}
                </p>
              </a>
            {/each}
          </div>
        </div>
      {/if}
    </div>
  </div>
{/if}

<style>
  /* Linear fade masking for top billed cast slider element */
  .mask-image-r {
    mask-image: linear-gradient(to right, rgba(0,0,0,1) 85%, rgba(0,0,0,0) 100%);
    -webkit-mask-image: linear-gradient(to right, rgba(0,0,0,1) 85%, rgba(0,0,0,0) 100%);
  }
</style>