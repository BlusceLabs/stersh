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