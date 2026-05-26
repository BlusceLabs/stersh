<script lang="ts">
  import Hls from 'hls.js';

  let { src = '', title = 'Video Player', autoPlay = false } = $props();

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
          hlsUrl = `/api/black/proxy/hls?url=${encodeURIComponent(rawUrl)}`;
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
      const hls = new Hls();
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

<div class="relative w-full max-w-5xl mx-auto group/player select-none">

  <div class="absolute -inset-4 bg-gradient-to-tr from-red-600/20 via-purple-600/10 to-transparent rounded-[2rem] blur-3xl opacity-40 group-hover/player:opacity-60 transition-opacity duration-700 pointer-events-none z-0"></div>

  <div class="relative z-10 w-full bg-zinc-950 rounded-2xl overflow-hidden border border-zinc-800/60 shadow-2xl shadow-black/80 aspect-video">

    {#if loading}
      <div class="absolute inset-0 flex flex-col items-center justify-center bg-zinc-950/90 backdrop-blur-md z-30">
        <div class="relative flex items-center justify-center">
          <div class="w-16 h-16 border-2 border-zinc-800 rounded-full absolute"></div>
          <div class="w-16 h-16 border-2 border-t-red-500 border-r-pink-500/30 border-b-transparent border-l-transparent rounded-full animate-spin"></div>
        </div>
        <p class="text-zinc-400 font-medium text-sm tracking-wider mt-4 animate-pulse">OPTIMIZING STREAM</p>
      </div>
    {/if}

    {#if error}
      <div class="absolute inset-0 flex flex-col items-center justify-center bg-zinc-950/95 backdrop-blur-md p-6 text-center z-30">
        <div class="w-12 h-12 rounded-full bg-red-500/10 border border-red-500/20 flex items-center justify-center text-red-500 mb-3.5">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-6 h-6">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z" />
          </svg>
        </div>
        <h4 class="text-zinc-200 font-semibold text-base mb-1">Playback Interrupted</h4>
        <p class="text-zinc-500 text-sm max-w-sm">{error}</p>
      </div>
    {/if}

    <video
      bind:this={videoEl}
      controls
      autoplay={autoPlay}
      class="w-full h-full object-contain bg-black transition-all duration-500 focus:outline-none"
      title={title}
    >
      <p class="text-white text-center p-4">Your platform architecture does not support inline HLS stream execution.</p>
    </video>

    <div class="absolute top-4 left-4 z-20 pointer-events-none opacity-0 group-hover/player:opacity-100 transition-opacity duration-300 transform translate-y-[-4px] group-hover/player:translate-y-0">
      <div class="bg-zinc-950/70 backdrop-blur-md px-3.5 py-1.5 rounded-xl border border-zinc-800/40 shadow-xl">
        <span class="text-xs font-semibold text-zinc-300 tracking-wide uppercase">{title}</span>
      </div>
    </div>

  </div>
</div>
