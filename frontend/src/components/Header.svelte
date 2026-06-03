<script lang="ts">
  import { onMount } from 'svelte';
  import BrandLogo from './BrandLogo.svelte';

  let currentPath = $state('/');
  let scrolled = $state(false);
  let searchOpen = $state(false);
  let searchQuery = $state('');
  let searchResults: any[] = $state([]);
  let searchLoading = $state(false);
  let searchAbort: AbortController | null = null;

  const navItems = [
    { href: '/home', label: 'Home' },
    { href: '/movies', label: 'Movies' },
    { href: '/tv', label: 'TV Shows' },
  ];

  function checkActiveStatus(href: string, current: string): boolean {
    if (href === '/') return current === '/';
    return current.startsWith(href);
  }

  let debounceTimer: ReturnType<typeof setTimeout>;

  async function handleSearch() {
    const q = searchQuery.trim();
    if (!q) { searchResults = []; return; }

    if (searchAbort) searchAbort.abort();
    searchAbort = new AbortController();

    searchLoading = true;
    try {
      const res = await fetch(`/api/tmdb/search/multi?query=${encodeURIComponent(q)}&page=1`, { signal: searchAbort.signal });
      const data = await res.json();
      searchResults = (data?.results || []).filter((r: any) => r.backdrop_path || r.poster_path).slice(0, 6);
    } catch { searchResults = []; }
    searchLoading = false;
  }

  function onSearchInput() {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(handleSearch, 280);
  }

  function openSearch() {
    searchOpen = true;
    setTimeout(() => document.getElementById('header-search-input')?.focus(), 80);
  }

  function closeSearch() {
    searchOpen = false;
    searchQuery = '';
    searchResults = [];
    searchLoading = false;
  }

  function getResultHref(r: any) {
    const type = r.media_type === 'tv' ? 'tv' : 'movie';
    return `/${type}/${r.id}`;
  }

  function getResultTitle(r: any) {
    return r.title || r.name || 'Untitled';
  }

  onMount(() => {
    currentPath = window.location.pathname;

    const sync = () => { currentPath = window.location.pathname; };
    const onScroll = () => { scrolled = window.scrollY > 8; };

    window.addEventListener('popstate', sync);
    document.addEventListener('astro:page-load', sync);
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();

    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && searchOpen) closeSearch();
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') { e.preventDefault(); openSearch(); }
    };
    document.addEventListener('keydown', onKey);

    return () => {
      window.removeEventListener('popstate', sync);
      document.removeEventListener('astro:page-load', sync);
      window.removeEventListener('scroll', onScroll);
      document.removeEventListener('keydown', onKey);
    };
  });
</script>

