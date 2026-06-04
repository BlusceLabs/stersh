<script lang="ts">
  /**
   * Horizontal media row skeleton. YouTube-style 16:9 cards.
   */
  let { count = 7 }: { count?: number } = $props();
</script>

<div class="mb-8">
  <div class="flex items-end justify-between mb-3 px-4 md:px-6">
    <div class="skeleton h-6 w-48 rounded"></div>
  </div>
  <div class="flex gap-4 overflow-hidden px-4 md:px-6">
    {#each Array(count) as _, i}
      <div class="flex-shrink-0 w-[280px] sm:w-[320px] md:w-[340px]" style="animation-delay: {i * 30}ms">
        <div class="skeleton aspect-video rounded-xl"></div>
        <div class="flex gap-3 mt-3">
          <div class="skeleton w-9 h-9 rounded-full flex-shrink-0"></div>
          <div class="flex-1 space-y-2">
            <div class="skeleton h-3.5 rounded w-5/6"></div>
            <div class="skeleton h-3 rounded w-3/4"></div>
            <div class="skeleton h-3 rounded w-1/2"></div>
          </div>
        </div>
      </div>
    {/each}
  </div>
</div>
