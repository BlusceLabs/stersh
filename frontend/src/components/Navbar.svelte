<script lang="ts">
  import { onMount } from 'svelte';

  let currentPath = $state('/');
  let pressing = $state('');
  let mounted = $state(false);
  let isAuthenticated = $state(false);
  let profileMenuOpen = $state(false);
  let userAvatar = $state<string | null>(null);
  let userName = $state('User');

  onMount(() => {
    currentPath = window.location.pathname;
    mounted = true;
    sync = () => { currentPath = window.location.pathname; };
    window.addEventListener('popstate', sync);
    document.addEventListener('astro:page-load', sync);
    loadAuth();
    document.addEventListener('click', handleClickOutside);
    return () => {
      window.removeEventListener('popstate', sync);
      document.removeEventListener('astro:page-load', sync);
      document.removeEventListener('click', handleClickOutside);
    };
  });

  let sync: () => void;

  function loadAuth() {
    try {
      const token = localStorage.getItem('watchfy_token');
      isAuthenticated = !!token;
      const userRaw = localStorage.getItem('watchfy_user');
      if (userRaw) {
        const user = JSON.parse(userRaw);
        userName = user.username || user.name || 'User';
        userAvatar = user.avatar || user.profile_path
          ? `https://image.tmdb.org/t/p/w185${user.profile_path}`
          : null;
      }
    } catch {
      isAuthenticated = false;
    }
  }

  function handleClickOutside(event: MouseEvent) {
    const target = event.target as HTMLElement;
    if (!target.closest('[data-profile-menu]')) {
      profileMenuOpen = false;
    }
  }

  function signOut() {
    localStorage.removeItem('watchfy_token');
    localStorage.removeItem('watchfy_user');
    isAuthenticated = false;
    profileMenuOpen = false;
    window.location.href = '/';
  }

  const navItems = [
    {
      href: '/home',
      label: 'Home',
      icon: 'M2.25 12l8.954-8.955a1.126 1.126 0 011.591 0L21.75 12M4.5 9.75v10.125c0 .621.504 1.125 1.125 1.125H9.75v-4.875c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21h4.125c.621 0 1.125-.504 1.125-1.125V9.75M8.25 21h8.25',
    },
    {
      href: '/movies',
      label: 'Movies',
      icon: 'M16.5 6v12m-9-12v12M3 7.5h18M3 12h18M3 16.5h18M4.5 19.5h15a2.25 2.25 0 0 0 2.25-2.25V6.75A2.25 2.25 0 0 0 19.5 4.5h-15a2.25 2.25 0 0 0-2.25 2.25v10.5A2.25 2.25 0 0 0 4.5 19.5Z',
    },
    {
      href: '/tv',
      label: 'TV',
      icon: 'M6 20.25h12m-12-3h12m-12-3h12m-12-3h12m-6-9v6m-3-3h6M3.75 20.25h16.5c.621 0 1.125-.504 1.125-1.125V4.125c0-.621-.504-1.125-1.125-1.125H3.75c-.621 0-1.125.504-1.125 1.125v15c0 .621.504 1.125 1.125 1.125Z',
    },
    {
      href: '/search',
      label: 'Search',
      icon: 'm21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.604 10.604Z',
    },
  ];

  function checkActiveStatus(href: string, current: string): boolean {
    if (href === '/') return current === '/';
    return current.startsWith(href);
  }

  function getInitials(name: string): string {
    return name
      .split(' ')
      .map(part => part[0])
      .slice(0, 2)
      .join('')
      .toUpperCase();
  }
</script>

<nav
  class="fixed bottom-0 left-0 right-0 z-nav pointer-events-none"
  aria-label="Primary navigation"
