<script lang="ts">
  import MediaRow from './MediaRow.svelte';
  import RowSkeleton from './skeletons/RowSkeleton.svelte';

  let items = $state<any[]>([]);
  let loaded = $state(false);

  function loadFromStorage() {
    const entries: { type: string; id: string }[] = [];
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (!key || !key.startsWith('watchfy:mylist:')) continue;
      const parts = key.split(':');
      if (parts.length === 4) {
        entries.push({ type: parts[2], id: parts[3] });
      }
    }
    if (entries.length === 0) { loaded = true; return; }

    Promise.all(
      entries.map(e =>
        fetch(`/api/tmdb/media/${e.type}/${e.id}`)
          .then(r => r.ok ? r.json() : null)
          .catch(() => null)
      )
    ).then(results => {
      items = results.filter(Boolean);
      loaded = true;
    });
  }

  $effect(() => {
    loadFromStorage();
  });
</script>

{#if !loaded}
  <RowSkeleton count={5} />
{:else if items.length > 0}
  <MediaRow
    title="My List"
    items={items}
    showViewAll={false}
  />
{/if}
