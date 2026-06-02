<script lang="ts">
  /**
   * Branded empty/error state with optional call-to-action.
   * Replaces ad-hoc inline "no data" messages scattered across pages.
   */
  let {
    title = 'Nothing here yet',
    message = '',
    variant = 'empty',
    ctaLabel = '',
    ctaHref = '',
    oncTaClick = undefined as (() => void) | undefined,
    icon = 'film',
    compact = false,
  }: {
    title?: string;
    message?: string;
    variant?: 'empty' | 'error' | 'info' | 'loading';
    ctaLabel?: string;
    ctaHref?: string;
    oncTaClick?: () => void;
    icon?: 'film' | 'search' | 'list' | 'episode' | 'alert' | 'play';
    compact?: boolean;
  } = $props();

  const tone = $derived(
    {
      empty: { ring: 'border-white/10', bg: 'bg-surface-1/40', text: 'text-ink-muted' },
      error: { ring: 'border-brand-red/20', bg: 'bg-brand-red/[0.04]', text: 'text-brand-red' },
      info: { ring: 'border-brand-cyan/20', bg: 'bg-brand-cyan/[0.04]', text: 'text-brand-cyan' },
      loading: { ring: 'border-white/10', bg: 'bg-surface-1/40', text: 'text-ink-muted' },
    }[variant]
  );

  const padding = $derived(compact ? 'p-4 sm:p-5' : 'p-8 sm:p-10');
  const iconSize = $derived(compact ? 'w-10 h-10 mb-3' : 'w-14 h-14 mb-5');
  const iconInner = $derived(compact ? 'w-5 h-5' : 'w-6 h-6');
</script>

<div
  class="rounded-2xl {padding} text-center {tone.ring} {compact ? 'bg-transparent border' : 'surface-elevated'}"
  role={variant === 'error' ? 'alert' : 'status'}
  aria-live={variant === 'error' ? 'assertive' : 'polite'}
>
  <div
    class="{iconSize} mx-auto rounded-2xl {tone.bg} border {tone.ring} flex items-center justify-center {tone.text}"
    aria-hidden="true"
  >
    {#if icon === 'film'}
      <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class={iconInner}>
        <path stroke-linecap="round" stroke-linejoin="round" d="M3.375 19.5h17.25m-17.25 0a1.125 1.125 0 0 1-1.125-1.125M3.375 19.5h7.5c.621 0 1.125-.504 1.125-1.125m-9.75 0V5.625m0 12.75v-1.5c0-.621.504-1.125 1.125-1.125m18.375 2.625V5.625m0 12.75c0 .621-.504 1.125-1.125 1.125m1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125m0 3.75h-7.5A1.125 1.125 0 0 1 12 18.375m9.75-12.75c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125m19.5 0v1.5c0 .621-.504 1.125-1.125 1.125M2.25 5.625v1.5c0 .621.504 1.125 1.125 1.125m0 0h17.25m-17.25 0h7.5c.621 0 1.125.504 1.125 1.125M3.375 8.25c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125m17.25-3.75h-7.5c-.621 0-1.125.504-1.125 1.125m8.625-1.125c.621 0 1.125.504 1.125 1.125v1.5c0 .621-.504 1.125-1.125 1.125m-17.25 0h7.5m-7.5 0c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125M12 10.875v-1.5m0 1.5c0 .621-.504 1.125-1.125 1.125M12 10.875c0 .621.504 1.125 1.125 1.125m-2.25 0c.621 0 1.125.504 1.125 1.125M13.125 12h7.5m-7.5 0c-.621 0-1.125.504-1.125 1.125M20.625 12c.621 0 1.125.504 1.125 1.125v1.5c0 .621-.504 1.125-1.125 1.125m-17.25 0h7.5M12 14.625v-1.5" />
      </svg>
    {:else if icon === 'search'}
      <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class={iconInner}>
        <path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.604 10.604Z" />
      </svg>
    {:else if icon === 'list'}
      <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class={iconInner}>
        <path stroke-linecap="round" stroke-linejoin="round" d="M8.242 5.992h6m-6 4.998h6m-6 4.999h6M4.243 5.992h.007m-.007 4.998h.007m-.007 4.999h.007" />
      </svg>
    {:else if icon === 'episode'}
      <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class={iconInner}>
        <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 4.5h16.5v3.75H3.75V4.5Zm0 5.25h16.5v3.75H3.75V9.75Zm0 5.25h16.5v3.75H3.75V15Z" />
      </svg>
    {:else if icon === 'alert'}
      <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class={iconInner}>
        <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m9-.75a9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z" />
      </svg>
    {:else}
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class={iconInner}>
        <path fill-rule="evenodd" d="M4.5 5.653c0-1.426 1.529-2.33 2.779-1.643l11.54 6.347c1.295.712 1.295 2.573 0 3.286L7.28 19.99c-1.25.687-2.779-.218-2.779-1.643V5.653Z" clip-rule="evenodd" />
      </svg>
    {/if}
  </div>

  <h3 class="text-base sm:text-lg font-bold text-ink mb-1.5 tracking-tight">{title}</h3>
  {#if message}
    <p class="text-sm text-ink-muted max-w-md mx-auto leading-relaxed">{message}</p>
  {/if}

  {#if ctaLabel}
    <div class="mt-6">
      {#if ctaHref}
        <a
          href={ctaHref}
          class="inline-flex items-center gap-2 px-5 py-2.5 bg-brand-gradient-cta text-white text-sm font-bold rounded-xl hover:brightness-110 active:scale-95 transition-all duration-200 shadow-glow-red"
        >
          {ctaLabel}
        </a>
      {:else if oncTaClick}
        <button
          type="button"
          onclick={oncTaClick}
          class="inline-flex items-center gap-2 px-5 py-2.5 bg-brand-gradient-cta text-white text-sm font-bold rounded-xl hover:brightness-110 active:scale-95 transition-all duration-200 shadow-glow-red"
        >
          {ctaLabel}
        </button>
      {/if}
    </div>
  {/if}
</div>
