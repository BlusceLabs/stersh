<script lang="ts">
  export let src: string = '';
  export let title: string = 'Video Player';
  export let autoPlay: boolean = false;
  
  let videoRef: HTMLVideoElement;
  
  $: if (videoRef && src) {
    videoRef.load();
    if (autoPlay) videoRef.play().catch(() => {});
  }
</script>

<div class="relative w-full bg-black rounded-lg overflow-hidden">
  <video
    bind:this={videoRef}
    controls
    {autoPlay}
    class="w-full aspect-video"
    title={title}
  >
    <source src={src} type="application/vnd.apple.mpegurl" />
    <source src={src} type="video/mp4" />
    Your browser does not support HLS video.
  </video>
  
  {#if !src}
    <div class="absolute inset-0 flex items-center justify-center bg-zinc-900">
      <div class="text-center">
        <div class="w-16 h-16 border-4 border-yellow-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
        <p class="text-gray-400">Loading player...</p>
      </div>
    </div>
  {/if}
</div>