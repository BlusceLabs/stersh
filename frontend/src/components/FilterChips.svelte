<script lang="ts">
  /**
   * YouTube-style horizontal filter chip row. Sticky, scrolls horizontally,
   * with a left/right fade gradient. Each chip can be active.
   */
  let {
    chips = [] as { id: string; label: string }[],
    active = '',
    hrefBuilder = (id: string) => '#',
  }: {
    chips: { id: string; label: string }[];
    active?: string;
    hrefBuilder?: (id: string) => string;
  } = $props();

  let scroller: HTMLDivElement | undefined = $state();
  let canScrollLeft = $state(false);
  let canScrollRight = $state(false);

  function update() {
    if (!scroller) return;
    canScrollLeft = scroller.scrollLeft > 4;
    canScrollRight = scroller.scrollLeft + scroller.clientWidth < scroller.scrollWidth - 4;
  }

  function scrollBy(dir: 1 | -1) {
    if (!scroller) return;
    scroller.scrollBy({ left: dir * 400, behavior: 'smooth' });
  }

  $effect(() => {
    if (!scroller) return;
    update();
    const onScroll = () => update();
    scroller.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', update);
    return () => {
      scroller?.removeEventListener('scroll', onScroll);
      window.removeEventListener('resize', update);
    };
  });
</script>

<div class="sticky top-14 z-30 bg-base -mx-4 px-4 sm:-mx-6 sm:px-6 lg:mx-0 lg:px-0">
  <div class="relative">
    {#if canScrollLeft}
      <button
        type="button"
        onclick={() => scrollBy(-1)}
        class="hidden sm:flex absolute left-0 top-1/2 -translate-y-1/2 z-10 w-8 h-8 bg-base items-center justify-center"
        aria-label="Scroll chips left"
      >
        <svg viewBox="0 0 24 24" class="w-5 h-5" fill="currentColor" aria-hidden="true">
          <path d="M15 6l-6 6 6 6V6z" />
        </svg>
      </button>
    {/if}
    {#if canScrollRight}
      <button
        type="button"
        onclick={() => scrollBy(1)}
        class="hidden sm:flex absolute right-0 top-1/2 -translate-y-1/2 z-10 w-8 h-8 bg-base items-center justify-center"
        aria-label="Scroll chips right"
      >
        <svg viewBox="0 0 24 24" class="w-5 h-5" fill="currentColor" aria-hidden="true">
          <path d="M9 6v12l6-6-6-6z" />
        </svg>
      </button>
    {/if}
    {#if canScrollLeft}
      <div class="pointer-events-none absolute left-0 top-0 bottom-0 w-8 bg-gradient-to-r from-base to-transparent z-[1]"></div>
    {/if}
    {#if canScrollRight}
      <div class="pointer-events-none absolute right-0 top-0 bottom-0 w-8 bg-gradient-to-l from-base to-transparent z-[1]"></div>
    {/if}

    <div
      bind:this={scroller}
      class="flex gap-3 overflow-x-auto no-scrollbar py-3"
      role="tablist"
    >
      {#each chips as chip}
        <a
          href={hrefBuilder(chip.id)}
          class="yt-chip flex-shrink-0"
          data-active={chip.id === active}
          role="tab"
          aria-selected={chip.id === active}
        >
          {chip.label}
        </a>
      {/each}
    </div>
  </div>
</div>
