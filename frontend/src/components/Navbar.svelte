<script lang="ts">
  import { onMount } from 'svelte';

  let currentPath = $state('/');

  onMount(() => {
    currentPath = window.location.pathname;
    const handleLocation = () => {
      currentPath = window.location.pathname;
    };
    window.addEventListener('popstate', handleLocation);
    return () => window.removeEventListener('popstate', handleLocation);
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
      icon: 'M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z',
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

  function isActive(href: string): boolean {
    if (href === '/') return currentPath === '/';
    return currentPath.startsWith(href);
  }
</script>

<nav
  class="fixed bottom-0 left-0 right-0 z-50 px-2 pb-[env(safe-area-inset-bottom,0px)]"
>
  <div
    class="max-w-[1744px] mx-auto rounded-2xl flex items-center justify-around h-16 px-2
      bg-black/[0.2] backdrop-blur-xl border border-white/[0.06] shadow-[0_-8px_32px_0_rgba(0,0,0,0.5)]
      transition-all duration-300"
  >
    {#each navItems as item}
      <a
        href={item.href}
        class="flex flex-col items-center justify-center gap-0.5 px-3 py-1.5 rounded-xl transition-all duration-200 min-w-0
          {isActive(item.href)
            ? 'text-red-500'
            : 'text-zinc-500 hover:text-zinc-300 hover:bg-white/[0.04]'}"
      >
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-5 h-5">
          <path stroke-linecap="round" stroke-linejoin="round" d={item.icon} />
        </svg>
        <span class="text-[10px] font-semibold tracking-wide leading-none whitespace-nowrap">
          {item.label}
        </span>
      </a>
    {/each}
  </div>
</nav>
