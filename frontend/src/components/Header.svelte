<script lang="ts">
  import { onMount } from 'svelte';
  import BrandLogo from './BrandLogo.svelte';

  let currentPath = $state('/');
  let scrolled = $state(false);
  let mobileSearchOpen = $state(false);

  const navItems = [
    { href: '/home', label: 'Home' },
    { href: '/movies', label: 'Movies' },
    { href: '/tv', label: 'TV Shows' },
    { href: '/search', label: 'Search' },
  ];

  function checkActiveStatus(href: string, current: string): boolean {
    if (href === '/') return current === '/';
    return current.startsWith(href);
  }

  onMount(() => {
    currentPath = window.location.pathname;

    const sync = () => { currentPath = window.location.pathname; };
    const onScroll = () => { scrolled = window.scrollY > 8; };

    window.addEventListener('popstate', sync);
    document.addEventListener('astro:page-load', sync);
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();

    return () => {
      window.removeEventListener('popstate', sync);
      document.removeEventListener('astro:page-load', sync);
      window.removeEventListener('scroll', onScroll);
    };
  });
</script>

<header
  class="fixed top-0 left-0 right-0 z-nav transition-all duration-500 ease-exo-out
    {scrolled ? 'glass-strong' : 'bg-transparent'}
    hidden lg:block"
  aria-label="Site header"
>
  <div class="max-w-content mx-auto h-16 px-6 xl:px-10 flex items-center justify-between gap-8">

    <a
      href="/"
      class="flex items-center gap-2 transition-transform duration-300 ease-exo-out hover:scale-[1.02] active:scale-[0.98] focus-visible:outline-none rounded-md"
      aria-label="Watchfy home"
    >
      <BrandLogo size="md" tone="gradient" />
    </a>

    <nav aria-label="Primary navigation" class="flex-1">
      <ul class="flex items-center justify-center gap-1">
        {#each navItems as item}
          {@const active = checkActiveStatus(item.href, currentPath)}
          <li>
            <a
              href={item.href}
              aria-current={active ? 'page' : undefined}
              class="relative inline-flex items-center px-4 py-2 rounded-lg text-sm font-semibold transition-colors duration-200
                {active ? 'text-ink' : 'text-ink-muted hover:text-ink'}"
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
      <a
        href="/search"
        class="inline-flex items-center justify-center w-10 h-10 rounded-xl text-ink-muted hover:text-ink hover:bg-white/[0.05] transition-colors duration-200"
        aria-label="Search"
      >
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-5 h-5">
          <path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.604 10.604Z" />
        </svg>
      </a>

      <a
        href="/search"
        class="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-brand-gradient-cta text-white text-sm font-bold shadow-glow-red hover:brightness-110 hover:scale-[1.02] active:scale-[0.98] transition-all duration-200"
      >
        <span>Sign In</span>
      </a>
    </div>

  </div>
</header>
