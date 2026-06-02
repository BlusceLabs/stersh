<script lang="ts">
  /**
   * Horizontal media row skeleton. Renders a configurable number of
   * PosterSkeleton cards with a leading title skeleton.
   */
  let { count = 7 }: { count?: number } = $props();
</script>

<div class="mb-10">
  <div class="flex items-end justify-between mb-4 px-4 md:px-12">
    <div class="skeleton h-6 w-48 rounded"></div>
  </div>
  <div class="flex gap-4 overflow-hidden px-4 md:px-12">
    {#each Array(count) as _}
      <div class="skeleton aspect-[2/3] w-[140px] sm:w-[170px] flex-shrink-0 rounded-2xl"></div>
    {/each}
  </div>
</div>
