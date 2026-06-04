<script lang="ts">
  /**
   * YouTube-style empty/error state.
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

  const iconColor = $derived(
    {
      empty: 'text-ink-muted',
      error: 'text-yt-red',
      info: 'text-ink-muted',
      loading: 'text-ink-muted',
    }[variant]
  );
</script>

<div
  class="text-center {compact ? 'py-6' : 'py-16'}"
  role={variant === 'error' ? 'alert' : 'status'}
  aria-live={variant === 'error' ? 'assertive' : 'polite'}
>
  <div class="{compact ? 'w-12 h-12 mb-3' : 'w-16 h-16 mb-4'} mx-auto rounded-full bg-base-2 flex items-center justify-center {iconColor}">
    {#if icon === 'film'}
      <svg viewBox="0 0 24 24" class="{compact ? 'w-5 h-5' : 'w-7 h-7'}" fill="currentColor" aria-hidden="true">
        <path d="M18 4l2 4h-3l-2-4h-2l2 4h-3l-2-4H8l2 4H7L5 4H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V4h-4z" />
      </svg>
    {:else if icon === 'search'}
      <svg viewBox="0 0 24 24" class="{compact ? 'w-5 h-5' : 'w-7 h-7'}" fill="currentColor" aria-hidden="true">
        <path d="M10 4a6 6 0 1 0 3.815 10.65L18 18.835 19.415 17.42l-4.185-4.185A6 6 0 0 0 10 4zm0 2a4 4 0 1 1 0 8 4 4 0 0 1 0-8z" />
      </svg>
    {:else if icon === 'list'}
      <svg viewBox="0 0 24 24" class="{compact ? 'w-5 h-5' : 'w-7 h-7'}" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
        <path stroke-linecap="round" stroke-linejoin="round" d="M8 6h12M8 12h12M8 18h12M4 6h.01M4 12h.01M4 18h.01" />
      </svg>
    {:else if icon === 'episode'}
      <svg viewBox="0 0 24 24" class="{compact ? 'w-5 h-5' : 'w-7 h-7'}" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
        <path stroke-linecap="round" stroke-linejoin="round" d="M3 6h18M3 12h18M3 18h18" />
      </svg>
    {:else if icon === 'alert'}
      <svg viewBox="0 0 24 24" class="{compact ? 'w-5 h-5' : 'w-7 h-7'}" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
        <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z" />
      </svg>
    {:else}
      <svg viewBox="0 0 24 24" class="{compact ? 'w-5 h-5' : 'w-7 h-7'}" fill="currentColor" aria-hidden="true">
        <path d="M8 5v14l11-7z" />
      </svg>
    {/if}
  </div>

  <h3 class="text-{compact ? 'base' : 'lg'} font-bold text-ink mb-1">{title}</h3>
  {#if message}
    <p class="text-sm text-ink-muted max-w-md mx-auto">{message}</p>
  {/if}

  {#if ctaLabel}
    <div class="mt-4">
      {#if ctaHref}
        <a
          href={ctaHref}
          class="inline-flex items-center gap-2 h-9 px-5 border border-yt-blue text-yt-blue rounded-full text-sm font-medium hover:bg-yt-blue/10"
        >
          {ctaLabel}
        </a>
      {:else if oncTaClick}
        <button
          type="button"
          onclick={oncTaClick}
          class="inline-flex items-center gap-2 h-9 px-5 border border-yt-blue text-yt-blue rounded-full text-sm font-medium hover:bg-yt-blue/10"
        >
          {ctaLabel}
        </button>
      {/if}
    </div>
  {/if}
</div>
