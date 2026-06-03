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
{:else}
  <section class="mb-8 sm:mb-10">
    <div class="flex items-center gap-3 mb-4 px-4 md:px-6">
      <div class="w-1 h-6 rounded-full bg-brand-gradient-cta" aria-hidden="true"></div>
      <h2 class="text-lg md:text-2xl font-black text-ink tracking-tight">My List</h2>
    </div>
    <div class="flex items-center justify-center py-10 mx-4 md:mx-6 rounded-2xl border border-white/[0.04] bg-white/[0.01]">
      <div class="text-center">
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.25" stroke="currentColor" class="w-8 h-8 mx-auto text-ink-faint mb-3" aria-hidden="true">
          <path stroke-linecap="round" stroke-linejoin="round" d="M17.593 3.322c1.1.128 1.907 1.077 1.907 2.185V21L12 17.25 4.5 21V5.507c0-1.108.806-2.057 1.907-2.185a48.507 48.507 0 0 1 11.186 0Z" />
        </svg>
        <p class="text-xs font-bold text-ink-muted tracking-wider uppercase">Add movies to your list</p>
      </div>
    </div>
  </section>
{/if}
