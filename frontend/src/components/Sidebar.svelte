<script lang="ts">
  import { onMount } from 'svelte';
  import { getToken, getUser, onAuthChange } from '../lib/auth';

  let currentPath = $state('/');
  let collapsed = $state(false);
  let isAuthenticated = $state(false);
  let userName = $state('User');
  let userAvatar = $state<string | null>(null);
  let subscriptions: { name: string; avatar?: string | null }[] = $state([]);

  function checkActive(href: string): boolean {
    if (href === '/') return currentPath === '/';
    return currentPath === href || currentPath.startsWith(href + '/');
  }

  onMount(() => {
    const saved = localStorage.getItem('watchfy_sidebar_collapsed');
    if (saved === '1') collapsed = true;

    const update = () => {
      currentPath = window.location.pathname;
      // On watch page or when window narrow enough, auto-collapse
      if (currentPath.startsWith('/watch/')) collapsed = true;
    };
    update();

    const onPop = () => update();
    const onAstro = () => update();
    const onToggle = () => {
      collapsed = !collapsed;
      try { localStorage.setItem('watchfy_sidebar_collapsed', collapsed ? '1' : '0'); } catch {}
    };
    const onResize = () => { /* keep current state; Layout switches to mobile bar at lg breakpoint */ };

    try {
      const token = getToken();
      isAuthenticated = !!token;
      if (isAuthenticated) {
        const user = getUser();
        if (user) {
          userName = user.username || 'User';
          userAvatar = null;
        }
      }
    } catch {}

    window.addEventListener('popstate', onPop);
    document.addEventListener('astro:page-load', onAstro);
    window.addEventListener('watchfy:toggle-sidebar', onToggle as EventListener);
    window.addEventListener('resize', onResize);
    const unsub = onAuthChange((authed) => { isAuthenticated = authed; });
    return () => {
      window.removeEventListener('popstate', onPop);
      document.removeEventListener('astro:page-load', onAstro);
      window.removeEventListener('watchfy:toggle-sidebar', onToggle as EventListener);
      window.removeEventListener('resize', onResize);
      unsub();
    };
  });

  const mainItems = [
    { href: '/', label: 'Home', icon: 'M12 4l9 8h-3v8h-4v-6h-4v6H6v-8H3l9-8z' },
    { href: '/movies', label: 'Movies', icon: 'M4 4h16v16H4V4zm2 2v12h12V6H6zm2 2h2v2H8V8zm4 0h4v2h-4V8zM8 12h2v2H8v-2zm4 0h4v2h-4v-2z' },
    { href: '/tv', label: 'TV Shows', icon: 'M3 5h18v12H3V5zm2 2v8h14V7H5zm5 10v2h4v-2h-4z' },
  ];

  const youItems = [
    { href: '/history', label: 'History', icon: 'M12 8v4l3 3 .7-.7-2.7-2.7V8H12zm0-6a10 10 0 1 0 10 10h-2a8 8 0 1 1-8-8V2z' },
    { href: '/mylist', label: 'My List', icon: 'M5 3h14a1 1 0 0 1 1 1v16l-8-4-8 4V4a1 1 0 0 1 1-1z' },
    { href: '/profile', label: 'Profile', icon: 'M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zm0 2c-3.3 0-8 1.7-8 5v1h16v-1c0-3.3-4.7-5-8-5z' },
  ];

  // TMDB movie genre IDs — these hit the /discover?with_genres=ID endpoint
  // so clicking takes the user to a real genre-filtered list (not a text search).
  const exploreItems = [
    { href: '/trending', label: 'Trending', icon: 'M13 3l-1 7h6l-7 11 1-7H6l7-11z' },
    { href: '/genre/28', label: 'Action', icon: 'M3 3l8 18 2-8 8-2L3 3z' },
    { href: '/genre/35', label: 'Comedy', icon: 'M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2zm-3 8a1.5 1.5 0 1 1-1.5 1.5A1.5 1.5 0 0 1 9 10zm6 0a1.5 1.5 0 1 1-1.5 1.5A1.5 1.5 0 0 1 15 10zm-3 7a5 5 0 0 1-4.6-3h9.2A5 5 0 0 1 12 17z' },
    { href: '/genre/18', label: 'Drama', icon: 'M5 4h14a1 1 0 0 1 1 1v14a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1zm2 2v2h10V6H7zm0 4v2h10v-2H7zm0 4v2h7v-2H7z' },
    { href: '/genre/27', label: 'Horror', icon: 'M12 2a8 8 0 0 0-8 8c0 3 1.6 5.6 4 7v3h8v-3c2.4-1.4 4-4 4-7a8 8 0 0 0-8-8z' },
    { href: '/genre/878', label: 'Sci-Fi', icon: 'M5 2h14a1 1 0 0 1 1 1v18a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V3a1 1 0 0 1 1-1zm7 4a5 5 0 1 0 5 5 5 5 0 0 0-5-5z' },
  ];
