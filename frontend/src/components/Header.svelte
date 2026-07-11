<script lang="ts">
  import { onMount } from 'svelte';
  import BrandLogo from './BrandLogo.svelte';
  import { getToken, getUser, logout as authLogout, onAuthChange } from '../lib/auth';

  let currentPath = $state('/');
  let searchQuery = $state('');
  let searchResults: any[] = $state([]);
  let searchLoading = $state(false);
  let searchAbort: AbortController | null = null;
  let searchInputEl: HTMLInputElement | undefined = $state();
  let mobileSearchOpen = $state(false);
  let userMenuOpen = $state(false);
  let isAuthenticated = $state(false);
  let userName = $state('');
  let userAvatar = $state<string | null>(null);

  let debounceTimer: ReturnType<typeof setTimeout>;

  function dispatchToggleSidebar() {
    window.dispatchEvent(new CustomEvent('stersh:toggle-sidebar'));
  }

  async function handleSearch() {
    const q = searchQuery.trim();
    if (!q) { searchResults = []; return; }
    if (searchAbort) searchAbort.abort();
    searchAbort = new AbortController();
    searchLoading = true;
    try {
      const res = await fetch(`/api/tmdb/search/multi?query=${encodeURIComponent(q)}&page=1`, { signal: searchAbort.signal });
      const data = await res.json();
      searchResults = (data?.results || []).filter((r: any) => r.backdrop_path || r.poster_path).slice(0, 8);
    } catch { searchResults = []; }
    searchLoading = false;
  }

  function onSearchInput() {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(handleSearch, 280);
  }

  function onSearchSubmit(e: Event) {
    e.preventDefault();
    const q = searchQuery.trim();
    if (!q) return;
    window.location.href = `/search?q=${encodeURIComponent(q)}`;
  }

  function openMobileSearch() {
    mobileSearchOpen = true;
    setTimeout(() => searchInputEl?.focus(), 50);
  }

  function closeMobileSearch() {
    mobileSearchOpen = false;
  }

  function clearSearch() {
    searchQuery = '';
    searchResults = [];
    searchInputEl?.focus();
  }

  function getResultHref(r: any) {
    const type = r.media_type === 'tv' ? 'tv' : 'movie';
    return `/${type}/${r.id}`;
  }

  function getResultTitle(r: any) {
    return r.title || r.name || 'Untitled';
  }

  function getResultMeta(r: any) {
    const parts: string[] = [];
    if (r.media_type === 'tv') parts.push('TV');
    const year = (r.release_date || r.first_air_date || '').slice(0, 4);
    if (year) parts.push(year);
    return parts.join(' · ');
  }

  function onDocClick(e: MouseEvent) {
    const target = e.target as HTMLElement;
    if (!target.closest('[data-user-menu]') && !target.closest('[data-user-button]')) {
      userMenuOpen = false;
    }
  }

  function signOut() {
    authLogout();
    isAuthenticated = false;
    userMenuOpen = false;
    window.location.href = '/';
  }

  function loadAuth() {
    try {
      const token = getToken();
      isAuthenticated = !!token;
      const user = getUser();
      if (user) {
        userName = user.username || 'You';
        userAvatar = null;
      }
    } catch { isAuthenticated = false; }
  }

  onMount(() => {
    currentPath = window.location.pathname;
    const sync = () => { currentPath = window.location.pathname; };

    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && mobileSearchOpen) closeMobileSearch();
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        if (window.innerWidth < 1024) openMobileSearch();
        else searchInputEl?.focus();
      }
      if (e.key === '/' && document.activeElement === document.body) {
        e.preventDefault();
        searchInputEl?.focus();
      }
    };

    window.addEventListener('popstate', sync);
    document.addEventListener('astro:page-load', sync);
    document.addEventListener('keydown', onKey);
    document.addEventListener('click', onDocClick);
    loadAuth();
    const unsub = onAuthChange((authed) => { isAuthenticated = authed; loadAuth(); });

    return () => {
      window.removeEventListener('popstate', sync);
      document.removeEventListener('astro:page-load', sync);
      document.removeEventListener('keydown', onKey);
      document.removeEventListener('click', onDocClick);
      unsub();
    };
  });
