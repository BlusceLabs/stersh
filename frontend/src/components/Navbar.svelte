<script lang="ts">
  import { onMount } from 'svelte';

  // Svelte 5 reactive path state anchor
  let currentPath = $state('/');

  onMount(() => {
    // Synchronize initial rendering coordinates securely
    currentPath = window.location.pathname;

    const syncRouteContext = () => {
      currentPath = window.location.pathname;
    };

    // Listen to standard history updates
    window.addEventListener('popstate', syncRouteContext);
    
    // Crucial Guard: Intercept Astro internal client-router swaps natively
    document.addEventListener('astro:page-load', syncRouteContext);

    return () => {
      window.removeEventListener('popstate', syncRouteContext);
      document.removeEventListener('astro:page-load', syncRouteContext);
    };
  });

  const navItems = [
    {
      href: '/',
      label: 'Home',
      icon: 'M2.25 12l8.954-8.955a1.126 1.126 0 011.591 0L21.75 12M4.5 9.75v10.125c0 .621.504 1.125 1.125 1.125H9.75v-4.875c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21h4.125c.621 0 1.125-.504 1.125-1.125V9.75M8.25 21h8.25',
    },
    {
      href: '/movies',
      label: 'Movies',
      // Fixed: Genuine cinema film frame outline path syntax
      icon: 'M16.5 6v12m-9-12v12M3 7.5h18M3 12h18M3 16.5h18M4.5 19.5h15a2.25 2.25 0 0 0 2.25-2.25V6.75A2.25 2.25 0 0 0 19.5 4.5h-15a2.25 2.25 0 0 0-2.25 2.25v10.5A2.25 2.25 0 0 0 4.5 19.5Z',
    },
    {
      href: '/tv',
      label: 'TV Shows',
      icon: 'M6 20.25h12m-12-3h12m-12-3h12m-12-3h12m-6-9v6m-3-3h6M3.75 20.25h16.5c.621 0 1.125-.504 1.125-1.125V4.125c0-.621-.504-1.125-1.125-1.125H3.75c-.621 0-1.125.504-1.125 1.125v15c0 .621.504 1.125 1.125 1.125Z',
    },
    {
      href: '/search',
      label: 'Search',
      icon: 'm21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.604 10.604Z',
    },
  ];

  // Precise navigation matcher logic configuration
  function checkActiveStatus(href: string, current: string): boolean {
    if (href === '/') return current === '/';
    return current.startsWith(href);
  }
</script>

<nav
  class="fixed top-0 left-0 right-0 z-50 px-6 py-3 pointer-events-none hidden md:block"
  aria-label="Desktop primary navigation"
>
  <div
    class="max-w-7xl mx-auto rounded-2xl flex items-center justify-between h-12 px-5
      bg-[#09090b]/70 backdrop-blur-xl border border-zinc-800/50 shadow-xl shadow-black/30
      pointer-events-auto transition-all duration-300"
  >
    <a href="/" class="flex items-center gap-2 text-white font-black text-lg tracking-tight shrink-0">
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="w-6 h-6 text-red-500">
        <path d="M15.75 8.25a.75.75 0 0 1 .75.75c0 1.12-.492 2.126-1.27 2.812a.75.75 0 1 1-.992-1.124A2.243 2.243 0 0 0 15 9a.75.75 0 0 1 .75-.75Z" />
        <path fill-rule="evenodd" d="M12 2.25c-5.385 0-9.75 4.365-9.75 9.75s4.365 9.75 9.75 9.75 9.75-4.365 9.75-9.75S17.385 2.25 12 2.25ZM4.575 15.6a8.25 8.25 0 0 0 9.348 4.425 1.966 1.966 0 0 0-1.84-1.275H9.75a2.25 2.25 0 0 1-2.25-2.25v-.75c0-.621.504-1.125 1.125-1.125h3.75c.621 0 1.125.504 1.125 1.125v.75c0 .621-.504 1.125-1.125 1.125h-.808a3.466 3.466 0 0 0-.467 2.175A8.204 8.204 0 0 1 12 20.25a8.25 8.25 0 0 1-7.425-4.65ZM12 6a2.25 2.25 0 0 1 2.25 2.25v.75a2.25 2.25 0 0 1-4.5 0v-.75A2.25 2.25 0 0 1 12 6Z" clip-rule="evenodd" />
      </svg>
      Watchfy
    </a>

    <div class="flex items-center gap-1">
      {#each navItems as item}
        {@const active = checkActiveStatus(item.href, currentPath)}
        <a
          href={item.href}
          aria-current={active ? 'page' : undefined}
          class="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-bold transition-all duration-200
            {active
              ? 'text-[#8B5CF6] bg-white/5'
              : 'text-zinc-400 hover:text-zinc-200 hover:bg-white/5'}"
        >
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-4 h-4">
            <path stroke-linecap="round" stroke-linejoin="round" d={item.icon} />
          </svg>
          {item.label}
        </a>
      {/each}
    </div>
  </div>
</nav>

<nav
  class="fixed bottom-0 left-0 right-0 z-50 px-4 pb-[env(safe-area-inset-bottom,16px)] pointer-events-none md:hidden"
  aria-label="Mobile primary navigation shell"
>
  <div
    class="max-w-md mx-auto rounded-2xl flex items-center justify-around h-16 px-3
      bg-[#09090b]/60 backdrop-blur-xl border border-zinc-800/50 shadow-[0_-12px_40px_rgba(0,0,0,0.7)]
      pointer-events-auto transition-all duration-300"
  >
    {#each navItems as item}
      {@const active = checkActiveStatus(item.href, currentPath)}
      <a
        href={item.href}
        aria-current={active ? 'page' : undefined}
        class="flex flex-col items-center justify-center gap-1 px-3 py-1.5 rounded-xl transition-all duration-300 min-w-0 select-none
          {active
            ? 'text-[#8B5CF6] scale-105 drop-shadow-[0_0_12px_rgba(139,92,246,0.3)]'
            : 'text-zinc-500 hover:text-zinc-300 active:scale-95'}"
      >
        <svg 
          xmlns="http://www.w3.org/2000/svg" 
          fill="none" 
          viewBox="0 0 24 24" 
          stroke-width={active ? "2.5" : "2"} 
          stroke="currentColor" 
          class="w-5 h-5 transition-transform duration-200"
        >
          <path stroke-linecap="round" stroke-linejoin="round" d={item.icon} />
        </svg>
        
        <span class="text-[10px] font-bold tracking-wider uppercase leading-none whitespace-nowrap">
          {item.label}
        </span>
      </a>
    {/each}
  </div>
</nav>