>
  <!-- Soft ambient glow beneath the dock -->
  <div class="absolute bottom-2 left-1/2 -translate-x-1/2 w-[80%] h-10 rounded-full blur-3xl pointer-events-none" aria-hidden="true" style="background: radial-gradient(ellipse at center, rgba(239, 68, 68, 0.18) 0%, rgba(168, 85, 247, 0.08) 50%, transparent 80%);"></div>

  <div class="px-3 sm:px-4 pb-[calc(0.5rem+env(safe-area-inset-bottom,0px))] sm:pb-[calc(0.75rem+env(safe-area-inset-bottom,0px))]">
    <div
      class="group/dock relative mx-auto max-w-md rounded-[1.5rem] flex items-center justify-around h-[68px] px-1.5
        pointer-events-auto
        transition-all duration-700 ease-exo-out
        {mounted ? 'translate-y-0 opacity-100' : 'translate-y-12 opacity-0'}"
    >
      <!-- ===== LIQUID GLASS LAYERS ===== -->
      <div class="absolute inset-0 rounded-[1.5rem] pointer-events-none" style="background: linear-gradient(180deg, rgba(24, 24, 27, 0.55) 0%, rgba(9, 9, 11, 0.72) 100%); backdrop-filter: blur(40px) saturate(180%); -webkit-backdrop-filter: blur(40px) saturate(180%);" aria-hidden="true"></div>
      <div class="absolute inset-0 rounded-[1.5rem] pointer-events-none overflow-hidden" aria-hidden="true">
        <div class="absolute -top-1/2 left-1/4 right-1/4 h-full opacity-60" style="background: radial-gradient(ellipse at center, rgba(255, 255, 255, 0.12) 0%, transparent 70%);"></div>
      </div>
      <div class="absolute inset-0 rounded-[1.5rem] pointer-events-none overflow-hidden" aria-hidden="true">
        <div class="absolute -inset-1 opacity-30" style="background: linear-gradient(115deg, transparent 30%, rgba(255, 255, 255, 0.06) 45%, rgba(239, 68, 68, 0.04) 55%, transparent 70%); transform: translateX(-100%); animation: dock-shimmer 8s ease-in-out infinite;"></div>
      </div>
      <div class="absolute inset-0 rounded-[1.5rem] pointer-events-none" style="border: 1px solid rgba(255, 255, 255, 0.08); box-shadow: 0 -8px 32px -8px rgba(0, 0, 0, 0.6), 0 0 0 0.5px rgba(255, 255, 255, 0.04), inset 0 1px 0 rgba(255, 255, 255, 0.06), inset 0 -1px 0 rgba(0, 0, 0, 0.2);" aria-hidden="true"></div>

      <!-- ===== NAV ITEMS ===== -->
      {#each navItems as item, i (item.href)}
        {@const active = checkActiveStatus(item.href, currentPath)}
        <a
          href={item.href}
          aria-current={active ? 'page' : undefined}
          aria-label={item.label}
          class="relative flex flex-col items-center justify-center gap-1 px-3.5 py-2 rounded-2xl transition-all duration-300 ease-exo-out min-w-[56px] select-none group
            {active
              ? 'text-ink'
              : 'text-ink-subtle'}"
          onpointerdown={() => pressing = item.href}
          onpointerup={() => pressing = ''}
          onpointerleave={() => pressing = ''}
        >
          {#if active}
            <span
              class="absolute inset-0 rounded-2xl pointer-events-none"
              style="background: linear-gradient(180deg, rgba(239, 68, 68, 0.22) 0%, rgba(236, 72, 153, 0.12) 100%); backdrop-filter: blur(12px) saturate(200%); -webkit-backdrop-filter: blur(12px) saturate(200%); box-shadow: 0 0 24px -4px rgba(239, 68, 68, 0.35), inset 0 1px 0 rgba(255, 255, 255, 0.12), inset 0 -1px 0 rgba(0, 0, 0, 0.1); border: 1px solid rgba(239, 68, 68, 0.2);"
              aria-hidden="true"
            ></span>
            <span class="absolute -top-1 left-1/2 -translate-x-1/2 w-8 h-[2px] rounded-full bg-brand-gradient-cta pointer-events-none" style="box-shadow: 0 0 12px rgba(239, 68, 68, 0.6);" aria-hidden="true"></span>
          {/if}

          <div class="relative transition-all duration-300 ease-exo-out {active ? 'scale-100' : 'group-hover:scale-110 group-active:scale-90'}">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              stroke-width={active ? 2.25 : 1.75}
              stroke="currentColor"
              class="w-[22px] h-[22px] transition-all duration-300 ease-exo-out {active ? 'text-white' : 'group-hover:text-ink-muted'}"
              style={active ? 'filter: drop-shadow(0 0 8px rgba(239, 68, 68, 0.4));' : ''}
              aria-hidden="true"
            >
              <path stroke-linecap="round" stroke-linejoin="round" d={item.icon} />
            </svg>
          </div>

          <span class="text-[9.5px] font-bold tracking-wider uppercase leading-none whitespace-nowrap transition-all duration-300 ease-exo-out {active ? 'opacity-100 text-ink' : 'opacity-50 group-hover:opacity-80 group-hover:text-ink-muted'}">
            {item.label}
          </span>

          {#if pressing === item.href && !active}
            <span class="absolute inset-0 rounded-2xl pointer-events-none" style="background: radial-gradient(circle at center, rgba(255, 255, 255, 0.08) 0%, transparent 70%);" aria-hidden="true"></span>
          {/if}
        </a>
      {/each}

      <!-- ===== PROFILE / AUTH ===== -->
      <div data-profile-menu class="relative flex items-center">
        {#if isAuthenticated}
          <!-- Signed in: Avatar button -->
          <button
            type="button"
            onclick={() => profileMenuOpen = !profileMenuOpen}
            class="relative w-10 h-10 rounded-full overflow-hidden transition-all duration-300 ease-exo-out hover:scale-110 active:scale-95 group/avatar"
            aria-label="Open profile menu"
            aria-expanded={profileMenuOpen}
            style="box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.08), 0 0 16px -4px rgba(239, 68, 68, 0.3);"
          >
            {#if userAvatar}
              <img src={userAvatar} alt={userName} class="w-full h-full object-cover" />
            {:else}
              <div class="w-full h-full flex items-center justify-center text-[11px] font-extrabold text-white" style="background: linear-gradient(135deg, #ef4444 0%, #ec4899 50%, #a855f7 100%);">
                {getInitials(userName)}
              </div>
            {/if}
          </button>

          <!-- Profile dropdown -->
          {#if profileMenuOpen}
            <div
              class="absolute bottom-full right-0 mb-3 w-56 rounded-2xl pointer-events-auto origin-bottom-right"
              style="
                background: linear-gradient(180deg, rgba(24, 24, 27, 0.85) 0%, rgba(9, 9, 11, 0.95) 100%);
                backdrop-filter: blur(40px) saturate(200%);
                -webkit-backdrop-filter: blur(40px) saturate(200%);
                border: 1px solid rgba(255, 255, 255, 0.08);
                box-shadow: 0 -8px 32px -4px rgba(0, 0, 0, 0.6), inset 0 1px 0 rgba(255, 255, 255, 0.06);
                animation: menu-rise 300ms var(--ease-exo-out) both;
              "
            >
              <div class="px-4 py-3 border-b border-white/[0.06]">
                <p class="text-sm font-bold text-ink truncate">{userName}</p>
                <p class="text-[10px] text-ink-subtle uppercase tracking-wider font-bold mt-0.5">Signed in</p>
              </div>
              <ul class="py-1.5">
                <li>
                  <a href="/profile" class="flex items-center gap-3 px-4 py-2.5 text-sm text-ink-secondary hover:text-ink hover:bg-white/[0.05] transition-colors">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.75" stroke="currentColor" class="w-4 h-4">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 6a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0ZM4.501 20.118a7.5 7.5 0 0 1 14.998 0A17.933 17.933 0 0 1 12 21.75c-2.676 0-5.216-.584-7.499-1.632Z" />
                    </svg>
                    Profile
                  </a>
                </li>
                <li>
                  <a href="/home" class="flex items-center gap-3 px-4 py-2.5 text-sm text-ink-secondary hover:text-ink hover:bg-white/[0.05] transition-colors">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.75" stroke="currentColor" class="w-4 h-4">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M17.593 3.322c1.1.128 1.907 1.077 1.907 2.185V21L12 17.25 4.5 21V5.507c0-1.108.806-2.057 1.907-2.185a48.507 48.507 0 0 1 11.186 0Z" />
                    </svg>
                    My List
                  </a>
                </li>
              </ul>
              <div class="border-t border-white/[0.06] py-1.5">
                <button
                  type="button"
                  onclick={signOut}
                  class="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-ink-secondary hover:text-brand-red hover:bg-white/[0.05] transition-colors"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.75" stroke="currentColor" class="w-4 h-4">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 9V5.25A2.25 2.25 0 0 0 13.5 3h-6a2.25 2.25 0 0 0-2.25 2.25v13.5A2.25 2.25 0 0 0 7.5 21h6a2.25 2.25 0 0 0 2.25-2.25V15m3 0 3-3m0 0-3-3m3 3H9" />
                  </svg>
                  Sign Out
                </button>
              </div>
            </div>
          {/if}
        {:else}
          <!-- Signed out: Generic profile icon button -->
          <button
            type="button"
            onclick={() => profileMenuOpen = !profileMenuOpen}
            class="relative w-10 h-10 rounded-full flex items-center justify-center transition-all duration-300 ease-exo-out hover:scale-110 active:scale-95 group/avatar"
            aria-label="Open profile menu"
            aria-expanded={profileMenuOpen}
            style="box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.08), 0 0 16px -4px rgba(239, 68, 68, 0.3); background: linear-gradient(135deg, rgba(24, 24, 27, 0.6) 0%, rgba(9, 9, 11, 0.8) 100%);"
          >
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.75" stroke="currentColor" class="w-5 h-5 text-ink-secondary group-hover/avatar:text-ink transition-colors">
              <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 6a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0ZM4.501 20.118a7.5 7.5 0 0 1 14.998 0A17.933 17.933 0 0 1 12 21.75c-2.676 0-5.216-.584-7.499-1.632Z" />
            </svg>
          </button>

          <!-- Auth dropdown (signed out) -->
          {#if profileMenuOpen}
            <div
              class="absolute bottom-full right-0 mb-3 w-64 rounded-2xl pointer-events-auto origin-bottom-right"
              style="
                background: linear-gradient(180deg, rgba(24, 24, 27, 0.85) 0%, rgba(9, 9, 11, 0.95) 100%);
                backdrop-filter: blur(40px) saturate(200%);
                -webkit-backdrop-filter: blur(40px) saturate(200%);
                border: 1px solid rgba(255, 255, 255, 0.08);
                box-shadow: 0 -8px 32px -4px rgba(0, 0, 0, 0.6), inset 0 1px 0 rgba(255, 255, 255, 0.06);
                animation: menu-rise 300ms var(--ease-exo-out) both;
              "
            >
              <div class="px-4 py-4 border-b border-white/[0.06]">
                <p class="text-sm font-bold text-ink">Welcome to Watchfy</p>
                <p class="text-[11px] text-ink-subtle mt-0.5">Sign in to track your list and continue watching</p>
              </div>
              <div class="p-3 space-y-2">
                <a
                  href="/signin"
                  class="flex items-center justify-center gap-2 w-full px-4 py-2.5 rounded-xl text-sm font-bold text-ink border border-white/[0.08] hover:border-white/15 hover:bg-white/[0.04] transition-all duration-200"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-4 h-4">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 9V5.25A2.25 2.25 0 0 0 13.5 3h-6a2.25 2.25 0 0 0-2.25 2.25v13.5A2.25 2.25 0 0 0 7.5 21h6a2.25 2.25 0 0 0 2.25-2.25V15m-6 0-3-3m0 0 3-3m-3 3h12" />
                  </svg>
                  Sign In
                </a>
                <a
                  href="/signup"
                  class="flex items-center justify-center gap-2 w-full px-4 py-2.5 rounded-xl text-sm font-extrabold text-white transition-all duration-300 ease-exo-out transform hover:scale-[1.02] active:scale-95"
                  style="background: linear-gradient(135deg, #ef4444 0%, #ec4899 100%); box-shadow: 0 0 16px -4px rgba(239, 68, 68, 0.4);"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-4 h-4">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M19 7.5v3m0 0v3m0-3h3m-3 0h-3m-2.25-4.125a3.375 3.375 0 1 1-6.75 0 3.375 3.375 0 0 1 6.75 0ZM4 19.235v-.11a6.375 6.375 0 0 1 12.75 0v.109A12.318 12.318 0 0 1 10.374 21c-2.331 0-4.512-.645-6.374-1.766Z" />
                  </svg>
                  Create Account
                </a>
              </div>
            </div>
          {/if}
        {/if}
      </div>
    </div>
  </div>
</nav>

<style>
  @keyframes dock-shimmer {
    0%, 100% { transform: translateX(-100%); }
    50% { transform: translateX(100%); }
  }
  @keyframes menu-rise {
    from { opacity: 0; transform: translateY(8px) scale(0.96); }
    to { opacity: 1; transform: translateY(0) scale(1); }
  }
</style>
