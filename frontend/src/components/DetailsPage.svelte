<script lang="ts">
  import { tmdbApi } from '../lib/api';
  import DetailSkeleton from './skeletons/DetailSkeleton.svelte';
  import EmptyState from './EmptyState.svelte';
  import MediaRow from './MediaRow.svelte';

  let { media = 'movie', id = '0' } = $props<{ media?: string; id?: string }>();

  interface Genre { id: number; name: string; }
  interface CastMember { name: string; character: string; profile_path: string; }
  interface Episode { name: string; episode_number: number; still_path: string; overview: string; }
  interface Season { season_number: number; episode_count: number; }
  interface Company { name: string; logo_path: string | null; }

  interface MediaDetails {
    title?: string; name?: string; release_date?: string; first_air_date?: string;
    vote_average?: number; vote_count?: number; runtime?: number;
    number_of_seasons?: number; seasons?: Season[]; genres?: Genre[];
    backdrop_path?: string; poster_path?: string; status?: string;
    tagline?: string; overview?: string;
    credits?: { cast: CastMember[]; crew?: any[] };
    videos?: { results: any[] };
    production_companies?: Company[];
    keywords?: { keywords?: any[] };
    spoken_languages?: any[];
    budget?: number;
    revenue?: number;
  }

  let data = $state<MediaDetails | null>(null);
  let loading = $state(true);
  let error = $state('');
  let selectedSeason = $state(1);
  let seasonEpisodes: Episode[] = $state([]);
  let recommendations: any[] = $state([]);
  let showTrailer = $state(false);
  let myListFlag = $state(false);
  let overviewExpanded = $state(false);
  let logoUrl = $state('');
  let scrollY = $state(0);

  $effect(() => {
    (async () => {
      try {
        const token = localStorage.getItem('watchfy_token');
        if (token) {
          const res = await fetch(`/user/watchlist/${mediaType}/${id}`, { headers: { 'Authorization': `Bearer ${token}` } });
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
        const url = `/user/watchlist/${mediaType}/${id}`;
        if (myListFlag) { await fetch(url, { method: 'DELETE', headers: { 'Authorization': `Bearer ${token}` } }); myListFlag = false; }
        else { await fetch(url, { method: 'POST', headers: { 'Authorization': `Bearer ${token}` } }); myListFlag = true; }
        return;
      } catch {}
    }
    try {
      if (myListFlag) { localStorage.removeItem(key); myListFlag = false; }
      else { localStorage.setItem(key, 'true'); myListFlag = true; }
    } catch {}
  }

  let trailerKey = $derived(data?.videos?.results?.find((v: any) => v.site === 'YouTube' && (v.type === 'Trailer' || v.type === 'Teaser'))?.key || data?.videos?.results?.[0]?.key || '');
  let mediaType: 'movie' | 'tv' = $derived(media === 'tv' ? 'tv' : 'movie');
  let title = $derived(data?.title || data?.name || '');
  let year = $derived((data?.release_date || data?.first_air_date || '').split('-')[0]);
  let rating = $derived(data?.vote_average ? (data.vote_average / 2).toFixed(1) : null);
  let runtime = $derived(data?.runtime ? `${Math.floor(data.runtime / 60)}h ${data.runtime % 60}m` : null);
  let seasons = $derived((data?.seasons || []).filter(s => s.season_number > 0 && s.episode_count > 0));
  let cast = $derived((data?.credits?.cast || []).slice(0, 20));
  let genres = $derived(data?.genres || []);
  let backdropUrl = $derived(data?.backdrop_path ? `https://image.tmdb.org/t/p/original${data.backdrop_path}` : '');
  let posterUrl = $derived(data?.poster_path ? `https://image.tmdb.org/t/p/w500${data.poster_path}` : '');
  let votes = $derived(data?.vote_count || 0);
  let tagline = $derived(data?.tagline || '');
  let overviewTruncated = $derived(data?.overview && data.overview.length > 200 ? data.overview.slice(0, 200) + '…' : data?.overview || '');
  let needsTruncation = $derived(data?.overview && data.overview.length > 200);
  let director = $derived(data?.credits?.crew?.find((c: any) => c.job === 'Director')?.name || '');
  let writers = $derived(data?.credits?.crew?.filter((c: any) => c.job === 'Writer' || c.job === 'Screenplay').slice(0, 3).map((c: any) => c.name) || []);
  let companies = $derived(data?.production_companies?.slice(0, 4) || []);
  let keywordsList = $derived(data?.keywords?.keywords?.slice(0, 8) || []);
  let language = $derived(data?.spoken_languages?.[0]?.english_name || '');

  $effect(() => {
    const currentId = Number(id);
    if (!currentId) return;
    loading = true; error = ''; data = null; selectedSeason = 1; seasonEpisodes = []; logoUrl = '';
    tmdbApi.details(mediaType, currentId)
      .then((res: any) => {
        data = res;
        fetch(`/api/tmdb/${mediaType}/${currentId}/images?include_image_language=en,null`)
          .then(r => r.json())
          .then((imgData: any) => {
            const logo = imgData?.logos?.[0];
            if (logo?.file_path) logoUrl = `https://image.tmdb.org/t/p/original${logo.file_path}`;
          })
          .catch(() => {});
        tmdbApi.recommendations(mediaType, currentId)
          .then((r: any) => { recommendations = (r.results || []).filter((x: any) => x.poster_path).slice(0, 12).map((x: any) => ({ ...x, media_type: x.media_type || mediaType })); })
          .catch(() => {});
      })
      .catch(() => { error = 'Unable to load details.'; })
      .finally(() => { loading = false; });
  });

  $effect(() => {
    const currentId = Number(id);
    if (mediaType !== 'tv' || !data || !selectedSeason) return;
    tmdbApi.seasonEpisodes(currentId, selectedSeason)
      .then((res: any) => { seasonEpisodes = res.episodes || []; })
      .catch(() => { seasonEpisodes = []; });
  });

  function tmdbImg(path: string, size: string = 'w185'): string {
    return path ? `https://image.tmdb.org/t/p/${size}${path}` : '';
  }

  function watchUrl(episode?: number): string {
    if (mediaType === 'tv') return `/watch/tv/${id}?season=${selectedSeason}&episode=${episode || 1}`;
    return `/watch/movie/${id}`;
  }

  function formatMoney(amount?: number): string {
    if (!amount) return '';
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(amount);
  }
</script>

<svelte:head>
  <title>{title ? `${title} — Watchfy` : 'Loading Details...'}</title>
</svelte:head>

<svelte:window bind:scrollY={scrollY} />

{#if loading}
  <DetailSkeleton />
{:else if error}
  <div class="min-h-screen flex items-center justify-center bg-surface-0 px-4">
    <EmptyState variant="error" icon="alert" title="Something went wrong" message={error} ctaLabel="Try Again" oncTaClick={() => window.location.reload()} />
  </div>
{:else}
  <div class="relative min-h-screen bg-surface-0 text-ink overflow-x-hidden">

    <!-- ===== FULL-BLEED BACKDROP WITH PARALLAX ===== -->
    {#if backdropUrl}
      <div class="fixed inset-0 z-0 pointer-events-none" style="transform: translateY({scrollY * 0.3}px);">
        <img src={backdropUrl} alt="" class="w-full h-[120%] object-cover brightness-[0.12] scale-105 motion-safe:animate-[kenburns_25s_ease-out_infinite_alternate]" />
      </div>
      <div class="fixed inset-0 z-0 pointer-events-none">
        <div class="absolute inset-0 bg-gradient-to-t from-surface-0 via-surface-0/80 to-transparent"></div>
        <div class="absolute inset-0 bg-gradient-to-b from-surface-0/50 via-transparent to-transparent"></div>
        <div class="absolute inset-0 bg-radial-vignette"></div>
      </div>
    {/if}

    <!-- ===== HERO SECTION (full viewport) ===== -->
    <section class="relative z-10 min-h-[100dvh] flex items-end">
      <div class="w-full px-4 sm:px-6 lg:px-8 pb-16 md:pb-24">
        <div class="flex flex-col md:flex-row gap-8 md:gap-12 items-end md:items-end">

          <!-- Poster (left side, extends below fold) -->
          <div class="hidden md:block w-[260px] lg:w-[320px] flex-shrink-0 relative group/poster self-end -mb-16">
            <div class="aspect-[2/3] rounded-2xl overflow-hidden shadow-4 border border-white/[0.06] bg-surface-1 transition-all duration-500 group-hover/poster:border-white/15 group-hover/poster:shadow-glow-red premium-shimmer">
              {#if posterUrl}
                <img src={posterUrl} alt={title} class="w-full h-full object-cover select-none transition-transform duration-700 ease-exo-out group-hover/poster:scale-[1.03]" loading="eager" />
              {:else}
                <div class="w-full h-full flex flex-col items-center justify-center text-ink-faint gap-3 relative overflow-hidden">
                  <div class="absolute inset-0 bg-gradient-to-br from-surface-1 via-surface-2 to-surface-0"></div>
                  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.25" stroke="currentColor" class="w-12 h-12 relative z-10 opacity-50"><path stroke-linecap="round" stroke-linejoin="round" d="M15.75 10.5l4.72-4.72a.75.75 0 011.28.53v11.38a.75.75 0 01-1.28.53l-4.72-4.72M4.5 18.75h9a2.25 2.25 0 002.25-2.25v-9a2.25 2.25 0 00-2.25-2.25h-9A2.25 2.25 0 002.25 7.5v9a2.25 2.25 0 002.25 2.25z" /></svg>
                  <span class="text-xs tracking-wider uppercase opacity-50 relative z-10">No Poster</span>
                </div>
              {/if}
            </div>
            {#if trailerKey}
              <button
                onclick={() => showTrailer = true}
                class="absolute inset-0 flex items-center justify-center rounded-2xl bg-black/0 group-hover/poster:bg-black/40 transition-all duration-500"
                aria-label="Play trailer"
              >
                <div class="w-16 h-16 rounded-full bg-brand-gradient-cta/90 backdrop-blur-sm border border-white/20 flex items-center justify-center shadow-glow-red opacity-0 group-hover/poster:opacity-100 scale-75 group-hover/poster:scale-100 transition-all duration-500 ease-spring">
                  <svg viewBox="0 0 24 24" fill="currentColor" class="w-7 h-7 text-white translate-x-[2px]"><path d="M8 5v14l11-7z"/></svg>
                </div>
              </button>
            {/if}
          </div>

          <!-- Info (right side) -->
          <div class="flex-1 min-w-0 pb-2">

            <!-- Badges row -->
            <div class="flex flex-wrap items-center gap-2 mb-4">
              <span class="bg-brand-red/[0.12] border border-brand-red/30 text-brand-red px-2.5 py-0.5 rounded-md text-[11px] font-extrabold uppercase tracking-widest">
                {mediaType === 'tv' ? 'TV Series' : 'Movie'}
              </span>
              {#if year}
                <span class="glass-strong px-2.5 py-0.5 rounded-md text-ink-secondary text-[11px] font-bold">{year}</span>
              {/if}
              {#if runtime}
                <span class="glass-strong px-2.5 py-0.5 rounded-md text-ink-secondary text-[11px] font-bold">{runtime}</span>
              {/if}
              {#if mediaType === 'tv' && data?.number_of_seasons}
                <span class="glass-strong px-2.5 py-0.5 rounded-md text-ink-secondary text-[11px] font-bold">{data.number_of_seasons} {data.number_of_seasons === 1 ? 'Season' : 'Seasons'}</span>
              {/if}
              {#if rating}
                <span class="glass-strong px-2.5 py-0.5 rounded-md flex items-center gap-1 text-accent-warm text-[11px] font-bold">
                  <svg class="w-3 h-3 fill-accent-warm" viewBox="0 0 20 20"><path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/></svg>
                  {rating}<span class="text-ink-subtle text-[10px] font-medium ml-0.5">({votes.toLocaleString()})</span>
                </span>
              {/if}
            </div>

            <!-- Title / Logo -->
            {#if logoUrl}
              <img src={logoUrl} alt={title} class="max-w-xs md:max-w-md lg:max-w-2xl h-auto max-h-[160px] object-contain mb-4 text-cinematic-lg" />
            {:else}
              <h1 class="text-5xl sm:text-6xl md:text-7xl lg:text-8xl font-display font-black text-ink tracking-tighter leading-[0.95] text-cinematic-lg mb-2">
                {title}
              </h1>
            {/if}

            {#if tagline}
              <p class="text-ink-muted text-base md:text-lg font-medium italic mb-5 opacity-80">"{tagline}"</p>
            {/if}

            <!-- Genres -->
            <div class="flex flex-wrap items-center gap-2 mb-6">
              {#each genres as genre}
                <a href="/search?genre={genre.id}" class="text-[11px] font-bold uppercase tracking-widest px-3 py-1.5 rounded-full border border-white/[0.06] bg-white/[0.02] text-ink-subtle hover:text-ink hover:bg-white/[0.06] hover:border-white/10 transition-all duration-200">
                  {genre.name}
                </a>
              {/each}
            </div>

            <!-- Action Buttons -->
            <div class="flex flex-wrap items-center gap-3 mb-8">
              <a href={watchUrl()} class="inline-flex items-center gap-2.5 px-8 py-4 bg-brand-gradient-cta text-white text-sm font-bold rounded-xl hover:brightness-110 active:scale-95 shadow-glow-red transition-all duration-300 ease-exo-out transform hover:scale-[1.02] active:scale-[0.98]">
                <svg class="w-5 h-5 fill-white" viewBox="0 0 20 20"><path d="M6.423 4.167A1 1 0 005 5.035v9.93a1 1 0 001.423.868l8.5-4.965a1 1 0 000-1.736l-8.5-4.965z"/></svg>
                {mediaType === 'tv' ? `Play S1:E1` : 'Play Now'}
              </a>
              <button onclick={toggleMyList} class="inline-flex items-center gap-2 px-6 py-4 glass-strong text-ink-secondary hover:text-ink text-sm font-semibold rounded-xl border border-white/[0.06] hover:border-white/10 hover:bg-white/[0.06] transition-all duration-300 ease-exo-out active:scale-95 transform hover:scale-[1.02] active:scale-[0.98]">
                <svg xmlns="http://www.w3.org/2000/svg" fill={myListFlag ? 'currentColor' : 'none'} viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-5 h-5 transition-all duration-300 {myListFlag ? 'text-brand-red' : ''}">
                  {#if myListFlag}<path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  {:else}<path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />{/if}
                </svg>
                {myListFlag ? 'In Your List' : 'My List'}
              </button>
              {#if trailerKey}
                <button onclick={() => showTrailer = true} class="inline-flex items-center gap-2 px-6 py-4 glass-strong text-ink-secondary hover:text-ink text-sm font-semibold rounded-xl border border-white/[0.06] hover:border-white/10 hover:bg-white/[0.06] transition-all duration-300 ease-exo-out active:scale-95">
                  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-5 h-5"><path stroke-linecap="round" stroke-linejoin="round" d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.347a1.125 1.125 0 0 1 0 1.972l-11.54 6.347a1.125 1.125 0 0 1-1.667-.986V5.653Z" /></svg>
                  Trailer
                </button>
              {/if}
            </div>

            <!-- Overview -->
            {#if data?.overview}
              <div class="max-w-2xl mb-6">
                <p class="text-ink-secondary text-sm md:text-base leading-relaxed">
                  {overviewExpanded ? data.overview : overviewTruncated}
                </p>
                {#if needsTruncation}
                  <button onclick={() => overviewExpanded = !overviewExpanded} class="text-brand-red text-xs font-bold mt-2 hover:text-brand-red/80 transition-colors">
                    {overviewExpanded ? 'Show less' : 'Read more'}
                  </button>
                {/if}
              </div>
            {/if}

            <!-- Metadata Grid -->
            <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 max-w-3xl">
              {#if director}
                <div>
                  <p class="text-[10px] uppercase tracking-widest text-ink-subtle font-bold mb-1">Director</p>
                  <p class="text-sm text-ink font-semibold">{director}</p>
                </div>
              {/if}
              {#if writers.length > 0}
                <div>
                  <p class="text-[10px] uppercase tracking-widest text-ink-subtle font-bold mb-1">Writers</p>
                  <p class="text-sm text-ink font-semibold">{writers.join(', ')}</p>
                </div>
              {/if}
              {#if language}
                <div>
                  <p class="text-[10px] uppercase tracking-widest text-ink-subtle font-bold mb-1">Language</p>
                  <p class="text-sm text-ink font-semibold">{language}</p>
                </div>
              {/if}
              {#if data?.status}
                <div>
                  <p class="text-[10px] uppercase tracking-widest text-ink-subtle font-bold mb-1">Status</p>
                  <p class="text-sm text-ink font-semibold">{data.status}</p>
                </div>
              {/if}
              {#if data?.budget && data.budget > 0}
                <div>
                  <p class="text-[10px] uppercase tracking-widest text-ink-subtle font-bold mb-1">Budget</p>
                  <p class="text-sm text-ink font-semibold">{formatMoney(data.budget)}</p>
                </div>
              {/if}
              {#if data?.revenue && data.revenue > 0}
                <div>
                  <p class="text-[10px] uppercase tracking-widest text-ink-subtle font-bold mb-1">Revenue</p>
                  <p class="text-sm text-ink font-semibold">{formatMoney(data.revenue)}</p>
                </div>
              {/if}
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- ===== CAST SECTION ===== -->
    {#if cast.length > 0}
      <section class="relative z-10 border-t border-white/[0.04] bg-surface-0/90 backdrop-blur-xl">
        <div class="px-4 sm:px-6 lg:px-8 py-12">
          <div class="flex items-end justify-between mb-6">
            <div>
              <h3 class="text-lg md:text-xl font-display font-black text-ink tracking-tight">Cast</h3>
              <p class="text-xs text-ink-subtle mt-1">{cast.length} actors</p>
            </div>
          </div>
          <div class="flex gap-4 sm:gap-6 overflow-x-auto pb-4 scroll-x-clean select-none -mx-4 px-4 sm:-mx-6 sm:px-6 lg:-mx-8 lg:px-8">
            {#each cast as person}
              <div class="flex-shrink-0 w-[120px] sm:w-[140px] text-center group/cast">
                <div class="w-[120px] h-[120px] sm:w-[140px] sm:h-[140px] mx-auto rounded-2xl overflow-hidden bg-surface-1 ring-1 ring-white/[0.04] group-hover/cast:ring-brand-red/40 group-hover/cast:scale-105 transition-all duration-300 shadow-2 mb-3">
                  {#if person.profile_path}
                    <img src={tmdbImg(person.profile_path, 'w185')} alt={person.name} class="w-full h-full object-cover group-hover/cast:scale-110 transition-transform duration-300" loading="lazy" />
                  {:else}
                    <div class="w-full h-full flex items-center justify-center bg-gradient-to-br from-surface-1 to-surface-2 text-ink-subtle text-2xl font-bold">{person.name.charAt(0)}</div>
                  {/if}
                </div>
                <p class="text-sm text-ink font-semibold leading-tight truncate w-full group-hover/cast:text-white transition-colors">{person.name}</p>
                <p class="text-[11px] text-ink-faint truncate w-full mt-0.5">{person.character || ''}</p>
              </div>
            {/each}
          </div>
        </div>
      </section>
    {/if}

    <!-- ===== KEYWORDS ===== -->
    {#if keywordsList.length > 0}
      <section class="relative z-10 border-t border-white/[0.04]">
        <div class="px-4 sm:px-6 lg:px-8 py-8">
          <h3 class="text-[11px] font-bold uppercase tracking-[0.2em] text-ink-subtle mb-3">Keywords</h3>
          <div class="flex flex-wrap gap-2">
            {#each keywordsList as kw}
              <span class="text-[11px] font-medium px-3 py-1.5 rounded-lg bg-white/[0.03] border border-white/[0.04] text-ink-subtle">{kw.name}</span>
            {/each}
          </div>
        </div>
      </section>
    {/if}

    <!-- ===== PRODUCTION COMPANIES ===== -->
    {#if companies.length > 0}
      <section class="relative z-10 border-t border-white/[0.04]">
        <div class="px-4 sm:px-6 lg:px-8 py-8">
          <h3 class="text-[11px] font-bold uppercase tracking-[0.2em] text-ink-subtle mb-4">Production</h3>
          <div class="flex flex-wrap gap-6 items-center">
            {#each companies as company}
              {#if company.logo_path}
                <img src={tmdbImg(company.logo_path, 'w92')} alt={company.name} class="h-8 w-auto opacity-60 hover:opacity-100 transition-opacity" loading="lazy" />
              {:else}
                <span class="text-xs text-ink-subtle font-medium">{company.name}</span>
              {/if}
            {/each}
          </div>
        </div>
      </section>
    {/if}

    <!-- ===== TV EPISODES ===== -->
    {#if mediaType === 'tv' && seasons.length > 0}
      <section class="relative z-10 border-t border-white/[0.04] bg-surface-0/50">
        <div class="px-4 sm:px-6 lg:px-8 py-12">
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
            <div>
              <h2 class="text-2xl md:text-3xl font-display font-black text-ink tracking-tight">Episodes</h2>
              <p class="text-sm text-ink-subtle mt-1">Season {selectedSeason} of {data?.number_of_seasons || seasons.length}</p>
            </div>
            <div class="relative min-w-[200px]">
              <select bind:value={selectedSeason} class="appearance-none w-full glass-strong text-ink text-sm font-bold pl-4 pr-10 py-3 rounded-xl hover:border-white/10 hover:text-ink transition-all cursor-pointer focus:outline-none focus:ring-2 focus:ring-brand-red/30">
                {#each seasons as s}
                  <option value={s.season_number} class="bg-surface-0 text-ink-secondary">Season {s.season_number} ({s.episode_count} eps)</option>
                {/each}
              </select>
              <div class="absolute right-3.5 top-1/2 -translate-y-1/2 pointer-events-none text-ink-muted">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-4 h-4"><path fill-rule="evenodd" d="M5.22 8.22a.75.75 0 0 1 1.06 0L10 11.94l3.72-3.72a.75.75 0 1 1 1.06 1.06l-4.25 4.25a.75.75 0 0 1-1.06 0L5.22 9.28a.75.75 0 0 1 0-1.06Z" clip-rule="evenodd" /></svg>
              </div>
            </div>
          </div>

          {#if seasonEpisodes.length > 0}
            <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              {#each seasonEpisodes as ep}
                <a
                  href={watchUrl(ep.episode_number)}
                  class="group/ep flex gap-4 p-4 rounded-2xl bg-white/[0.02] hover:bg-white/[0.05] border border-white/[0.03] hover:border-white/[0.1] transition-all duration-300"
                >
                  <div class="flex-shrink-0 w-36 sm:w-44 aspect-video rounded-xl overflow-hidden bg-surface-1 relative">
                    {#if ep.still_path}
                      <img src={tmdbImg(ep.still_path, 'w300')} alt={ep.name} class="w-full h-full object-cover transition-transform duration-500 group-hover/ep:scale-105" loading="lazy" />
                    {:else}
                      <div class="w-full h-full flex items-center justify-center bg-surface-0/60">
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="w-6 h-6 text-ink-faint"><path fill-rule="evenodd" d="M4.5 5.653c0-1.426 1.529-2.33 2.779-1.643l11.54 6.347c1.295.712 1.295 2.573 0 3.286L7.28 19.99c-1.25.687-2.779-.218-2.779-1.643V5.653Z" clip-rule="evenodd" /></svg>
                      </div>
                    {/if}
                    <div class="absolute inset-0 bg-black/0 group-hover/ep:bg-black/30 transition-all duration-300 flex items-center justify-center opacity-0 group-hover/ep:opacity-100 backdrop-blur-[2px]">
                      <div class="w-10 h-10 rounded-full bg-white/20 border border-white/30 flex items-center justify-center shadow-2">
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="w-5 h-5 text-white translate-x-[0.5px]"><path fill-rule="evenodd" d="M4.5 5.653c0-1.426 1.529-2.33 2.779-1.643l11.54 6.347c1.295.712 1.295 2.573 0 3.286L7.28 19.99c-1.25.687-2.779-.218-2.779-1.643V5.653Z" clip-rule="evenodd" /></svg>
                      </div>
                    </div>
                    <div class="absolute bottom-2 left-2 glass-strong text-ink-secondary text-[10px] font-bold px-2 py-1 rounded tracking-wider">E{String(ep.episode_number).padStart(2, '0')}</div>
                  </div>
                  <div class="flex-1 min-w-0 py-1">
                    <p class="text-sm text-ink font-semibold line-clamp-1 group-hover/ep:text-white transition-colors">{ep.name || `Episode ${ep.episode_number}`}</p>
                    {#if ep.overview}
                      <p class="text-xs text-ink-muted line-clamp-2 mt-1.5 leading-relaxed">{ep.overview}</p>
                    {/if}
                  </div>
                </a>
              {/each}
            </div>
          {:else}
            <div class="text-center py-16 glass-strong rounded-2xl">
              <p class="text-sm text-ink-muted font-medium">Loading episodes...</p>
            </div>
          {/if}
        </div>
      </section>
    {/if}

    <!-- ===== RECOMMENDATIONS ===== -->
    {#if recommendations.length > 0}
      <section class="relative z-10 border-t border-white/[0.04]">
        <MediaRow title="More Like This" items={recommendations} showViewAll={false} />
      </section>
    {/if}

    <div class="h-28"></div>
  </div>
{/if}

{#if showTrailer && trailerKey}
  <!-- svelte-ignore a11y_no_static_element_interactions a11y_click_events_have_key_events -->
  <div
    class="fixed inset-0 z-[100] flex items-center justify-center bg-black/90 backdrop-blur-md p-4"
    onclick={(event) => { if (event.currentTarget === event.target) showTrailer = false; }}
    role="dialog"
    aria-modal="true"
    aria-label="Trailer"
    tabindex="-1"
    style="animation: watchfy-rise 400ms var(--ease-exo-out) both;"
  >
    <div class="relative w-full max-w-5xl aspect-video rounded-2xl overflow-hidden bg-black shadow-4 border border-white/[0.06]" role="document" style="animation: watchfy-rise 500ms var(--ease-spring) both;">
      <button onclick={() => showTrailer = false} class="absolute top-4 right-4 z-10 w-10 h-10 rounded-full bg-black/60 hover:bg-black/80 border border-white/10 flex items-center justify-center text-ink transition-all duration-200 hover:scale-110 active:scale-95" aria-label="Close trailer">
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-5 h-5"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" /></svg>
      </button>
      <iframe src={`https://www.youtube-nocookie.com/embed/${trailerKey}?autoplay=1&rel=0`} class="w-full h-full" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen title="Trailer"></iframe>
    </div>
  </div>
{/if}