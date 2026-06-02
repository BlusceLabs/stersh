<script lang="ts">
  /**
   * Detail page hero skeleton — backdrop, poster, title, action row.
   * Replaces the inline skeleton in DetailsPage.svelte.
   */
</script>

<div class="min-h-screen bg-surface-0 flex items-center justify-center px-4 sm:px-6 lg:px-8">
  <div class="max-w-7xl w-full mx-auto grid grid-cols-1 md:grid-cols-[280px_1fr] lg:grid-cols-[340px_1fr] gap-10 lg:gap-16 items-center pt-24">
    <div class="skeleton w-full aspect-[2/3] rounded-2xl hidden md:block"></div>
    <div class="space-y-6">
      <div class="flex gap-2">
        <div class="skeleton h-6 rounded w-20"></div>
        <div class="skeleton h-6 rounded w-16"></div>
        <div class="skeleton h-6 rounded w-24"></div>
      </div>
      <div class="skeleton h-12 rounded-xl w-3/4"></div>
      <div class="skeleton h-4 rounded w-1/2"></div>
      <div class="space-y-2 pt-4">
        <div class="skeleton h-4 rounded w-full"></div>
        <div class="skeleton h-4 rounded w-5/6"></div>
        <div class="skeleton h-4 rounded w-4/6"></div>
      </div>
      <div class="flex gap-3 pt-4">
        <div class="skeleton h-12 w-32 rounded-xl"></div>
        <div class="skeleton h-12 w-32 rounded-xl"></div>
      </div>
    </div>
  </div>
</div>