</script>

<aside
  class="hidden lg:flex sticky top-14 self-start flex-shrink-0 h-[calc(100vh-3.5rem)] overflow-y-auto no-scrollbar bg-base transition-[width] duration-200"
  style="width: {collapsed ? 'var(--sidebar-mini)' : 'var(--sidebar-width)'}"
  aria-label="Sidebar"
>
  <div class="flex flex-col w-full py-3 {collapsed ? 'px-2' : 'px-3'} gap-1">
    {#each mainItems as item}
      <a
        href={item.href}
        class="yt-nav-item {collapsed ? 'justify-center px-0 gap-0' : ''}"
        aria-current={checkActive(item.href) ? 'page' : undefined}
        title={collapsed ? item.label : undefined}
      >
        <svg viewBox="0 0 24 24" class="w-6 h-6 flex-shrink-0" fill="currentColor" aria-hidden="true">
          <path d={item.icon} />
        </svg>
        {#if !collapsed}<span class="truncate">{item.label}</span>{/if}
      </a>
    {/each}

    {#if !collapsed}
      <div class="my-2 border-t border-white/10"></div>
      <h3 class="px-3 text-sm font-semibold text-ink-secondary mb-1">You</h3>
      {#if isAuthenticated}
        {#each youItems as item}
          <a
            href={item.href}
            class="yt-nav-item"
            aria-current={checkActive(item.href) ? 'page' : undefined}
          >
            <svg viewBox="0 0 24 24" class="w-6 h-6 flex-shrink-0" fill="currentColor" aria-hidden="true">
              <path d={item.icon} />
            </svg>
            <span class="truncate">{item.label}</span>
          </a>
        {/each}
      {:else}
        <a href="/signin" class="yt-nav-item">
          <svg viewBox="0 0 24 24" class="w-6 h-6 flex-shrink-0" fill="currentColor" aria-hidden="true">
            <path d="M11 7L9.6 8.4l2.6 2.6H2v2h10.2l-2.6 2.6L11 17l5-5-5-5zM21 3h-8v2h8v14h-8v2h8a2 2 0 0 0 2-2V5a2 2 0 0 0-2-2z" />
          </svg>
          <span class="truncate">Sign in</span>
        </a>
      {/if}

      <div class="my-2 border-t border-white/10"></div>
      <h3 class="px-3 text-sm font-semibold text-ink-secondary mb-1">Explore</h3>
      {#each exploreItems as item}
        <a
          href={item.href}
          class="yt-nav-item"
          aria-current={checkActive(item.href) ? 'page' : undefined}
        >
          <svg viewBox="0 0 24 24" class="w-6 h-6 flex-shrink-0" fill="currentColor" aria-hidden="true">
            <path d={item.icon} />
          </svg>
          <span class="truncate">{item.label}</span>
        </a>
      {/each}

      <div class="my-2 border-t border-white/10"></div>
      <div class="px-3 text-[11px] text-ink-muted leading-snug">
        © {new Date().getFullYear()} Watchfy · A movie & TV streaming service
      </div>
    {:else}
      <div class="my-2 border-t border-white/10"></div>
      <a href="/mylist" class="yt-nav-item justify-center px-0 gap-0" title="My List">
        <svg viewBox="0 0 24 24" class="w-6 h-6 flex-shrink-0" fill="currentColor" aria-hidden="true">
          <path d="M5 3h14a1 1 0 0 1 1 1v16l-8-4-8 4V4a1 1 0 0 1 1-1z" />
        </svg>
      </a>
      <a href="/history" class="yt-nav-item justify-center px-0 gap-0" title="History">
        <svg viewBox="0 0 24 24" class="w-6 h-6 flex-shrink-0" fill="currentColor" aria-hidden="true">
          <path d="M12 8v4l3 3 .7-.7-2.7-2.7V8H12zm0-6a10 10 0 1 0 10 10h-2a8 8 0 1 1-8-8V2z" />
        </svg>
      </a>
    {/if}
  </div>
</aside>
