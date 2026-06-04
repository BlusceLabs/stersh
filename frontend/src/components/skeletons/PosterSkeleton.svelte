<script lang="ts">
  /**
   * Single 16:9 video card skeleton.
   */
  let { width = 'w-[280px]' }: { width?: string } = $props();
</script>

<div class="flex-shrink-0 {width}">
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
