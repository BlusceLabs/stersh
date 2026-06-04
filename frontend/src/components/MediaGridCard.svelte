<script lang="ts">
  /**
   * Compact media card optimized for grid layouts (search results,
   * movies browse, TV browse). Lighter than MovieCard — no progress
   * bar, no continue-watching routing. Uses the same visual language
   * but with grid-friendly density.
   */
  let {
    movie,
  }: {
    movie: any;
  } = $props();

  let explicitType: 'movie' | 'tv' = $derived(
    movie.media_type === 'tv' || movie.name ? 'tv' : 'movie'
  );
  let id = $derived(movie.id);
  let title = $derived(movie.title || movie.name || 'Untitled Feature');
  let year = $derived((movie.release_date || movie.first_air_date || '').split('-')[0] || '');
  let rating = $derived(movie.vote_average || 0);
  let hasRating = $derived(rating > 0);
  let hasPoster = $derived(Boolean(movie.poster_path));
</script>

<a
  href={`/${explicitType}/${id}`}
  class="group block focus:outline-none rounded-2xl"
  aria-label={`View details for ${title}`}
>
  <div
    class="relative aspect-[2/3] rounded-2xl overflow-hidden bg-surface-1 transition-all duration-500 ease-exo-out transform group-hover:-translate-y-1 group-hover:scale-[1.03] focus-visible:ring-2 focus-visible:ring-brand-red/50"
  >
    {#if hasPoster}
      <img
        src={`https://image.tmdb.org/t/p/w500${movie.poster_path}`}
        alt=""
        class="w-full h-full object-cover transition-transform duration-700 ease-exo-out group-hover:scale-[1.06] group-hover:brightness-110"
        loading="lazy"
        decoding="async"
      />
    {:else}
      <div class="w-full h-full relative overflow-hidden">
        <div class="absolute inset-0 bg-gradient-to-br from-surface-1 via-surface-2 to-surface-0"></div>
        <div class="absolute -top-8 -right-8 w-32 h-32 rounded-full bg-brand-red/10 blur-2xl"></div>
        <div class="absolute -bottom-8 -left-8 w-32 h-32 rounded-full bg-brand-purple/10 blur-2xl"></div>
        <div class="relative w-full h-full flex flex-col items-center justify-center text-ink-subtle gap-2 p-3">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.25" stroke="currentColor" class="w-10 h-10 opacity-60" aria-hidden="true">
            <path stroke-linecap="round" stroke-linejoin="round" d="M3.375 19.5h17.25m-17.25 0a1.125 1.125 0 0 1-1.125-1.125M3.375 19.5h7.5c.621 0 1.125-.504 1.125-1.125m-9.75 0V5.625m0 12.75v-1.5c0-.621.504-1.125 1.125-1.125m18.375 2.625V5.625m0 12.75c0 .621-.504 1.125-1.125 1.125m1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125m0 3.75h-7.5A1.125 1.125 0 0 1 12 18.375m9.75-12.75c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125m19.5 0v1.5c0 .621-.504 1.125-1.125 1.125M2.25 5.625v1.5c0 .621.504 1.125 1.125 1.125m0 0h17.25m-17.25 0h7.5c.621 0 1.125.504 1.125 1.125M3.375 8.25c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125m17.25-3.75h-7.5c-.621 0-1.125.504-1.125 1.125m8.625-1.125c.621 0 1.125.504 1.125 1.125v1.5c0 .621-.504 1.125-1.125 1.125m-17.25 0h7.5m-7.5 0c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125M12 10.875v-1.5m0 1.5c0 .621-.504 1.125-1.125 1.125M12 10.875c0 .621.504 1.125 1.125 1.125m-2.25 0c.621 0 1.125.504 1.125 1.125M13.125 12h7.5m-7.5 0c-.621 0-1.125.504-1.125 1.125M20.625 12c.621 0 1.125.504 1.125 1.125v1.5c0 .621-.504 1.125-1.125 1.125m-17.25 0h7.5M12 14.625v-1.5" />
          </svg>
          <span class="text-[9px] font-bold tracking-[0.18em] uppercase opacity-60 text-center line-clamp-2 leading-tight">{title}</span>
        </div>
      </div>
    {/if}

    {#if hasRating}
      <div
        class="absolute top-2 right-2 glass-strong text-accent-warm font-bold text-[11px] px-2 py-1 rounded-lg flex items-center gap-1 shadow-2"
        aria-label={`Rating ${rating.toFixed(1)} out of 10`}
      >
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-3 h-3" aria-hidden="true">
          <path fill-rule="evenodd" d="M10.868 2.884c-.321-.772-1.415-.772-1.736 0l-1.83 4.401-4.753.381c-.833.067-1.171 1.107-.536 1.651l3.6 3.1-.114 4.715c-.02.83.844 1.44 1.54 1.022l4.133-2.514 4.132 2.514c.695.418 1.56-.192 1.54-1.022l-.114-4.715 3.6-3.1c.635-.544.297-1.584-.536-1.65l-4.752-.382-1.831-4.401Z" clip-rule="evenodd" />
        </svg>
        <span>{rating.toFixed(1)}</span>
      </div>
    {/if}

    <div
      class="absolute inset-x-0 bottom-0 h-1/2 bg-gradient-to-t from-black/70 via-black/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500 ease-exo-out pointer-events-none"
      aria-hidden="true"
    ></div>
  </div>

  <div class="mt-3 px-0.5">
    <h3 class="font-semibold text-ink-secondary group-hover:text-ink text-sm tracking-tight line-clamp-1 transition-colors duration-200">
      {title}
    </h3>
    <div class="flex items-center gap-2 mt-1 text-[11px] font-medium text-ink-subtle group-hover:text-ink-muted transition-colors duration-200">
      {#if year}
        <span>{year}</span>
        <span class="w-1 h-1 rounded-full bg-ink-faint" aria-hidden="true"></span>
      {/if}
      <span class="uppercase tracking-wider text-[10px] font-bold text-ink-faint group-hover:text-brand-red/80 transition-colors duration-200">
        {explicitType === 'tv' ? 'TV Series' : 'Movie'}
      </span>
    </div>
  </div>
</a>
