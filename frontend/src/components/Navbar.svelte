<script lang="ts">
  import { onMount } from 'svelte';

  let currentPath = $state('/');
  let pressing = $state('');
  let mounted = $state(false);

  onMount(() => {
    currentPath = window.location.pathname;
    mounted = true;
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
  class="fixed bottom-0 left-0 right-0 z-nav pointer-events-none lg:hidden"
  aria-label="Primary navigation"
>
  <!-- Ambient glow behind the dock -->
  <div class="absolute bottom-2 left-1/2 -translate-x-1/2 w-[70%] h-8 bg-brand-red/[0.08] rounded-full blur-2xl" aria-hidden="true"></div>

  <div class="px-4 pb-[calc(0.75rem+env(safe-area-inset-bottom,0px))] sm:pb-[calc(1rem+env(safe-area-inset-bottom,0px))]">
    <div
      class="mx-auto max-w-md rounded-[1.25rem] flex items-center justify-around h-[68px] px-1.5
        pointer-events-auto
        transition-all duration-500 ease-exo-out
        {mounted ? 'translate-y-0 opacity-100' : 'translate-y-8 opacity-0'}"
      style="
        background: linear-gradient(135deg, rgba(24, 24, 27, 0.85) 0%, rgba(9, 9, 11, 0.92) 100%);
        backdrop-filter: blur(32px) saturate(200%);
        -webkit-backdrop-filter: blur(32px) saturate(200%);
        border: 1px solid rgba(255, 255, 255, 0.06);
        box-shadow: 0 -4px 32px -8px rgba(0, 0, 0, 0.5), 0 0 0 1px rgba(255, 255, 255, 0.03), inset 0 1px 0 rgba(255, 255, 255, 0.04);
      "
    >
      {#each navItems as item}
        {@const active = checkActiveStatus(item.href, currentPath)}
        <a
          href={item.href}
          aria-current={active ? 'page' : undefined}
          aria-label={item.label}
          class="relative flex flex-col items-center justify-center gap-1 px-3.5 py-2 rounded-2xl transition-all duration-300 ease-exo-out min-w-[56px] select-none group
            {active
              ? 'text-ink'
              : 'text-ink-subtle active:text-ink-secondary'}"
          onpointerdown={() => pressing = item.href}
          onpointerup={() => pressing = ''}
          onpointerleave={() => pressing = ''}
        >
          <!-- Active pill background -->
          {#if active}
            <span
              class="absolute inset-1 rounded-[0.85rem] transition-all duration-500 ease-exo-out"
              style="
                background: linear-gradient(135deg, rgba(239, 68, 68, 0.12) 0%, rgba(236, 72, 153, 0.08) 100%);
                box-shadow: 0 0 20px -4px rgba(239, 68, 68, 0.2), inset 0 1px 0 rgba(255, 255, 255, 0.04);
              "
              aria-hidden="true"
            ></span>
          {/if}

          <!-- Active top glow bar -->
          {#if active}
            <span class="absolute -top-px left-1/2 -translate-x-1/2 w-8 h-[2px] rounded-full bg-brand-gradient-cta shadow-glow-red" aria-hidden="true"></span>
          {/if}

          <!-- Icon container -->
          <div
            class="relative transition-all duration-300 ease-exo-out
              {active ? 'scale-100' : 'group-active:scale-90'}"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              stroke-width={active ? 2.25 : 1.75}
              stroke="currentColor"
              class="w-[22px] h-[22px] transition-all duration-300 ease-exo-out
                {active ? 'text-white drop-shadow-[0_0_8px_rgba(239,68,68,0.3)]' : 'group-hover:text-ink-muted group-hover:scale-105'}"
              aria-hidden="true"
            >
              <path stroke-linecap="round" stroke-linejoin="round" d={item.icon} />
            </svg>
          </div>

          <!-- Label -->
          <span class="text-[9.5px] font-bold tracking-wider uppercase leading-none whitespace-nowrap transition-all duration-300 ease-exo-out
            {active
              ? 'opacity-100 text-ink translate-y-0'
              : 'opacity-50 group-hover:opacity-70 group-active:opacity-80'}">
            {item.label}
          </span>

          <!-- Press ripple -->
          {#if pressing === item.href}
            <span class="absolute inset-1 rounded-[0.85rem] bg-white/[0.04] animate-pulse" aria-hidden="true"></span>
          {/if}
        </a>
      {/each}
    </div>
  </div>
</nav>
