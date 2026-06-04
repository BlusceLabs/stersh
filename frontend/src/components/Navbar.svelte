<script lang="ts">
  import { onMount } from 'svelte';

  let currentPath = $state('/');

  function checkActive(href: string): boolean {
    if (href === '/' || href === '/home') {
      return currentPath === '/' || currentPath === '/home';
    }
    return currentPath === href || currentPath.startsWith(href + '/');
  }

  onMount(() => {
    const sync = () => { currentPath = window.location.pathname; };
    sync();
    window.addEventListener('popstate', sync);
    document.addEventListener('astro:page-load', sync);
    return () => {
      window.removeEventListener('popstate', sync);
      document.removeEventListener('astro:page-load', sync);
    };
  });

  const items = [
    {
      href: '/home',
      label: 'Home',
      icon: 'M12 4l9 8h-3v8h-4v-6h-4v6H6v-8H3l9-8z',
    },
    {
      href: '/movies',
      label: 'Shorts',
      icon: 'M10 14.65v-5.3L15 12l-5 2.65zm7.77-4.33c-.77-.32-1.2-.5-1.2-.5L18 9.06c1.84-.96 2.53-3.23 1.56-5.06s-3.24-2.53-5.07-1.56L6 6.94c-1.29.68-2.07 2.04-2 3.49.07 1.42.93 2.67 2.22 3.25.03.01 1.2.5 1.2.5L6 14.93c-1.83.97-2.53 3.24-1.56 5.07.97 1.83 3.24 2.53 5.07 1.56l8.5-4.5c1.29-.68 2.06-2.04 1.99-3.49-.07-1.42-.94-2.68-2.23-3.25zM10 14.65v-5.3L15 12l-5 2.65z',
    },
    {
      href: '/mylist',
      label: 'Library',
      icon: 'M14 6l-3.75 5 2.85 3.8-1.6 1.2C9.81 13.95 7.78 12.5 6 12.5c-3.5 0-3.5 3.5-3.5 3.5v3h17v-3c0-1.5-1-3-3-3-1.78 0-3.81 1.45-5.5 3.5l-1.6-1.2L14 6z',
    },
    {
      href: '/search',
      label: 'Search',
      icon: 'M10 4a6 6 0 1 0 3.815 10.65L18 18.835 19.415 17.42l-4.185-4.185A6 6 0 0 0 10 4zm0 2a4 4 0 1 1 0 8 4 4 0 0 1 0-8z',
    },
  ];
</script>

<nav
  class="lg:hidden fixed bottom-0 left-0 right-0 z-nav bg-base border-t border-white/10"
  aria-label="Bottom navigation"
>
  <ul class="flex items-stretch justify-around h-14">
    {#each items as item}
      {@const active = checkActive(item.href)}
      <li class="flex-1">
        <a
          href={item.href}
          class="relative flex flex-col items-center justify-center h-full {active ? 'text-ink' : 'text-ink-secondary'} hover:text-ink transition-colors duration-100"
          aria-current={active ? 'page' : undefined}
          aria-label={item.label}
        >
          {#if active}
            <span class="absolute top-0 left-1/2 -translate-x-1/2 w-12 h-0.5 bg-white rounded-b" aria-hidden="true"></span>
          {/if}
          <svg viewBox="0 0 24 24" class="w-6 h-6 mb-0.5" fill="currentColor" aria-hidden="true">
            <path d={item.icon} />
          </svg>
          <span class="text-[10px] font-medium leading-none">{item.label}</span>
        </a>
      </li>
    {/each}
  </ul>
</nav>
