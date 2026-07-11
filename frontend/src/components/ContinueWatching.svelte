<script lang="ts">
  import { onMount } from 'svelte';
  import MediaRow from './MediaRow.svelte';
  import RowSkeleton from './skeletons/RowSkeleton.svelte';
  import { getToken } from '../lib/auth';

  let items = $state<any[]>([]);
  let loaded = $state(false);

  async function loadFromAPI() {
    try {
      const token = getToken();
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
          backdrop_path: item.backdrop_path,
          vote_average: item.vote_average || 0,
          release_date: item.release_date || '',
          first_air_date: item.first_air_date || '',
          media_type: item.media_type,
          _progress: item.current_time && item.duration ? item.current_time / item.duration : 0,
          _season: item.season,
          _episode: item.episode,
          _startTime: item.current_time || 0,
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
      if (!key || !key.startsWith('stersh:')) continue;
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
          backdrop_path: data.backdrop,
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
  <RowSkeleton count={4} />
{:else if items.length > 0}
  <MediaRow title="Continue watching" items={items} showViewAll={false} />
{/if}
