<script lang="ts">
  import { onMount } from 'svelte';
  import { tmdbApi } from '../lib/api';

  let { media = 'movie', id = '0' } = $props();

  let data: any = $state(null);
  let loading = $state(true);
  let error = $state('');
  let selectedSeason = $state(1);
  let seasonEpisodes: any[] = $state([]);

  let mediaType = $derived(media === 'tv' ? 'tv' : 'movie');
  let title = $derived(data?.title || data?.name || '');
  let year = $derived((data?.release_date || data?.first_air_date || '').split('-')[0]);
  let rating = $derived(data?.vote_average ? (data.vote_average / 2).toFixed(1) : null);
  let runtime = $derived(
    data?.runtime ? `${Math.floor(data.runtime / 60)}h ${data.runtime % 60}m` : null
  );
  let seasons = $derived(
    (data?.seasons || []).filter((s: any) => s.season_number > 0 && s.episode_count > 0)
  );
  let cast = $derived((data?.credits?.cast || []).slice(0, 20));
  let genres = $derived(data?.genres || []);
  let backdropUrl = $derived(
    data?.backdrop_path ? `https://image.tmdb.org/t/p/original${data.backdrop_path}` : ''
  );
  let posterUrl = $derived(
    data?.poster_path
      ? `https://image.tmdb.org/t/p/w500${data.poster_path}`
      : ''
  );
  let votes = $derived(data?.vote_count || 0);
  let status = $derived(data?.status || '');
  let tagline = $derived(data?.tagline || '');

  onMount(() => {
    tmdbApi.details(mediaType, Number(id))
      .then((res: any) => {
        data = res;
        document.title = `${res.title || res.name || 'Details'} - Watchfy`;
      })
      .catch(() => {
        error = 'Failed to load details';
      })
      .finally(() => {
        loading = false;
      });
  });

  $effect(() => {
    if (mediaType !== 'tv' || !data || !selectedSeason) return;
    tmdbApi.seasonEpisodes(Number(id), selectedSeason)
      .then((res: any) => {
        seasonEpisodes = res.episodes || [];
      })
      .catch(() => {});
  });

  function tmdbImg(path: string, size: string = 'w185'): string {
    if (!path) return '';
    return `https://image.tmdb.org/t/p/${size}${path}`;
  }

  function watchUrl(episode?: number): string {
    if (mediaType === 'tv') {
      return `/watch/tv/${id}?season=${selectedSeason}&episode=${episode || 1}`;
    }
    return `/watch/movie/${id}`;
  }
</script>