</script>

<header
  class="fixed top-0 left-0 right-0 z-nav h-14 bg-base border-b border-white/10"
  aria-label="Top navigation"
>
  <div class="flex items-center h-full pl-4 pr-4 lg:pr-6 gap-4">

    <!-- Left cluster -->
    <div class="flex items-center gap-1 flex-shrink-0">
      <button
        type="button"
        onclick={dispatchToggleSidebar}
        class="yt-icon-btn"
        aria-label="Toggle sidebar"
        title="Toggle sidebar"
      >
        <svg viewBox="0 0 24 24" class="w-6 h-6" fill="currentColor" aria-hidden="true">
          <path d="M3 6h18v2H3V6zm0 5h18v2H3v-2zm0 5h18v2H3v-2z" />
        </svg>
      </button>
      <a href="/home" class="flex items-center pl-2 pr-3 py-1 rounded-lg hover:bg-base-3 transition-colors duration-100" aria-label="Stersh home">
        <BrandLogo size="md" />
      </a>
    </div>

    <!-- Center cluster: search (desktop) -->
    <div class="hidden lg:flex flex-1 justify-center">
      <form
        onsubmit={onSearchSubmit}
        class="flex items-center w-full max-w-[640px]"
        role="search"
        autocomplete="off"
      >
        <div class="flex flex-1 h-10 border border-white/10 rounded-l-full rounded-r-none bg-base-1 focus-within:border-yt-blue transition-colors duration-100 overflow-hidden">
          <div class="flex items-center pl-4 pr-1 text-ink-secondary">
            <svg viewBox="0 0 24 24" class="w-5 h-5" fill="currentColor" aria-hidden="true">
              <path d="M10 4a6 6 0 1 0 3.815 10.65L18 18.835 19.415 17.42l-4.185-4.185A6 6 0 0 0 10 4zm0 2a4 4 0 1 1 0 8 4 4 0 0 1 0-8z" />
            </svg>
          </div>
          <input
            bind:this={searchInputEl}
            bind:value={searchQuery}
            oninput={onSearchInput}
            type="search"
            placeholder="Search movies, TV shows..."
            class="flex-1 bg-transparent border-0 outline-none text-ink text-base placeholder:text-ink-muted px-3"
            aria-label="Search"
          />
          {#if searchQuery}
            <button
              type="button"
              onclick={clearSearch}
              class="yt-icon-btn mr-1"
              aria-label="Clear search"
            >
              <svg viewBox="0 0 24 24" class="w-5 h-5" fill="currentColor" aria-hidden="true">
                <path d="M19 6.4L17.6 5 12 10.6 6.4 5 5 6.4 10.6 12 5 17.6 6.4 19 12 13.4 17.6 19 19 17.6 13.4 12 19 6.4z" />
              </svg>
            </button>
          {/if}
        </div>
        <button
          type="submit"
          class="h-10 w-16 flex items-center justify-center bg-base-3 border border-l-0 border-white/10 rounded-r-full hover:bg-base-4 transition-colors duration-100"
          aria-label="Search"
          title="Search"
        >
          <svg viewBox="0 0 24 24" class="w-5 h-5" fill="currentColor" aria-hidden="true">
            <path d="M10 4a6 6 0 1 0 3.815 10.65L18 18.835 19.415 17.42l-4.185-4.185A6 6 0 0 0 10 4zm0 2a4 4 0 1 1 0 8 4 4 0 0 1 0-8z" />
          </svg>
        </button>
        <button
          type="button"
          class="yt-icon-btn ml-2"
          aria-label="Search with voice"
          title="Search with voice"
        >
          <svg viewBox="0 0 24 24" class="w-6 h-6" fill="currentColor" aria-hidden="true">
            <path d="M12 14a3 3 0 0 0 3-3V5a3 3 0 0 0-6 0v6a3 3 0 0 0 3 3z" />
            <path d="M17 11a5 5 0 0 1-10 0H5a7 7 0 0 0 6 6.92V21h2v-3.08A7 7 0 0 0 19 11h-2z" />
          </svg>
        </button>
      </form>
    </div>

    <!-- Right cluster -->
    <div class="flex items-center gap-1 flex-shrink-0 ml-auto lg:ml-0">
      <button
        type="button"
        onclick={openMobileSearch}
        class="yt-icon-btn lg:hidden"
        aria-label="Search"
      >
        <svg viewBox="0 0 24 24" class="w-6 h-6" fill="currentColor" aria-hidden="true">
          <path d="M10 4a6 6 0 1 0 3.815 10.65L18 18.835 19.415 17.42l-4.185-4.185A6 6 0 0 0 10 4zm0 2a4 4 0 1 1 0 8 4 4 0 0 1 0-8z" />
        </svg>
      </button>

      {#if isAuthenticated}
        <a
          href="/mylist"
          class="yt-icon-btn"
          aria-label="My list"
          title="My list"
        >
          <svg viewBox="0 0 24 24" class="w-6 h-6" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
          </svg>
        </a>
      {:else}
        <a
          href="/signin"
          class="hidden sm:flex items-center gap-2 h-9 px-4 border border-yt-blue text-yt-blue rounded-full text-sm font-medium hover:bg-yt-blue/10 transition-colors duration-100"
        >
          <svg viewBox="0 0 24 24" class="w-5 h-5" fill="currentColor" aria-hidden="true">
            <path d="M11 7L9.6 8.4l2.6 2.6H2v2h10.2l-2.6 2.6L11 17l5-5-5-5zM21 3h-8v2h8v14h-8v2h8a2 2 0 0 0 2-2V5a2 2 0 0 0-2-2z" />
          </svg>
          Sign in
        </a>
      {/if}

      <div class="relative">
        <button
          data-user-button
          type="button"
          onclick={() => userMenuOpen = !userMenuOpen}
          class="block w-8 h-8 rounded-full overflow-hidden hover:ring-2 hover:ring-white transition-shadow"
          aria-label="Account menu"
          aria-expanded={userMenuOpen}
        >
          {#if isAuthenticated && userAvatar}
            <img src={userAvatar} alt={userName} class="w-full h-full object-cover" />
          {:else}
            <span class="w-full h-full flex items-center justify-center bg-yt-blue text-base text-base font-medium">
              <svg viewBox="0 0 24 24" class="w-8 h-8 rounded-full bg-yt-red p-1.5" fill="white" aria-hidden="true">
                <path d="M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zm0 2c-3.3 0-8 1.7-8 5v1h16v-1c0-3.3-4.7-5-8-5z" />
              </svg>
            </span>
          {/if}
        </button>
        {#if userMenuOpen}
          <div
            data-user-menu
            class="absolute right-0 top-full mt-2 w-72 bg-base-1 border border-white/10 rounded-xl shadow-2xl py-3 z-50"
          >
            <div class="px-4 pb-3 border-b border-white/10">
              {#if isAuthenticated}
                <p class="text-base text-ink">{userName}</p>
                <p class="text-sm text-ink-muted">@{userName.toLowerCase().replace(/\s+/g, '')}</p>
              {:else}
                <p class="text-base text-ink">You</p>
                <p class="text-sm text-ink-muted">Sign in to access your library</p>
                <div class="mt-3 flex flex-col gap-2">
                  <a href="/signin" class="flex items-center justify-center h-9 px-4 border border-yt-blue text-yt-blue rounded-full text-sm font-medium hover:bg-yt-blue/10">
                    Sign in
                  </a>
                  <a href="/signup" class="flex items-center justify-center h-9 px-4 bg-base-3 text-ink rounded-full text-sm font-medium hover:bg-base-4">
                    Create account
                  </a>
                </div>
              {/if}
            </div>
            <div class="py-1">
              {#if isAuthenticated}
                <a href="/profile" class="flex items-center gap-3 px-4 py-2 hover:bg-base-3">
                  <svg viewBox="0 0 24 24" class="w-5 h-5" fill="currentColor" aria-hidden="true">
                    <path d="M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zm0 2c-3.3 0-8 1.7-8 5v1h16v-1c0-3.3-4.7-5-8-5z" />
                  </svg>
                  <span>Your profile</span>
                </a>
                <a href="/mylist" class="flex items-center gap-3 px-4 py-2 hover:bg-base-3">
                  <svg viewBox="0 0 24 24" class="w-5 h-5" fill="currentColor" aria-hidden="true">
                    <path d="M5 3h14a1 1 0 0 1 1 1v16l-8-4-8 4V4a1 1 0 0 1 1-1z" />
                  </svg>
                  <span>My list</span>
                </a>
                <a href="/history" class="flex items-center gap-3 px-4 py-2 hover:bg-base-3">
                  <svg viewBox="0 0 24 24" class="w-5 h-5" fill="currentColor" aria-hidden="true">
                    <path d="M12 8v4l3 3 .7-.7-2.7-2.7V8H12zm0-6a10 10 0 1 0 10 10h-2a8 8 0 1 1-8-8V2z" />
                  </svg>
                  <span>History</span>
                </a>
              {:else}
                <a href="/signin" class="flex items-center gap-3 px-4 py-2 hover:bg-base-3">
                  <span>Help</span>
                </a>
                <a href="/signin" class="flex items-center gap-3 px-4 py-2 hover:bg-base-3">
                  <span>Send feedback</span>
                </a>
              {/if}
            </div>
            {#if isAuthenticated}
              <div class="border-t border-white/10 py-1">
                <button
                  type="button"
                  onclick={signOut}
                  class="w-full text-left flex items-center gap-3 px-4 py-2 hover:bg-base-3"
                >
                  <svg viewBox="0 0 24 24" class="w-5 h-5" fill="currentColor" aria-hidden="true">
                    <path d="M17 8l-1.4 1.4L17.2 11H10v2h7.2l-1.6 1.6L17 16l4-4-4-4zM5 3h8v2H7v14h6v2H5V3z" />
                  </svg>
                  <span>Sign out</span>
                </button>
              </div>
            {/if}
          </div>
        {/if}
      </div>
    </div>
  </div>

  <!-- Search suggestions (desktop) -->
  {#if searchResults.length > 0 && searchQuery && !mobileSearchOpen}
    <div class="hidden lg:block absolute left-0 right-0 top-14 pointer-events-none">
      <div class="max-w-[640px] mx-auto pointer-events-auto bg-base-1 border border-white/10 rounded-2xl shadow-2xl overflow-hidden">
        <ul>
          {#each searchResults as r}
            <li>
              <a
                href={getResultHref(r)}
                class="flex items-center gap-4 px-4 py-2 hover:bg-base-3"
              >
                <div class="w-16 h-9 bg-base-3 rounded overflow-hidden flex-shrink-0">
                  {#if r.backdrop_path}
                    <img src={`https://image.tmdb.org/t/p/w185${r.backdrop_path}`} alt="" class="w-full h-full object-cover" loading="lazy" />
                  {:else if r.poster_path}
                    <img src={`https://image.tmdb.org/t/p/w92${r.poster_path}`} alt="" class="w-full h-full object-cover" loading="lazy" />
                  {/if}
                </div>
                <div class="flex-1 min-w-0">
                  <p class="text-sm text-ink truncate">{getResultTitle(r)}</p>
                  <p class="text-xs text-ink-muted truncate">{getResultMeta(r)}</p>
                </div>
                <svg viewBox="0 0 24 24" class="w-4 h-4 text-ink-muted flex-shrink-0" fill="currentColor" aria-hidden="true">
                  <path d="M9 6l6 6-6 6" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" />
                </svg>
              </a>
            </li>
          {/each}
        </ul>
        <a
          href={`/search?q=${encodeURIComponent(searchQuery)}`}
          class="flex items-center gap-3 px-4 py-3 border-t border-white/10 hover:bg-base-3"
        >
          <svg viewBox="0 0 24 24" class="w-5 h-5" fill="currentColor" aria-hidden="true">
            <path d="M10 4a6 6 0 1 0 3.815 10.65L18 18.835 19.415 17.42l-4.185-4.185A6 6 0 0 0 10 4zm0 2a4 4 0 1 1 0 8 4 4 0 0 1 0-8z" />
          </svg>
          <span class="text-sm">Search for "{searchQuery}"</span>
        </a>
      </div>
    </div>
  {/if}
</header>

<!-- Mobile full-screen search overlay -->
{#if mobileSearchOpen}
  <div class="fixed inset-0 z-[100] bg-base lg:hidden" role="dialog" aria-label="Search">
    <div class="flex items-center h-14 px-4 gap-2 border-b border-white/10">
      <button
        type="button"
        onclick={closeMobileSearch}
        class="yt-icon-btn"
        aria-label="Close search"
      >
        <svg viewBox="0 0 24 24" class="w-6 h-6" fill="currentColor" aria-hidden="true">
          <path d="M19 6.4L17.6 5 12 10.6 6.4 5 5 6.4 10.6 12 5 17.6 6.4 19 12 13.4 17.6 19 19 17.6 13.4 12 19 6.4z" />
        </svg>
      </button>
      <form onsubmit={onSearchSubmit} class="flex-1">
        <input
          bind:this={searchInputEl}
          bind:value={searchQuery}
          oninput={onSearchInput}
          type="search"
          placeholder="Search movies, TV shows..."
          class="w-full h-10 bg-base-1 border border-white/10 rounded-full px-4 text-ink placeholder:text-ink-muted focus:border-yt-blue focus:outline-none"
          aria-label="Search"
        />
      </form>
    </div>
    <div class="overflow-y-auto h-[calc(100vh-3.5rem)]">
      {#if searchLoading}
        <div class="px-4 py-8 flex items-center justify-center gap-3 text-ink-muted">
          <div class="w-5 h-5 border-2 border-white/20 border-t-yt-red rounded-full animate-spin"></div>
          <span>Searching...</span>
        </div>
      {:else if searchResults.length > 0}
        <ul>
          {#each searchResults as r}
            <li>
              <a
                href={getResultHref(r)}
                onclick={closeMobileSearch}
                class="flex items-center gap-4 px-4 py-3 hover:bg-base-3"
              >
                <div class="w-20 h-12 bg-base-3 rounded overflow-hidden flex-shrink-0">
                  {#if r.backdrop_path}
                    <img src={`https://image.tmdb.org/t/p/w185${r.backdrop_path}`} alt="" class="w-full h-full object-cover" loading="lazy" />
                  {:else if r.poster_path}
                    <img src={`https://image.tmdb.org/t/p/w92${r.poster_path}`} alt="" class="w-full h-full object-cover" loading="lazy" />
                  {/if}
                </div>
                <div class="flex-1 min-w-0">
                  <p class="text-base text-ink truncate">{getResultTitle(r)}</p>
                  <p class="text-sm text-ink-muted truncate">{getResultMeta(r)}</p>
                </div>
              </a>
            </li>
          {/each}
        </ul>
      {:else if searchQuery}
        <div class="px-4 py-12 text-center text-ink-muted">
          No results for "{searchQuery}"
        </div>
      {:else}
        <div class="px-4 py-6 text-sm text-ink-muted">Start typing to search</div>
      {/if}
    </div>
  </div>
{/if}