{#if searchOpen}
  <div
    class="fixed inset-0 z-[90] bg-black/70 backdrop-blur-sm transition-opacity duration-300"
    onclick={closeSearch}
    onkeydown={(e) => e.key === 'Escape' && closeSearch()}
    role="presentation"
  ></div>
{/if}

<header
  class="fixed top-0 left-0 right-0 z-nav transition-all duration-500 ease-exo-out
    {scrolled ? 'glass-strong shadow-2' : 'bg-gradient-to-b from-black/60 to-transparent'}
    hidden lg:block"
  aria-label="Site header"
>
  <div class="max-w-content mx-auto h-16 px-6 xl:px-10 flex items-center justify-between gap-8">

    <a
      href="/"
      class="flex items-center gap-2 transition-all duration-500 ease-exo-out hover:scale-[1.02] active:scale-[0.98] focus-visible:outline-none rounded-md group"
      aria-label="Watchfy home"
    >
      <BrandLogo size={scrolled ? 'sm' : 'md'} tone="gradient" />
    </a>

    <nav aria-label="Primary navigation" class="flex-1">
      <ul class="flex items-center justify-center gap-1">
        {#each navItems as item}
          {@const active = checkActiveStatus(item.href, currentPath)}
          <li>
            <a
              href={item.href}
              aria-current={active ? 'page' : undefined}
              class="relative inline-flex items-center px-4 py-2 rounded-lg text-sm font-semibold transition-all duration-200 ease-exo-out
                {active
                  ? 'text-ink bg-white/[0.08]'
                  : 'text-ink-muted hover:text-ink hover:bg-white/[0.03]'}"
            >
              {item.label}
              {#if active}
                <span
                  class="absolute inset-x-3 -bottom-px h-0.5 rounded-full bg-brand-gradient-cta"
                  aria-hidden="true"
                ></span>
              {/if}
            </a>
          </li>
        {/each}
      </ul>
    </nav>

    <div class="flex items-center gap-2">
      <button
        type="button"
        onclick={openSearch}
        class="inline-flex items-center gap-2 px-3.5 py-2 rounded-xl text-ink-muted hover:text-ink hover:bg-white/[0.06] transition-all duration-200 ease-exo-out text-sm"
        aria-label="Search (Ctrl+K)"
      >
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-4 h-4">
          <path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.604 10.604Z" />
        </svg>
        <span class="text-ink-subtle text-xs hidden xl:inline">Search</span>
        <kbd class="hidden lg:inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded border border-white/[0.08] bg-white/[0.04] text-[10px] text-ink-subtle font-mono">⌘K</kbd>
      </button>

      <a
        href="/search"
        class="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-brand-gradient-cta text-white text-sm font-bold shadow-glow-red hover:brightness-110 hover:scale-[1.02] active:scale-[0.98] transition-all duration-200 ease-exo-out"
      >
        Sign In
      </a>
    </div>
  </div>
</header>

{#if searchOpen}
  <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
  <div class="fixed top-0 left-0 right-0 z-[100] pt-[12vh] px-4" role="dialog" aria-label="Search overlay" tabindex={-1} onclick={() => closeSearch()}>
    <div
      class="mx-auto max-w-2xl glass-strong rounded-2xl shadow-4 overflow-hidden transform transition-all duration-300 ease-exo-out"
      style="animation: watchfy-rise 300ms var(--ease-exo-out) both;"
    >
      <div class="flex items-center gap-3 px-5 py-4 border-b border-white/[0.06]">
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-5 h-5 text-ink-subtle flex-shrink-0">
          <path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.604 10.604Z" />
        </svg>
        <input
          id="header-search-input"
          type="search"
          placeholder="Search movies, TV shows..."
          bind:value={searchQuery}
          oninput={onSearchInput}
          class="w-full bg-transparent border-none outline-none text-ink text-base placeholder:text-ink-subtle"
          autocomplete="off"
        />
        {#if searchQuery}
          <button
            type="button"
            onclick={() => { searchQuery = ''; searchResults = []; }}
            class="text-ink-subtle hover:text-ink-muted transition-colors"
            aria-label="Clear search"
          >
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-4 h-4">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
            </svg>
          </button>
        {/if}
        <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
        <button type="button" tabindex={-1} class="flex-shrink-0 inline-flex items-center px-1.5 py-0.5 rounded border border-white/[0.08] bg-white/[0.04] text-[10px] text-ink-subtle font-mono cursor-pointer" onclick={closeSearch}>ESC</button>
      </div>

      {#if searchLoading}
        <div class="px-5 py-6 flex items-center justify-center gap-3 text-ink-subtle text-sm">
          <svg class="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2" opacity="0.25" />
            <path d="M4 12a8 8 0 018-8" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
          </svg>
          Searching...
        </div>
      {:else if searchResults.length > 0}
        <ul class="max-h-[50vh] overflow-y-auto py-2">
          {#each searchResults as r}
            <li>
              <a
                href={getResultHref(r)}
                onclick={closeSearch}
                class="flex items-center gap-3.5 px-5 py-3 hover:bg-white/[0.05] transition-colors duration-150 group"
              >
                {#if r.poster_path}
                  <img
                    src={`https://image.tmdb.org/t/p/w92${r.poster_path}`}
                    alt=""
                    class="w-10 h-[60px] rounded-lg object-cover flex-shrink-0 shadow-2 border border-white/[0.06]"
                    loading="lazy"
                  />
                {:else}
                  <div class="w-10 h-[60px] rounded-lg bg-surface-2 flex-shrink-0 flex items-center justify-center">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-5 h-5 text-ink-subtle">
                      <path stroke-linecap="round" stroke-linejoin="round" d="m2.25 15.75 5.159-5.159a2.25 2.25 0 0 1 3.182 0l5.159 5.159m-1.5-1.5 1.409-1.409a2.25 2.25 0 0 1 3.182 0l2.909 2.909M3.75 21h16.5A2.25 2.25 0 0 0 22.5 18.75V5.25A2.25 2.25 0 0 0 20.25 3H3.75A2.25 2.25 0 0 0 1.5 5.25v13.5A2.25 2.25 0 0 0 3.75 21Z" />
                    </svg>
                  </div>
                {/if}
                <div class="flex-1 min-w-0">
                  <p class="text-sm font-semibold text-ink group-hover:text-white truncate">{getResultTitle(r)}</p>
                  <div class="flex items-center gap-2 mt-0.5">
                    <span class="text-[10px] uppercase tracking-wider font-bold text-ink-subtle group-hover:text-brand-red/80 transition-colors">{r.media_type === 'tv' ? 'TV Series' : 'Movie'}</span>
                    {#if r.release_date || r.first_air_date}
                      <span class="text-[10px] text-ink-subtle">{(r.release_date || r.first_air_date || '').slice(0, 4)}</span>
                    {/if}
                    {#if r.vote_average > 0}
                      <span class="text-[10px] text-accent-warm font-bold">★ {(r.vote_average).toFixed(1)}</span>
                    {/if}
                  </div>
                </div>
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-4 h-4 text-ink-subtle group-hover:text-ink-muted transition-colors flex-shrink-0">
                  <path stroke-linecap="round" stroke-linejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" />
                </svg>
              </a>
            </li>
          {/each}
        </ul>
        <div class="px-5 py-2.5 border-t border-white/[0.04] text-center">
          <a href={`/search?q=${encodeURIComponent(searchQuery)}`} onclick={closeSearch} class="text-xs font-bold tracking-wider uppercase text-ink-subtle hover:text-brand-red transition-colors">
            View all results →
          </a>
        </div>
      {:else if searchQuery && !searchLoading}
        <div class="px-5 py-8 text-center text-ink-subtle text-sm">
          No results for "<span class="text-ink">{searchQuery}</span>"
        </div>
      {/if}
    </div>
  </div>
{/if}