{#if loading}
  <div class="min-h-screen pb-24">
    <div class="w-full h-[60vh] min-h-[400px] flex items-end p-8 md:p-16 bg-gradient-to-t from-[#0f0f0f] to-zinc-900/20 animate-pulse">
      <div class="max-w-7xl mx-auto w-full flex flex-col md:flex-row gap-8 items-start">
        <div class="w-44 md:w-64 aspect-[2/3] bg-zinc-800 rounded-xl flex-shrink-0"></div>
        <div class="flex-1 space-y-4 w-full mt-4">
          <div class="h-4 bg-zinc-800 rounded w-1/4"></div>
          <div class="h-10 bg-zinc-800 rounded w-3/4"></div>
          <div class="h-6 bg-zinc-800 rounded w-1/3"></div>
          <div class="h-16 bg-zinc-800 rounded w-full"></div>
        </div>
      </div>
    </div>
  </div>
{:else if error}
  <div class="min-h-screen pb-24 flex items-center justify-center">
    <div class="text-center">
      <div class="w-12 h-12 rounded-full bg-red-500/10 border border-red-500/20 flex items-center justify-center text-red-500 mx-auto mb-3">
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-6 h-6">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z" />
        </svg>
      </div>
      <p class="text-zinc-400 text-sm">{error}</p>
    </div>
  </div>
{:else}
  <div class="relative min-h-screen pb-24">
    {#if backdropUrl}
      <div class="fixed top-0 left-0 right-0 h-[70vh] min-h-[500px] z-0 pointer-events-none">
        <img src={backdropUrl} alt="" class="w-full h-full object-cover brightness-[0.3]" />
        <div class="absolute inset-0 bg-gradient-to-t from-[#0f0f0f] via-[#0f0f0f]/60 to-transparent"></div>
        <div class="absolute inset-0 bg-gradient-to-r from-[#0f0f0f] via-transparent to-transparent"></div>
      </div>
    {/if}

    <div class="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 pt-[20vh] md:pt-[30vh]">
      <div class="flex flex-col md:flex-row gap-6 lg:gap-10 items-start">
        <div class="w-40 sm:w-56 md:w-64 mx-auto md:mx-0 flex-shrink-0">
          <div class="aspect-[2/3] rounded-xl overflow-hidden shadow-2xl shadow-black/60 border border-zinc-800/50 bg-zinc-900">
            {#if posterUrl}
              <img src={posterUrl} alt={title} class="w-full h-full object-cover" />
            {:else}
              <div class="w-full h-full flex items-center justify-center text-zinc-600">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-12 h-12">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 10.5l4.72-4.72a.75.75 0 011.28.53v11.38a.75.75 0 01-1.28.53l-4.72-4.72M4.5 18.75h9a2.25 2.25 0 002.25-2.25v-9a2.25 2.25 0 00-2.25-2.25h-9A2.25 2.25 0 002.25 7.5v9a2.25 2.25 0 002.25 2.25z" />
                </svg>
              </div>
            {/if}
          </div>
        </div>

        <div class="flex-1 text-center md:text-left mt-2 md:mt-0">
          <div class="flex flex-wrap items-center justify-center md:justify-start gap-2 text-xs font-semibold mb-3">
            <span class="bg-red-500/10 border border-red-500/30 text-red-400 px-2.5 py-1 rounded-md uppercase tracking-wide">
              {mediaType === 'tv' ? 'TV Series' : 'Movie'}
            </span>
            {#if year}
              <span class="bg-zinc-900/80 backdrop-blur px-2.5 py-1 rounded-md border border-zinc-800/60 text-zinc-300">{year}</span>
            {/if}
            {#if runtime}
              <span class="bg-zinc-900/80 backdrop-blur px-2.5 py-1 rounded-md border border-zinc-800/60 text-zinc-300">{runtime}</span>
            {/if}
            {#if mediaType === 'tv' && data?.number_of_seasons}
              <span class="bg-zinc-900/80 backdrop-blur px-2.5 py-1 rounded-md border border-zinc-800/60 text-zinc-300">
                {data.number_of_seasons} {data.number_of_seasons === 1 ? 'Season' : 'Seasons'}
              </span>
            {/if}
            {#if rating}
              <span class="bg-zinc-900/80 backdrop-blur px-2.5 py-1 rounded-md border border-zinc-800/60 flex items-center gap-1 text-amber-400">
                <svg class="w-3.5 h-3.5 fill-amber-400" viewBox="0 0 20 20"><path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/></svg>
                {rating}
              </span>
            {/if}
            {#if votes > 0}
              <span class="text-zinc-500 text-[11px]">({votes.toLocaleString()})</span>
            {/if}
          </div>

          <h1 class="text-3xl sm:text-4xl lg:text-5xl font-black text-white tracking-tight leading-[1.1] mb-2">
            {title}
          </h1>

          {#if tagline}
            <p class="text-zinc-400 text-sm italic mb-3">"{tagline}"</p>
          {/if}

          <div class="flex flex-wrap items-center justify-center md:justify-start gap-2 mb-3">
            {#each genres as genre}
              <a href="/search?genre={genre.id}" class="text-[11px] font-semibold px-2.5 py-1 rounded-full bg-white/5 hover:bg-white/10 text-zinc-300 hover:text-white border border-white/10 transition-all">
                {genre.name}
              </a>
            {/each}
          </div>

          <div class="flex flex-wrap items-center justify-center md:justify-start gap-3 mb-6">
            <a
              href={watchUrl()}
              class="inline-flex items-center gap-2.5 px-7 py-3 bg-red-600 hover:bg-red-500 text-white text-sm font-bold rounded-xl transition-all active:scale-95 shadow-lg shadow-red-600/25"
            >
              <svg class="w-5 h-5 fill-white" viewBox="0 0 20 20"><path d="M6.423 4.167A1 1 0 005 5.035v9.93a1 1 0 001.423.868l8.5-4.965a1 1 0 000-1.736l-8.5-4.965z"/></svg>
              {mediaType === 'tv' ? `Play S${selectedSeason}:E1` : 'Play Now'}
            </a>
            <button class="inline-flex items-center gap-2 px-5 py-3 bg-zinc-900/60 text-zinc-300 hover:text-white text-sm font-semibold rounded-xl border border-zinc-800/60 hover:bg-zinc-800/80 transition-all active:scale-95 cursor-pointer">
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-4 h-4">
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
              </svg>
              My List
            </button>
            {#if data?.videos?.results?.length}
              <button class="inline-flex items-center gap-2 px-5 py-3 bg-zinc-900/60 text-zinc-300 hover:text-white text-sm font-semibold rounded-xl border border-zinc-800/60 hover:bg-zinc-800/80 transition-all active:scale-95 cursor-pointer">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-4 h-4">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M3.375 19.5h17.25m-17.25 0a1.125 1.125 0 01-1.125-1.125M3.375 19.5h7.5c.621 0 1.125-.504 1.125-1.125m-9.75 0V5.625m0 12.75v-1.5c0-.621.504-1.125 1.125-1.125m18.375 2.625V5.625m0 12.75c0 .621-.504 1.125-1.125 1.125m1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125m0 3.75h-7.5A1.125 1.125 0 0112 18.375m9.75-12.75c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125m19.5 0v1.5c0 .621-.504 1.125-1.125 1.125M2.25 5.625v1.5c0 .621.504 1.125 1.125 1.125m0 0h17.25m-17.25 0h7.5c.621 0 1.125.504 1.125 1.125M3.375 8.25c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125m17.25-3.75h-7.5c-.621 0-1.125.504-1.125 1.125m8.625-1.125c.621 0 1.125.504 1.125 1.125v1.5c0 .621-.504 1.125-1.125 1.125m-17.25 0h7.5m-7.5 0c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125M12 10.875v-1.5m0 1.5c0 .621-.504 1.125-1.125 1.125M12 10.875c0 .621.504 1.125 1.125 1.125m-2.25 0c.621 0 1.125.504 1.125 1.125M10.875 12h2.25m-2.25 0a1.125 1.125 0 01-1.125 1.125M12 12h2.25m-2.25 0a1.125 1.125 0 001.125 1.125M15.375 12h1.5m-1.5 0a1.125 1.125 0 00-1.125 1.125M15.375 12c.621 0 1.125.504 1.125 1.125" />
                </svg>
                Trailer
              </button>
            {/if}
          </div>

          {#if data?.overview}
            <div class="max-w-3xl mb-6">
              <h3 class="text-[11px] font-bold uppercase tracking-widest text-zinc-500 mb-2">Overview</h3>
              <p class="text-zinc-300 text-sm leading-relaxed">
                {data.overview}
              </p>
            </div>
          {/if}

          {#if cast.length > 0}
            <div class="mb-6">
              <h3 class="text-[11px] font-bold uppercase tracking-widest text-zinc-500 mb-3">Cast</h3>
              <div class="flex gap-3 overflow-x-auto pb-2 -mx-4 px-4 scrollbar-none">
                {#each cast as person}
                  <div class="flex-shrink-0 w-20 text-center">
                    <div class="w-16 h-16 mx-auto rounded-full overflow-hidden bg-zinc-800 mb-1.5 ring-2 ring-zinc-800/50">
                      {#if person.profile_path}
                        <img src={tmdbImg(person.profile_path, 'w185')} alt={person.name} class="w-full h-full object-cover" loading="lazy" />
                      {:else}
                        <div class="w-full h-full flex items-center justify-center text-zinc-600 text-lg font-bold">
                          {person.name.charAt(0)}
                        </div>
                      {/if}
                    </div>
                    <p class="text-[11px] text-zinc-300 font-medium leading-tight truncate">{person.name}</p>
                    <p class="text-[10px] text-zinc-500 truncate">{person.character || ''}</p>
                  </div>
                {/each}
              </div>
            </div>
          {/if}
        </div>
      </div>

      {#if mediaType === 'tv' && seasons.length > 0}
        <div class="mt-10 border-t border-zinc-800/40 pt-8">
          <div class="flex items-center justify-between mb-6">
            <h2 class="text-lg font-bold text-white">Episodes</h2>
            <div class="relative">
              <select
                bind:value={selectedSeason}
                class="appearance-none bg-zinc-900/80 text-zinc-200 text-sm font-semibold px-4 py-2 pr-10 rounded-xl border border-zinc-800/60 hover:border-zinc-700 transition-all cursor-pointer focus:outline-none focus:ring-1 focus:ring-red-500/30"
              >
                {#each seasons as s}
                  <option value={s.season_number} class="bg-zinc-900 text-zinc-300">
                    Season {s.season_number}
                  </option>
                {/each}
              </select>
              <div class="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-zinc-500">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-4 h-4">
                  <path fill-rule="evenodd" d="M5.22 8.22a.75.75 0 0 1 1.06 0L10 11.94l3.72-3.72a.75.75 0 1 1 1.06 1.06l-4.25 4.25a.75.75 0 0 1-1.06 0L5.22 9.28a.75.75 0 0 1 0-1.06Z" clip-rule="evenodd" />
                </svg>
              </div>
            </div>
          </div>

          {#if seasonEpisodes.length > 0}
            <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
              {#each seasonEpisodes as ep}
                <a
                  href={watchUrl(ep.episode_number)}
                  class="group flex gap-3 p-3 rounded-xl bg-zinc-900/30 hover:bg-zinc-800/30 border border-zinc-800/30 hover:border-zinc-700/50 transition-all active:scale-[0.99]"
                >
                  <div class="relative w-24 aspect-video rounded-lg overflow-hidden bg-zinc-800 flex-shrink-0">
                    {#if ep.still_path}
                      <img src={tmdbImg(ep.still_path, 'w185')} alt={ep.name} class="w-full h-full object-cover" loading="lazy" />
                    {:else}
                      <div class="w-full h-full flex items-center justify-center">
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="w-5 h-5 text-zinc-600">
                          <path fill-rule="evenodd" d="M4.5 5.653c0-1.426 1.529-2.33 2.779-1.643l11.54 6.347c1.295.712 1.295 2.573 0 3.286L7.28 19.99c-1.25.687-2.779-.218-2.779-1.643V5.653Z" clip-rule="evenodd" />
                        </svg>
                      </div>
                    {/if}
                    <div class="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-colors flex items-center justify-center">
                      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="w-8 h-8 text-white opacity-0 group-hover:opacity-100 transition-all scale-75 group-hover:scale-100 drop-shadow-lg">
                        <path fill-rule="evenodd" d="M4.5 5.653c0-1.426 1.529-2.33 2.779-1.643l11.54 6.347c1.295.712 1.295 2.573 0 3.286L7.28 19.99c-1.25.687-2.779-.218-2.779-1.643V5.653Z" clip-rule="evenodd" />
                      </svg>
                    </div>
                    <div class="absolute bottom-1 right-1 bg-black/70 text-white text-[10px] font-semibold px-1.5 py-0.5 rounded">
                      {String(ep.episode_number).padStart(2, '0')}
                    </div>
                  </div>
                  <div class="flex-1 min-w-0 pt-0.5">
                    <p class="text-sm text-zinc-200 group-hover:text-white font-medium leading-tight line-clamp-2 transition-colors">
                      {ep.name || `Episode ${ep.episode_number}`}
                    </p>
                    {#if ep.overview}
                      <p class="text-xs text-zinc-500 mt-1 line-clamp-2 leading-relaxed">{ep.overview}</p>
                    {/if}
                  </div>
                </a>
              {/each}
            </div>
          {:else}
            <div class="text-center py-12 text-zinc-500">
              <p class="text-sm">Loading episodes...</p>
            </div>
          {/if}
        </div>
      {/if}
    </div>
  </div>
{/if}