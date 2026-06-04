<script lang="ts">
  import { onMount } from 'svelte';
  import MediaRow from './MediaRow.svelte';
  import EmptyState from './EmptyState.svelte';
  import RowSkeleton from './skeletons/RowSkeleton.svelte';

  let items = $state<any[]>([]);
  let loaded = $state(false);

  async function loadFromAPI() {
    try {
      const token = localStorage.getItem('watchfy_token');
      const headers: Record<string, string> = { 'Content-Type': 'application/json' };
      if (token) headers['Authorization'] = `Bearer ${token}`;
      const res = await fetch('/continue-watching/', { headers });
      if (res.ok) {
        const data = await res.json();
        items = (data || []).map((item: any) => ({
          id: item.tmdb_id,
          title: item.title,
          name: item.title,
          poster_path: item.poster_path,
          vote_average: item.vote_average || 0,
          release_date: item.release_date || '',
          first_air_date: item.first_air_date || '',
          media_type: item.media_type,
          _progress: item.current_time && item.duration ? item.current_time / item.duration : 0,
          _season: item.season,
          _episode: item.episode,
        }));
        loaded = true;
        return;
      }
    } catch {}
    loadFromStorage();
  }

  function loadFromStorage() {
    const seen = new Set<string>();
    const result: any[] = [];
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (!key || !key.startsWith('watchfy:')) continue;
      try {
        const raw = localStorage.getItem(key) || '';
        const data: any = JSON.parse(raw);
        if (!data || typeof data !== 'object') continue;
        if (Object.prototype.hasOwnProperty.call(data, '__proto__') ||
            Object.prototype.hasOwnProperty.call(data, 'constructor')) continue;
        const dedupeKey = `${data.mediaType}:${data.tmdbId}`;
        if (seen.has(dedupeKey)) continue;
        seen.add(dedupeKey);
        result.push({
          id: data.tmdbId,
          title: data.title,
          name: data.title,
          poster_path: data.poster,
          vote_average: 0,
          release_date: '',
          first_air_date: '',
          media_type: data.mediaType,
          _progress: data.duration > 0 ? (data.currentTime / data.duration) : 0,
          _season: data.season,
          _episode: data.episode,
        });
      } catch {}
    }
    items = result.slice(0, 10);
    loaded = true;
  }

  async function dismissItem(item: any) {
    // Remove from UI immediately
    items = items.filter(i => i.id !== item.id || i.media_type !== item.media_type);

    // Remove from API if authenticated
    try {
      const token = localStorage.getItem('watchfy_token');
      if (token) {
        const params = new URLSearchParams({ media_type: item.media_type });
        if (item._season) params.set('season', String(item._season));
        if (item._episode) params.set('episode', String(item._episode));
        await fetch(`/continue-watching/${item.id}?${params}`, {
          method: 'DELETE',
          headers: { 'Authorization': `Bearer ${token}` },
        });
      }
    } catch {}

    // Remove from localStorage
    const storageKey = `watchfy:${item.media_type}:${item.id}`;
    localStorage.removeItem(storageKey);
  }

  onMount(() => {
    if (!loaded) loadFromAPI();
  });
</script>

