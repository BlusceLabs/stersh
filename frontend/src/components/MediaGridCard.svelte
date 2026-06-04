<script lang="ts">
  /**
   * Compact YouTube-style media card used inside grid pages (search,
   * movies, tv, mylist, genre). Same visual language as MovieCard but
   * optimised for grid density (no extra meta row variant).
   */
  let {
    movie,
  }: {
    movie: any;
  } = $props();

  let mediaType: 'movie' | 'tv' = $derived(
    movie.media_type === 'tv' || movie.name ? 'tv' : 'movie'
  );
  let id = $derived(movie.id);
  let title = $derived(movie.title || movie.name || 'Untitled');
  let thumb = $derived(movie.backdrop_path || movie.poster_path || '');
  let hasThumb = $derived(Boolean(thumb));
  let year = $derived((movie.release_date || movie.first_air_date || '').split('-')[0] || '');
  let rating = $derived(movie.vote_average || 0);
  let voteCount = $derived(movie.vote_count || 0);

  let channelName = $derived(
    movie?.production_companies?.[0]?.name ||
    movie?.credits?.crew?.find((c: any) => c.job === 'Director')?.name ||
    (mediaType === 'tv' ? 'Series' : 'Movie')
  );

  let viewsLabel = $derived(formatViews(voteCount || (movie.popularity ? Math.round(movie.popularity * 100) : 0)));

  function formatViews(n: number): string {
    if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M views`;
    if (n >= 1_000) return `${(n / 1_000).toFixed(0)}K views`;
    if (n > 0) return `${n} views`;
    return '';
  }
</script>

<a
  href={`/${mediaType}/${id}`}
  class="group block focus:outline-none"
  aria-label={`View ${title}`}
>
  <div class="relative w-full aspect-video rounded-xl overflow-hidden bg-base-2">
    {#if hasThumb}
      <img
        src={`https://image.tmdb.org/t/p/w780${thumb}`}
        srcset={`https://image.tmdb.org/t/p/w342${thumb} 342w, https://image.tmdb.org/t/p/w780${thumb} 780w`}
        sizes="(max-width: 640px) 50vw, (max-width: 1024px) 33vw, 25vw"
        alt={title}
        class="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"
        loading="lazy"
        decoding="async"
      />
    {:else}
      <div class="w-full h-full flex items-center justify-center bg-base-2 text-ink-muted">
        <svg viewBox="0 0 24 24" class="w-12 h-12" fill="currentColor" aria-hidden="true">
          <path d="M18 4l2 4h-3l-2-4h-2l2 4h-3l-2-4H8l2 4H7L5 4H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V4h-4z" />
        </svg>
      </div>
    {/if}
  </div>

  <div class="flex gap-3 mt-3">
    <div class="flex-shrink-0 w-9 h-9 rounded-full bg-base-3 overflow-hidden flex items-center justify-center text-sm font-medium text-ink">
      {channelName.charAt(0).toUpperCase()}
    </div>
    <div class="flex-1 min-w-0">
      <h3 class="text-base font-medium text-ink leading-snug line-clamp-2">
        {title}
      </h3>
      <div class="mt-1 text-sm text-ink-secondary">
        <div class="hover:text-ink transition-colors duration-100 truncate">{channelName}</div>
        <div class="flex items-center gap-1">
          {#if viewsLabel}<span>{viewsLabel}</span><span class="text-ink-muted">·</span>{/if}
          {#if year}<span>{year}</span>{/if}
          {#if !viewsLabel && rating > 0}
            <span class="text-ink-muted">·</span>
            <span class="text-ink-muted">★ {rating.toFixed(1)}</span>
          {/if}
        </div>
      </div>
    </div>
  </div>
</a>
