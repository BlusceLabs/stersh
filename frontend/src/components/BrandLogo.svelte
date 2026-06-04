<script lang="ts">
  /**
   * Watchfy brand wordmark. YouTube-style: a red play button triangle
   * followed by the "Watchfy" wordmark in white.
   */
  let {
    size = 'md',
  }: {
    size?: 'sm' | 'md' | 'lg' | 'xl';
  } = $props();

  const textSizeMap = {
    sm: 'text-[15px]',
    md: 'text-[20px]',
    lg: 'text-[28px]',
    xl: 'text-[48px]',
  } as const;

  const iconSizeMap = {
    sm: 'h-4 w-5',
    md: 'h-5 w-7',
    lg: 'h-7 w-10',
    xl: 'h-12 w-16',
  } as const;

  const gapMap = {
    sm: 'gap-1.5',
    md: 'gap-2',
    lg: 'gap-2.5',
    xl: 'gap-3',
  } as const;
</script>

<span
  class="inline-flex items-center {gapMap[size]} font-sans select-none"
  aria-label="Watchfy"
>
  <span class="relative inline-flex items-center justify-center {iconSizeMap[size]}" aria-hidden="true">
    <svg viewBox="0 0 90 60" class="w-full h-full">
      <polygon points="0,0 90,30 0,60" fill="#ff0000" />
      <polygon points="20,12 70,30 20,48" fill="#fff" />
    </svg>
  </span>
  <span class="font-sans {textSizeMap[size]} font-bold tracking-tight leading-none text-white">
    Watchfy
  </span>
</span>
