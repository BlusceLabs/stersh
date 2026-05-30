<script lang="ts">
  let { movie, type = 'movie', progress = undefined, season = undefined, episode = undefined } = $props<{
    movie: any;
    type?: string;
    progress?: number;
    season?: number;
    episode?: number;
  }>();
  
  // Clean Data Normalization Engine
  const mediaType = typeof type === 'string' ? type : (movie.media_type === 'tv' ? 'tv' : 'movie');
  const id = movie.id;
  const watchHref = season && episode ? `/${mediaType}/${id}?season=${season}&episode=${episode}` : `/${mediaType}/${id}`;
  const title = movie.title || movie.name || 'Untitled Feature';
  const year = (movie.release_date || movie.first_air_date || '').split('-')[0] || '—';
  const poster = movie.poster_path 
    ? `https://image.tmdb.org/t/p/w500${movie.poster_path}` 
    : 'https://images.unsplash.com/photo-1594909122845-11baa439b7bf?q=80&w=1470&auto=format&fit=crop'; // Cinematic fallback
  const rating = movie.vote_average || 0;
</script>

<a 
  href={watchHref} 
  class="group block focus:outline-none"
  aria-label={`View details for ${title}`}
>
  <div class="relative bg-zinc-900 rounded-xl overflow-hidden aspect-[2/3] border border-zinc-800/40 shadow-lg shadow-black/50 transition-all duration-500 ease-out transform group-hover:-translate-y-1.5 group-hover:border-zinc-700/60 group-hover:shadow-2xl group-hover:shadow-black/80 focus-within:ring-2 focus-within:ring-red-500/50">
    
    <img 
      src={poster} 
      alt="" 
      class="w-full h-full object-cover transition-transform duration-700 ease-out group-hover:scale-105 brightness-[0.95] group-hover:brightness-110" 
      loading="lazy"
    />
    
    {#if rating > 0}
      <div class="absolute top-2 right-2 bg-zinc-950/75 backdrop-blur-md text-amber-400 font-bold text-[11px] px-2 py-1 rounded-lg flex items-center gap-1 border border-zinc-800/50 shadow-md">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-3 h-3">
          <path fill-rule="evenodd" d="M10.868 2.884c-.321-.772-1.415-.772-1.736 0l-1.83 4.401-4.753.381c-.833.067-1.171 1.107-.536 1.651l3.6 3.1-.114 4.715c-.02.83.844 1.44 1.54 1.022l4.133-2.514 4.132 2.514c.695.418 1.56-.192 1.54-1.022l-.114-4.715 3.6-3.1c.635-.544.297-1.584-.536-1.65l-4.752-.382-1.831-4.401Z" clip-rule="evenodd" />
        </svg>
        <span>{rating.toFixed(1)}</span>
      </div>
    {/if}

    <div class="absolute inset-0 bg-gradient-to-t from-zinc-950 via-transparent to-transparent opacity-0 group-hover:opacity-40 transition-opacity duration-500 pointer-events-none"></div>
    
    {#if progress !== undefined && progress > 0}
      <div class="absolute bottom-0 left-0 right-0 h-1 bg-zinc-800">
        <div class="h-full bg-red-500 transition-all duration-300" style="width: {Math.min(progress * 100, 100)}%"></div>
      </div>
    {/if}
  </div>

  <div class="mt-2.5 px-0.5">
    <h3 class="font-semibold text-zinc-200 group-hover:text-white text-sm tracking-tight line-clamp-1 transition-colors duration-200">
      {title}
    </h3>
    <div class="flex items-center gap-2 mt-0.5 text-[11px] font-medium text-zinc-500 group-hover:text-zinc-400 transition-colors duration-200">
      <span>{year}</span>
      <span class="w-1 h-1 rounded-full bg-zinc-700"></span>
      <span class="uppercase tracking-wider text-[10px] text-zinc-600 group-hover:text-red-400/80 transition-colors duration-200 font-bold">
        {mediaType === 'tv' ? 'TV' : 'Movie'}
      </span>
    </div>
  </div>
</a>