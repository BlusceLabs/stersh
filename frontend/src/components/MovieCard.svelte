<script lang="ts">
  let { movie, type = 'movie' } = $props();
  
  const mediaType = typeof type === 'string' ? type : (movie.media_type === 'tv' ? 'tv' : 'movie');
  const id = movie.id;
  const title = movie.title || movie.name || 'Untitled';
  const year = (movie.release_date || movie.first_air_date || '').split('-')[0] || '—';
  const poster = movie.poster_path 
    ? `https://image.tmdb.org/t/p/w500${movie.poster_path}` 
    : '/placeholder-movie.jpg';
  const rating = movie.vote_average || 0;
</script>

<a href={`/${mediaType}/${id}`} class="group block">
  <div class="relative bg-surface-raised rounded-lg overflow-hidden aspect-[2/3] transition-transform duration-300">
    <img 
      src={poster} 
      alt={title}
      class="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"
      loading="lazy"
    />
    {#if rating > 0}
      <div class="absolute top-2 right-2 bg-surface-sunken/70 text-primary text-xs px-2 py-1 rounded flex items-center gap-1">
        <span>★</span>
        <span>{rating.toFixed(1)}</span>
      </div>
    {/if}
  </div>
  <div class="mt-2">
    <h3 class="font-medium text-sm line-clamp-1 text-text">{title}</h3>
    <p class="text-xs text-text-muted">{year}</p>
  </div>
</a>

<style>
  a {
    text-decoration: none;
  }
</style>