
<script lang="ts">
  let { src = '', title = 'Video Player', autoPlay = false } = $props();
  
  let hlsUrl = $state('');
  let loading = $state(false);
  let error = $state('');
  
  $effect(() => {
    if (src && !hlsUrl) {
      loading = true;
      error = '';
      fetch(src)
        .then(r => r.ok ? r.json() : Promise.reject())
        .then(data => {
          if (data.sources?.length) {
            hlsUrl = data.sources[0].url;
          } else {
            error = 'No sources available';
          }
        })
        .catch(() => error = 'Failed to load stream')
        .finally(() => loading = false);
    }
  });
</script>

<div class="relative w-full bg-surface-sunken rounded-lg overflow-hidden">
  {#if loading}
    <div class="absolute inset-0 flex items-center justify-center bg-surface">
      <div class="text-center">
        <div class="w-16 h-16 border-4 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
        <p class="text-text-muted">Loading stream...</p>
      </div>
    </div>
  {/if}
  
  {#if error}
    <div class="absolute inset-0 flex items-center justify-center bg-surface">
      <p class="text-red-400">{error}</p>
    </div>
  {/if}
  
  <video
    controls
    {autoPlay}
    class="w-full aspect-video"
    title={title}
  >
    <source src={hlsUrl} type="application/vnd.apple.mpegurl" />
    <source src={hlsUrl} type="video/mp4" />
    Your browser does not support HLS video.
  </video>
</div>