<script lang="ts">
  import { getToken, authFetch } from '../lib/auth';
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
    belongs_to_collection?: { id: number; name: string; poster_path: string; backdrop_path: string } | null;
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
  let userRating = $state(0);
  let showRatingUI = $state(false);
  let descriptionExpanded = $state(false);

  $effect(() => {
    (async () => {
      try {
        const token = getToken();
        if (token) {
          const res = await authFetch(`/user/watchlist/${mediaType}/${id}`);
          if (res.ok) { myListFlag = true; return; }
        }
      } catch {}
      try { myListFlag = localStorage.getItem(`watchfy:mylist:${mediaType}:${id}`) === 'true'; }
      catch { myListFlag = false; }
    })();
  });

  async function toggleMyList() {
    const key = `watchfy:mylist:${mediaType}:${id}`;
    const token = getToken();
    if (token) {
      try {
        const url = `/user/watchlist/${mediaType}/${id}`;
        if (myListFlag) { await authFetch(url, { method: 'DELETE' }); myListFlag = false; }
        else { await authFetch(url, { method: 'POST' }); myListFlag = true; }
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
  let companies = $derived(data?.production_companies?.slice(0, 4) || []);

  $effect(() => {
    const currentId = Number(id);
    if (!currentId) return;
    loading = true; error = ''; data = null; selectedSeason = 1; seasonEpisodes = [];
    tmdbApi.details(mediaType, currentId)
      .then((res: any) => {
        data = res;
        tmdbApi.recommendations(mediaType, currentId)
          .then((r: any) => { recommendations = (r.results || []).filter((x: any) => x.backdrop_path || x.poster_path).slice(0, 12).map((x: any) => ({ ...x, media_type: x.media_type || mediaType })); })
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

  async function loadUserRating() {
    const token = getToken();
    if (!token) return;
    try {
      const res = await authFetch(`/user/ratings/${mediaType}/${id}`);
      if (res.ok) { const data = await res.json(); userRating = data.rating || 0; }
    } catch {}
  }

  async function submitRating(rating: number) {
    const token = getToken();
    if (!token) return;
    try {
      await authFetch(`/user/ratings/${mediaType}/${id}`, {
        method: 'POST',
        body: JSON.stringify({ rating }),
      });
      userRating = rating;
      showRatingUI = false;
    } catch {}
  }

  $effect(() => { if (id && mediaType) loadUserRating(); });

  async function shareContent() {
    const shareUrl = window.location.href;
    const shareTitle = title || 'Check this out on Watchfy';
    if (navigator.share) {
      try {
        await navigator.share({ title: shareTitle, text: `Watch ${title} on Watchfy`, url: shareUrl });
        return;
      } catch {}
    }
    try { await navigator.clipboard.writeText(shareUrl); } catch {
      window.open(`https://twitter.com/intent/tweet?text=${encodeURIComponent(`Watch ${title} on Watchfy`)}&url=${encodeURIComponent(shareUrl)}`, '_blank');
    }
  }
</script>

<svelte:head>
  <title>{title ? `${title} - Watchfy` : 'Loading...'}</title>
</svelte:head>

{#if loading}
  <DetailSkeleton />
{:else if error}
  <div class="min-h-screen flex items-center justify-center bg-base px-4">
    <EmptyState variant="error" icon="alert" title="Something went wrong" message={error} ctaLabel="Try Again" oncTaClick={() => window.location.reload()} />
  </div>
{:else}
  <div class="min-h-screen bg-base text-ink">

    <!-- ===== BACKDROP BANNER (subtle) ===== -->
    {#if backdropUrl}
      <div class="relative w-full h-[280px] md:h-[380px] overflow-hidden">
        <img src={backdropUrl} alt="" class="w-full h-full object-cover opacity-60" loading="eager" />
        <div class="absolute inset-0 bg-gradient-to-b from-transparent to-base"></div>
      </div>
    {/if}

    <div class="max-w-[1280px] mx-auto px-4 md:px-6 -mt-24 md:-mt-32 relative z-10">
      <div class="flex flex-col md:flex-row gap-6 md:gap-8">
        <!-- Poster -->
        <div class="flex-shrink-0 w-[160px] md:w-[260px] aspect-[2/3] rounded-xl overflow-hidden bg-base-2 mx-auto md:mx-0">
          {#if posterUrl}
            <img src={posterUrl} alt={title} class="w-full h-full object-cover" loading="eager" />
          {:else}
            <div class="w-full h-full flex items-center justify-center text-ink-muted">
              <svg viewBox="0 0 24 24" class="w-12 h-12" fill="currentColor" aria-hidden="true">
                <path d="M18 4l2 4h-3l-2-4h-2l2 4h-3l-2-4H8l2 4H7L5 4H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V4h-4z" />
              </svg>
            </div>
          {/if}
        </div>

        <!-- Info column -->
        <div class="flex-1 min-w-0">
          <h1 class="text-2xl md:text-4xl font-bold text-ink leading-tight">{title}</h1>
          {#if data?.tagline}
            <p class="text-sm text-ink-muted italic mt-1">{data.tagline}</p>
          {/if}

          <!-- Badges row -->
          <div class="flex flex-wrap items-center gap-2 mt-3 text-sm text-ink-secondary">
            {#if year}<span>{year}</span>{/if}
            {#if rating}
              <span class="text-ink-muted">·</span>
              <span class="text-ink">{rating} ★</span>
              <span class="text-ink-muted">({votes.toLocaleString()})</span>
            {/if}
            {#if runtime}
              <span class="text-ink-muted">·</span>
              <span>{runtime}</span>
            {/if}
            {#if mediaType === 'tv' && data?.number_of_seasons}
              <span class="text-ink-muted">·</span>
              <span>{data.number_of_seasons} {data.number_of_seasons === 1 ? 'season' : 'seasons'}</span>
            {/if}
          </div>

          <!-- Genres -->
          {#if genres.length > 0}
            <div class="flex flex-wrap gap-2 mt-3">
              {#each genres as genre}
                <a href="/search?genre={genre.id}" class="text-xs px-3 py-1 bg-base-2 text-ink-secondary rounded-full hover:bg-base-3">
                  {genre.name}
                </a>
              {/each}
            </div>
          {/if}

          <!-- Action bar -->
          <div class="flex flex-wrap items-center gap-2 mt-5">
            <a href={watchUrl()} class="inline-flex items-center gap-2 h-10 px-6 bg-white text-base text-sm font-medium rounded-full hover:bg-white/90">
              <svg viewBox="0 0 24 24" class="w-5 h-5" fill="currentColor" aria-hidden="true">
                <path d="M8 5v14l11-7z" />
              </svg>
              {mediaType === 'tv' ? `Play S1:E1` : 'Play'}
            </a>
            <button
              type="button"
              onclick={toggleMyList}
              class="inline-flex items-center gap-2 h-10 px-4 bg-base-2 text-ink rounded-full text-sm font-medium hover:bg-base-3"
              aria-label="Save to My List"
            >
              {#if myListFlag}
                <svg viewBox="0 0 24 24" class="w-5 h-5" fill="currentColor" aria-hidden="true">
                  <path d="M9 16.2l-3.5-3.5L4 14.2l5 5 11-11-1.5-1.5z" />
                </svg>
                Saved
              {:else}
                <svg viewBox="0 0 24 24" class="w-5 h-5" fill="currentColor" aria-hidden="true">
                  <path d="M12 4v16m8-8H4" stroke="currentColor" stroke-width="2" fill="none" />
                </svg>
              {/if}
            </button>
            {#if trailerKey}
              <button
                type="button"
                onclick={() => showTrailer = true}
                class="inline-flex items-center gap-2 h-10 px-4 bg-base-2 text-ink rounded-full text-sm font-medium hover:bg-base-3"
              >
                <svg viewBox="0 0 24 24" class="w-5 h-5" fill="currentColor" aria-hidden="true">
                  <path d="M4 6h16v12H4z" fill="none" stroke="currentColor" stroke-width="2" />
                  <path d="M10 9l5 3-5 3z" />
                </svg>
                Trailer
              </button>
            {/if}
            <button
              type="button"
              onclick={shareContent}
              class="yt-icon-btn"
              aria-label="Share"
              title="Share"
            >
              <svg viewBox="0 0 24 24" class="w-5 h-5" fill="currentColor" aria-hidden="true">
                <path d="M15 8a3 3 0 1 0-2.83-4H15L12 1 9 4h.83A3 3 0 0 0 12 10a3 3 0 0 0 3-2zM4 13a3 3 0 0 1 2-2.83V13l-2 1l-1-1H4zm11 4a3 3 0 1 0-2.83 4h.83l-3-3l1-1l1 1v-.83A3 3 0 0 0 15 17zm6-4h-1l-1 1l-2-1v-2.83A3 3 0 0 1 21 13z" />
              </svg>
            </button>
            <div class="relative">
              <button
                type="button"
                onclick={() => showRatingUI = !showRatingUI}
                class="yt-icon-btn"
                aria-label="Rate"
                title="Rate"
              >
                <svg viewBox="0 0 24 24" class="w-5 h-5" fill={userRating > 0 ? 'currentColor' : 'none'} stroke="currentColor" stroke-width="2" aria-hidden="true">
                  <path d="M12 2l3 7h7l-5.5 4.5L18 21l-6-4l-6 4l1.5-7.5L2 9h7z" />
                </svg>
              </button>
              {#if showRatingUI}
                <div class="absolute top-full mt-2 right-0 bg-base-1 border border-white/10 rounded-lg shadow-2xl p-2 flex gap-1 z-50">
                  {#each [1, 2, 3, 4, 5] as star}
                    <button
                      onclick={() => submitRating(star)}
                      aria-label={`Rate ${star} out of 5`}
                      class="w-8 h-8 rounded flex items-center justify-center hover:bg-base-3"
                    >
                      <svg viewBox="0 0 24 24" class="w-5 h-5" fill={star <= userRating ? 'currentColor' : 'none'} stroke="currentColor" stroke-width="2" aria-hidden="true">
                        <path d="M12 2l3 7h7l-5.5 4.5L18 21l-6-4l-6 4l1.5-7.5L2 9h7z" />
                      </svg>
                    </button>
                  {/each}
                </div>
              {/if}
            </div>
          </div>

          <!-- Description -->
          {#if data?.overview}
            <div class="mt-5 p-3 bg-base-2 rounded-xl text-sm text-ink leading-relaxed max-w-3xl">
              <p class={descriptionExpanded ? '' : 'line-clamp-3'}>
                {data.overview}
              </p>
              {#if data.overview.length > 200}
                <button onclick={() => descriptionExpanded = !descriptionExpanded} class="text-ink-secondary hover:text-ink text-sm font-medium mt-1">
                  {descriptionExpanded ? 'Show less' : '...more'}
                </button>
              {/if}
            </div>
          {/if}
        </div>
      </div>
    </div>

    <!-- ===== CAST ===== -->
    {#if cast.length > 0}
      <section class="max-w-[1280px] mx-auto px-4 md:px-6 mt-10">
        <h2 class="text-lg font-medium text-ink mb-3">Cast</h2>
        <div class="flex gap-3 overflow-x-auto no-scrollbar pb-2 -mx-4 px-4 md:-mx-6 md:px-6">
          {#each cast as person}
            <a href="/search?q={encodeURIComponent(person.name)}" class="flex-shrink-0 w-32 text-center group/cast">
              <div class="w-32 h-32 rounded-full overflow-hidden bg-base-2 mb-2">
                {#if person.profile_path}
                  <img src={tmdbImg(person.profile_path, 'w185')} alt={person.name} class="w-full h-full object-cover group-hover/cast:scale-110 transition-transform duration-300" loading="lazy" />
                {:else}
                  <div class="w-full h-full flex items-center justify-center bg-base-3 text-ink-secondary text-2xl font-medium">
                    {person.name.charAt(0)}
                  </div>
                {/if}
              </div>
              <p class="text-sm text-ink truncate group-hover/cast:text-white">{person.name}</p>
              {#if person.character}
                <p class="text-xs text-ink-muted truncate">{person.character}</p>
              {/if}
            </a>
          {/each}
        </div>
      </section>
    {/if}

    <!-- ===== TV EPISODES ===== -->
    {#if mediaType === 'tv' && seasons.length > 0}
      <section class="max-w-[1280px] mx-auto px-4 md:px-6 mt-10">
        <div class="flex items-center justify-between mb-4">
          <h2 class="text-lg font-medium text-ink">Episodes</h2>
          <select bind:value={selectedSeason} class="bg-base-2 border border-white/10 text-ink text-sm rounded-full px-3 py-1.5 focus:outline-none focus:border-yt-blue">
            {#each seasons as s}
              <option value={s.season_number} class="bg-base">Season {s.season_number}</option>
            {/each}
          </select>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
          {#each seasonEpisodes as ep}
            <a
              href={watchUrl(ep.episode_number)}
              class="group/ep flex gap-3 p-2 rounded-xl hover:bg-base-2 transition-colors duration-100"
            >
              <div class="flex-shrink-0 w-44 aspect-video rounded-lg overflow-hidden bg-base-2 relative">
                {#if ep.still_path}
                  <img src={tmdbImg(ep.still_path, 'w300')} alt={ep.name} class="w-full h-full object-cover" loading="lazy" />
                {:else}
                  <div class="w-full h-full flex items-center justify-center text-ink-muted">E{String(ep.episode_number).padStart(2, '0')}</div>
                {/if}
              </div>
              <div class="flex-1 min-w-0 py-1">
                <div class="flex items-center gap-2">
                  <span class="text-sm text-ink-muted">{ep.episode_number}</span>
                  <p class="text-sm font-medium text-ink line-clamp-1">{ep.name || `Episode ${ep.episode_number}`}</p>
                </div>
                {#if ep.overview}
                  <p class="text-xs text-ink-muted line-clamp-2 mt-1 leading-relaxed">{ep.overview}</p>
                {/if}
              </div>
            </a>
          {/each}
        </div>
      </section>
    {/if}

    <!-- ===== RECOMMENDATIONS ===== -->
    {#if recommendations.length > 0}
      <section class="max-w-[1280px] mx-auto px-4 md:px-6 mt-10">
        <h2 class="text-lg font-medium text-ink mb-3">You may also like</h2>
        <MediaRow title="" items={recommendations} showViewAll={false} />
      </section>
    {/if}

    <!-- ===== PRODUCTION COMPANIES ===== -->
    {#if companies.length > 0}
      <section class="max-w-[1280px] mx-auto px-4 md:px-6 mt-10 mb-10">
        <h3 class="text-xs uppercase tracking-widest text-ink-muted font-medium mb-3">Production</h3>
        <div class="flex flex-wrap gap-6 items-center">
          {#each companies as company}
            {#if company.logo_path}
              <img src={tmdbImg(company.logo_path, 'w92')} alt={company.name} class="h-6 w-auto opacity-60 hover:opacity-100 transition-opacity" loading="lazy" />
            {:else}
              <span class="text-sm text-ink-muted">{company.name}</span>
            {/if}
          {/each}
        </div>
      </section>
    {/if}
  </div>
{/if}

{#if showTrailer && trailerKey}
  <div
    class="fixed inset-0 z-[100] flex items-center justify-center bg-black/90 p-4"
    onclick={(event) => { if (event.currentTarget === event.target) showTrailer = false; }}
    role="dialog"
    aria-modal="true"
    aria-label="Trailer"
    tabindex="-1"
  >
    <div class="relative w-full max-w-5xl aspect-video rounded-xl overflow-hidden bg-black">
      <button onclick={() => showTrailer = false} class="absolute top-3 right-3 z-10 w-9 h-9 rounded-full bg-black/70 hover:bg-black/90 flex items-center justify-center text-ink" aria-label="Close trailer">
        <svg viewBox="0 0 24 24" class="w-5 h-5" fill="currentColor" aria-hidden="true">
          <path d="M19 6.4L17.6 5 12 10.6 6.4 5 5 6.4 10.6 12 5 17.6 6.4 19 12 13.4 17.6 19 19 17.6 13.4 12 19 6.4z" />
        </svg>
      </button>
      <iframe src={`https://www.youtube-nocookie.com/embed/${trailerKey}?autoplay=1&rel=0`} class="w-full h-full" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen title="Trailer"></iframe>
    </div>
  </div>
{/if}
