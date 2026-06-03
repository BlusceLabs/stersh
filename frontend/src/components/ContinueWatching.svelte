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

  onMount(() => {
    if (!loaded) loadFromAPI();
  });
</script>

{#if !loaded}
  <RowSkeleton count={6} />
{:else if items.length > 0}
  <MediaRow
    title="Continue Watching"
    items={items}
    showViewAll={false}
  />
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
