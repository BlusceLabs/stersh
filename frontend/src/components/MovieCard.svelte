<script lang="ts">
  /**
   * YouTube-style video card. Uses TMDB backdrop (16:9) as the "video"
   * thumbnail, with title + channel (director/studio) + views + time below.
   */
  let {
    movie,
    type = 'movie',
    progress = undefined,
    season = undefined,
    episode = undefined,
    startTime = undefined,
  }: {
    movie: any;
    type?: 'movie' | 'tv' | string;
    progress?: number;
    season?: number;
    episode?: number;
    startTime?: number;
  } = $props();

  let mediaType = $derived(
    type === 'tv' || movie.media_type === 'tv' ? 'tv' : 'movie'
  );
  let id = $derived(movie.id);
  let watchHref = $derived(
    season && episode
      ? `/${mediaType}/${id}?season=${season}&episode=${episode}${startTime ? `&t=${Math.floor(startTime)}` : ''}`
      : `/${mediaType}/${id}${startTime ? `?t=${Math.floor(startTime)}` : ''}`
  );
  let title = $derived(movie.title || movie.name || 'Untitled');
  let thumb = $derived(movie.backdrop_path || movie.poster_path || '');
  let hasThumb = $derived(Boolean(thumb));
  let year = $derived((movie.release_date || movie.first_air_date || '').split('-')[0] || '');
  let rating = $derived(movie.vote_average || 0);
  let voteCount = $derived(movie.vote_count || 0);
  let runtime = $derived(movie.runtime);
  let runtimeLabel = $derived(runtime ? `${Math.floor(runtime / 60)}h ${runtime % 60}m` : '');
  let isTV = $derived(mediaType === 'tv');

  // YouTube-style: "channel name" = first production company, or director fallback
  let channelName = $derived(
    movie?.production_companies?.[0]?.name ||
    movie?.credits?.crew?.find((c: any) => c.job === 'Director')?.name ||
    (isTV ? 'Series' : 'Movie')
  );

  // "views" — show vote_count as a number, fall back to popularity
  let viewsLabel = $derived(formatViews(voteCount || (movie.popularity ? Math.round(movie.popularity * 100) : 0)));

  // "time" — show year or computed age
  let timeLabel = $derived(year);

  function formatViews(n: number): string {
    if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M views`;
    if (n >= 1_000) return `${(n / 1_000).toFixed(0)}K views`;
    if (n > 0) return `${n} views`;
    return '';
  }
</script>

<a
  href={watchHref}
  class="group block focus:outline-none"
  aria-label={`View ${title}`}
>
  <!-- 16:9 Thumbnail -->
  <div class="relative w-full aspect-video rounded-xl overflow-hidden bg-base-2">
    {#if hasThumb}
      <img
        src={`https://image.tmdb.org/t/p/w780${thumb}`}
        srcset={`https://image.tmdb.org/t/p/w342${thumb} 342w, https://image.tmdb.org/t/p/w780${thumb} 780w, https://image.tmdb.org/t/p/w1280${thumb} 1280w`}
        sizes="(max-width: 640px) 100vw, (max-width: 1280px) 50vw, 33vw"
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

    <!-- Duration / runtime badge (bottom-right) -->
    {#if runtimeLabel && !progress}
      <div class="absolute bottom-1.5 right-1.5 bg-black/80 text-white text-xs font-medium px-1.5 py-0.5 rounded">
        {runtimeLabel}
      </div>
    {/if}

    <!-- Continue-watching progress bar (bottom of thumbnail) -->
    {#if progress !== undefined && progress > 0}
      <div class="absolute bottom-0 left-0 right-0 h-1 bg-white/30">
        <div
          class="h-full bg-yt-red"
          style="width: {Math.min(progress * 100, 100)}%"
        ></div>
      </div>
    {/if}
  </div>

  <!-- Meta row: channel avatar + text column -->
  <div class="flex gap-3 mt-3">
    <!-- Channel avatar (initials circle, YouTube-style) -->
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
          {#if timeLabel}<span>{timeLabel}</span>{/if}
          {#if rating > 0 && !viewsLabel}
            <span class="text-ink-muted">·</span>
            <span class="text-ink-muted">★ {rating.toFixed(1)}</span>
          {/if}
        </div>
      </div>
    </div>

    <!-- 3-dot menu (decorative for now) -->
    <button
      type="button"
      class="yt-icon-btn flex-shrink-0 -mt-1 opacity-0 group-hover:opacity-100"
      aria-label="More options"
      tabindex={-1}
    >
      <svg viewBox="0 0 24 24" class="w-5 h-5" fill="currentColor" aria-hidden="true">
        <circle cx="5" cy="12" r="2" /><circle cx="12" cy="12" r="2" /><circle cx="19" cy="12" r="2" />
      </svg>
    </button>
  </div>
</a>
