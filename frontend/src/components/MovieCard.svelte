<script lang="ts">
  export let id: number;
  export let title: string = 'Movie Title';
  export let year: string = '2024';
  export let poster: string = '/placeholder-movie.jpg';
  export let rating: number = 0;
  export let type: 'movie' | 'tv' = 'movie';
</script>

<a href={`/${type}/${id}`} class="group block">
  <div class="relative bg-zinc-800 rounded-lg overflow-hidden aspect-[2/3] transition-transform duration-300">
    <img 
      src={poster} 
      alt={title}
      class="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"
      loading="lazy"
    />
    {#if rating > 0}
      <div class="absolute top-2 right-2 bg-black/70 text-yellow-500 text-xs px-2 py-1 rounded flex items-center gap-1">
        <span>★</span>
        <span>{rating.toFixed(1)}</span>
      </div>
    {/if}
  </div>
  <div class="mt-2">
    <h3 class="font-medium text-sm line-clamp-1 text-white">{title}</h3>
    <p class="text-xs text-gray-400">{year}</p>
  </div>
</a>

<style>
  a {
    text-decoration: none;
  }
</style>