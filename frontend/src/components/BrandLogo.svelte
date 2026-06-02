<script lang="ts">
  /**
   * Watchfy brand wordmark. Renders the gradient "Watchfy." treatment
   * with a configurable size and tone (gradient | solid | mono).
   */
  let {
    size = 'md',
    tone = 'gradient',
    showDot = true,
  }: {
    size?: 'sm' | 'md' | 'lg' | 'xl';
    tone?: 'gradient' | 'solid' | 'mono';
    showDot?: boolean;
  } = $props();

  const sizeMap = {
    sm: 'text-lg',
    md: 'text-2xl',
    lg: 'text-3xl',
    xl: 'text-5xl',
  } as const;

  const trackingMap = {
    sm: 'tracking-tight',
    md: 'tracking-tighter',
    lg: 'tracking-tighter',
    xl: 'tracking-tighter',
  } as const;

  const dotSizeMap = {
    sm: 'text-base',
    md: 'text-lg',
    lg: 'text-xl',
    xl: 'text-3xl',
  } as const;
</script>

<span
  class="inline-flex items-baseline font-display font-black {sizeMap[size]} {trackingMap[size]}"
  aria-label="Watchfy"
>
  {#if tone === 'gradient'}
    <span class="text-brand-gradient">Watchfy</span>
  {:else if tone === 'mono'}
    <span class="text-ink">Watchfy</span>
  {:else}
    <span class="text-ink">Watchfy</span>
  {/if}
  {#if showDot}
    <span class="text-ink {dotSizeMap[size]} font-normal">.</span>
  {/if}
</span>
