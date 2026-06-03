<script lang="ts">
  import { onMount } from 'svelte';

  let currentPath = $state('/');
  let pressing = $state('');

  onMount(() => {
    currentPath = window.location.pathname;
    const sync = () => { currentPath = window.location.pathname; };
    window.addEventListener('popstate', sync);
    document.addEventListener('astro:page-load', sync);
    return () => {
      window.removeEventListener('popstate', sync);
      document.removeEventListener('astro:page-load', sync);
    };
  });

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
</script>

<nav
  class="fixed bottom-0 left-0 right-0 z-nav px-3 pb-3 sm:pb-4 pointer-events-none lg:hidden"
  aria-label="Primary navigation"
>
  <div
    class="mx-auto rounded-2xl flex items-center justify-around h-16 sm:h-[68px] px-2 sm:px-4
      glass-strong shadow-4
      pointer-events-auto transition-all duration-300 max-w-lg sm:max-w-xl border-t border-white/[0.06]"
  >
    {#each navItems as item}
      {@const active = checkActiveStatus(item.href, currentPath)}
      <a
        href={item.href}
        aria-current={active ? 'page' : undefined}
        aria-label={item.label}
        class="relative flex flex-col items-center justify-center gap-0.5 px-3 sm:px-5 py-2 rounded-xl transition-all duration-300 ease-exo-out min-w-0 select-none group
          {active
            ? 'text-ink'
            : 'text-ink-subtle hover:text-ink-secondary'}"
        onpointerdown={() => pressing = item.href}
        onpointerup={() => pressing = ''}
        onpointerleave={() => pressing = ''}
      >
        {#if active}
          <span class="absolute -top-1 left-1/2 -translate-x-1/2 w-6 h-0.5 rounded-full bg-brand-gradient-cta shadow-glow-red" aria-hidden="true"></span>
        {/if}

        <div
          class="relative p-1.5 rounded-xl transition-all duration-300 ease-exo-out
            {active ? 'bg-white/[0.08]' : ''}"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            stroke-width={active ? 2.5 : 1.75}
            stroke="currentColor"
            class="w-5 h-5 sm:w-[22px] sm:h-[22px] transition-all duration-300 group-hover:scale-105
              {active ? 'text-white' : ''}"
            aria-hidden="true"
          >
            <path stroke-linecap="round" stroke-linejoin="round" d={item.icon} />
          </svg>

          {#if active}
            <span class="absolute inset-0 rounded-xl bg-brand-red/10 animate-pulse-glow" aria-hidden="true"></span>
          {/if}
        </div>

        <span class="text-[10px] sm:text-[11px] font-bold tracking-wide leading-none whitespace-nowrap mt-0.5 transition-all duration-300
          {active ? 'opacity-100' : 'opacity-70 group-hover:opacity-90 group-hover:scale-105'}">
          {item.label}
        </span>
      </a>
    {/each}
  </div>
</nav>