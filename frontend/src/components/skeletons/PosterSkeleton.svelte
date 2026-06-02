<script lang="ts">
  /**
   * Single poster-shaped skeleton card.
   * Uses the global .skeleton shimmer defined in global.css.
   */
  let { width = 'w-[140px] sm:w-[170px]' }: { width?: string } = $props();
</script>

<div class="flex-shrink-0 {width} space-y-3">
  <div class="skeleton aspect-[2/3] rounded-2xl border border-white/[0.04]"></div>
  <div class="space-y-2 px-1">
    <div class="skeleton h-3.5 rounded w-5/6"></div>
    <div class="skeleton h-2.5 rounded w-1/2"></div>
  </div>
</div>
