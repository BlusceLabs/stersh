<script lang="ts">
  import Hls from 'hls.js';

  let { src = '', title = 'Video Player', autoPlay = false, server = 'white' } = $props();

  let videoEl: HTMLVideoElement;
  let hlsInstance: Hls | null = null;
  let hlsUrl = $state('');
  let loading = $state(false);
  let error = $state('');

  $effect(() => {
    if (!src) {
      hlsUrl = '';
      return;
    }

    loading = true;
    error = '';
    hlsUrl = '';

    let cancelled = false;

    fetch(src)
      .then(r => {
        if (!r.ok) throw new Error('Fetch failed');
        return r.json();
      })
      .then(data => {
        if (cancelled) return;
        if (data.sources?.length) {
          const rawUrl = data.sources[0].url;
          hlsUrl = `/api/${server}/proxy/hls?url=${encodeURIComponent(rawUrl)}`;
        } else {
          error = 'No stream sources available for this title';
        }
      })
      .catch(() => {
        if (!cancelled) error = 'Failed to establish stable stream path';
      })
      .finally(() => {
        if (!cancelled) loading = false;
      });

    return () => { cancelled = true; };
  });

  $effect(() => {
    if (!hlsUrl || !videoEl) return;

    if (hlsInstance) {
      hlsInstance.destroy();
      hlsInstance = null;
    }

    if (Hls.isSupported()) {
      const hls = new Hls({
        startPosition: 0,
      });
      hls.loadSource(hlsUrl);
      hls.attachMedia(videoEl);
      hls.on(Hls.Events.MANIFEST_PARSED, () => {
        if (autoPlay) videoEl.play().catch(() => {});
      });
      hls.on(Hls.Events.ERROR, (_event, data) => {
        if (data.fatal) {
          error = 'Stream connection interrupted';
        }
      });
      hlsInstance = hls;

      return () => {
        hls.destroy();
        if (hlsInstance === hls) hlsInstance = null;
      };
    } else if (videoEl.canPlayType('application/vnd.apple.mpegurl')) {
      videoEl.src = hlsUrl;
    } else {
      error = 'Your browser does not support HLS playback';
    }
  });
</script>

<div class="relative w-full">

  <div class="relative w-full bg-black aspect-video">

    {#if loading}
      <div class="absolute inset-0 flex flex-col items-center justify-center bg-black/90 z-30">
        <div class="relative flex items-center justify-center">
          <div class="w-14 h-14 border-2 border-zinc-800 rounded-full absolute"></div>
          <div class="w-14 h-14 border-2 border-t-red-500 border-r-transparent border-b-transparent border-l-transparent rounded-full animate-spin"></div>
        </div>
        <p class="text-zinc-500 text-xs font-semibold tracking-widest uppercase mt-4">Loading Stream</p>
      </div>
    {/if}

    {#if error}
      <div class="absolute inset-0 flex flex-col items-center justify-center bg-black/95 p-6 text-center z-30">
        <div class="w-12 h-12 rounded-full bg-red-500/10 border border-red-500/20 flex items-center justify-center text-red-500 mb-3">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-6 h-6">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z" />
          </svg>
        </div>
        <p class="text-zinc-400 text-sm">{error}</p>
      </div>
    {/if}

    <video
      bind:this={videoEl}
      controls
      autoplay={autoPlay}
      class="w-full h-full object-contain bg-black focus:outline-none"
      title={title}
      playsinline
    >
      <p class="text-zinc-500 text-center p-4 text-sm">Your browser does not support HLS playback.</p>
    </video>

  </div>
</div>
