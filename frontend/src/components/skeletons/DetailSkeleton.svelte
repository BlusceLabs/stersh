<script lang="ts">
  /**
   * Detail page skeleton (YouTube-style): backdrop, poster, title row, action row.
   */
</script>

<div class="min-h-screen bg-base">
  <div class="w-full h-[280px] md:h-[380px] bg-base-2"></div>
  <div class="max-w-[1280px] mx-auto px-4 md:px-6 -mt-24 md:-mt-32 relative">
    <div class="flex flex-col md:flex-row gap-6 md:gap-8">
      <div class="flex-shrink-0 w-[160px] md:w-[260px] aspect-[2/3] rounded-xl skeleton mx-auto md:mx-0"></div>
      <div class="flex-1 min-w-0 space-y-4">
        <div class="skeleton h-8 md:h-10 rounded w-3/4"></div>
        <div class="skeleton h-4 rounded w-1/2"></div>
        <div class="flex gap-2 mt-3">
          <div class="skeleton h-6 w-16 rounded-full"></div>
          <div class="skeleton h-6 w-20 rounded-full"></div>
          <div class="skeleton h-6 w-14 rounded-full"></div>
        </div>
        <div class="flex gap-2 mt-4">
          <div class="skeleton h-10 w-24 rounded-full"></div>
          <div class="skeleton h-10 w-10 rounded-full"></div>
          <div class="skeleton h-10 w-10 rounded-full"></div>
        </div>
        <div class="skeleton h-20 rounded-xl w-full max-w-3xl"></div>
      </div>
    </div>
  </div>
</div>