{#if !loaded}
  <RowSkeleton count={6} />
{:else if items.length > 0}
  <section class="mb-8 sm:mb-10">
    <div class="flex items-center gap-3 mb-4 px-4 md:px-6">
      <div class="w-1 h-6 rounded-full bg-brand-gradient-cta" aria-hidden="true"></div>
      <h2 class="text-lg md:text-2xl font-black text-ink tracking-tight">Continue Watching</h2>
    </div>
    <div class="relative group/track">
      <div class="absolute inset-y-0 left-0 w-8 md:w-16 bg-gradient-to-r from-surface-0 via-surface-0/80 to-transparent z-20 pointer-events-none" aria-hidden="true"></div>
      <div class="absolute inset-y-0 right-0 w-8 md:w-16 bg-gradient-to-l from-surface-0 via-surface-0/80 to-transparent z-20 pointer-events-none" aria-hidden="true"></div>

      <div class="flex gap-3.5 sm:gap-4 overflow-x-auto scroll-x-clean pb-4 pt-1 snap-x snap-mandatory">
        {#each items as item, i (item.id + item.media_type)}
          <div class="flex-shrink-0 w-[140px] sm:w-[170px] snap-start rise-in relative group/card" style="animation-delay: {Math.min(i * 40, 280)}ms">
            <a
              href={item.media_type === 'tv' && item._season && item._episode
                ? `/watch/${item.media_type}/${item.id}?season=${item._season}&episode=${item._episode}`
                : `/watch/${item.media_type}/${item.id}`}
              class="block"
            >
              <div class="relative aspect-[2/3] rounded-2xl overflow-hidden bg-surface-1 border border-white/[0.04] shadow-2">
                {#if item.poster_path}
                  <img
                    src={`https://image.tmdb.org/t/p/w342${item.poster_path}`}
                    alt={item.title}
                    class="w-full h-full object-cover"
                    loading="lazy"
                  />
                {:else}
                  <div class="w-full h-full bg-surface-2 flex items-center justify-center">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-10 h-10 text-ink-faint">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M3.375 19.5h17.25m-17.25 0a1.125 1.125 0 0 1-1.125-1.125M3.375 19.5h7.5c.621 0 1.125-.504 1.125-1.125m-9.75 0V5.625m0 12.75v-1.5c0-.621.504-1.125 1.125-1.125m18.375 2.625V5.625m0 12.75c0 .621-.504 1.125-1.125 1.125m1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125m0 3.75h-7.5A1.125 1.125 0 0 1 12 18.375m9.75-12.75c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125m19.5 0v1.5c0 .621-.504 1.125-1.125 1.125M2.25 5.625v1.5c0 .621.504 1.125 1.125 1.125m0 0h17.25m-17.25 0h7.5c.621 0 1.125.504 1.125 1.125M3.375 8.25c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125m17.25-3.75h-7.5c-.621 0-1.125.504-1.125 1.125m8.625-1.125c.621 0 1.125.504 1.125 1.125v1.5c0 .621-.504 1.125-1.125 1.125m-17.25 0h7.5m-7.5 0c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125M12 10.875v-1.5m0 1.5c0 .621-.504 1.125-1.125 1.125M12 10.875c0 .621.504 1.125 1.125 1.125m-2.25 0c.621 0 1.125.504 1.125 1.125M13.125 12h7.5m-7.5 0c-.621 0-1.125.504-1.125 1.125M20.625 12c.621 0 1.125.504 1.125 1.125v1.5c0 .621-.504 1.125-1.125 1.125m-17.25 0h7.5M12 14.625v-1.5" />
                    </svg>
                  </div>
                {/if}

                <!-- Progress bar -->
                {#if item._progress > 0}
                  <div class="absolute bottom-0 left-0 right-0 h-1 bg-white/10" aria-hidden="true">
                    <div class="h-full bg-brand-gradient-cta transition-all duration-300" style="width: {Math.min(item._progress * 100, 100)}%"></div>
                  </div>
                {/if}

                <!-- Hover overlay -->
                <div class="absolute inset-0 bg-gradient-to-t from-black/90 via-black/30 to-transparent opacity-0 group-hover/card:opacity-100 transition-opacity duration-500">
                  <div class="absolute inset-0 flex items-center justify-center">
                    <div class="w-14 h-14 rounded-full bg-brand-gradient-cta/90 backdrop-blur-sm border border-white/20 flex items-center justify-center shadow-glow-red transform scale-75 group-hover/card:scale-100 transition-all duration-500">
                      <svg viewBox="0 0 24 24" fill="currentColor" class="w-6 h-6 text-white translate-x-[1.5px]">
                        <path d="M8 5v14l11-7z"/>
                      </svg>
                    </div>
                  </div>
                  <div class="absolute bottom-3 left-3 right-3">
                    <p class="text-white text-xs font-bold truncate">{item.title}</p>
                    <div class="flex items-center gap-1.5 mt-0.5">
                      {#if item._season && item._episode}
                        <span class="text-[10px] text-white/70">S{item._season} E{item._episode}</span>
                      {/if}
                      <span class="text-[10px] uppercase tracking-wider font-bold text-brand-red/80">
                        {item.media_type === 'tv' ? 'TV' : 'Movie'}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </a>

            <!-- Dismiss button -->
            <button
              onclick={(e) => { e.preventDefault(); e.stopPropagation(); dismissItem(item); }}
              class="absolute top-2 right-2 w-7 h-7 rounded-full bg-black/60 backdrop-blur-sm border border-white/10 flex items-center justify-center opacity-0 group-hover/card:opacity-100 transition-all duration-200 hover:bg-brand-red/80 hover:border-brand-red/40 z-30"
              aria-label="Remove from continue watching"
            >
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="14" height="14" color="currentColor" fill="none">
                <path d="M18 6L6 18M6 6l12 12" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
              </svg>
            </button>
          </div>
        {/each}
      </div>
    </div>
  </section>
{:else}
  <section class="mb-8 sm:mb-10">
    <div class="flex items-center gap-3 mb-4 px-4 md:px-6">
      <div class="w-1 h-6 rounded-full bg-brand-gradient-cta" aria-hidden="true"></div>
      <h2 class="text-lg md:text-2xl font-black text-ink tracking-tight">Continue Watching</h2>
    </div>
    <div class="flex items-center justify-center py-10 mx-4 md:mx-6 rounded-2xl border border-white/[0.04] bg-white/[0.01]">
      <div class="text-center">
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.25" stroke="currentColor" class="w-8 h-8 mx-auto text-ink-faint mb-3" aria-hidden="true">
          <path stroke-linecap="round" stroke-linejoin="round" d="M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
          <path stroke-linecap="round" stroke-linejoin="round" d="M15.91 11.672a.375.375 0 0 1 0 .656l-5.603 3.113a.375.375 0 0 1-.557-.328V8.887c0-.286.307-.466.557-.327l5.603 3.112Z" />
        </svg>
        <p class="text-xs font-bold text-ink-muted tracking-wider uppercase">Start watching to see your history</p>
      </div>
    </div>
  </section>
{/if}
