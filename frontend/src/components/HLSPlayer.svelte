<script lang="ts">
  import Hls from 'hls.js';

  let { src = '', title = 'Video Player', autoPlay = false, server = 'white' } = $props();

  let videoEl: HTMLVideoElement;
  let containerEl: HTMLDivElement;
  let hlsInstance: Hls | null = null;
  let hlsUrl = $state('');
  let loading = $state(true);
  let error = $state('');

  let playing = $state(false);
  let ended = $state(false);
  let currentTime = $state(0);
  let duration = $state(0);
  let buffered = $state(0);
  let volume = $state(1);
  let muted = $state(false);
  let isFullscreen = $state(false);
  let showControls = $state(true);
  let hideTimer: ReturnType<typeof setTimeout> | null = null;

  let seeking = $state(false);
  let seekPreview = $state(0);
  let seekPos = $state(0);

  let progressBar: HTMLDivElement;

  function formatTime(t: number): string {
    if (!t || !isFinite(t)) return '0:00';
    const h = Math.floor(t / 3600);
    const m = Math.floor((t % 3600) / 60);
    const s = Math.floor(t % 60);
    if (h > 0) return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
    return `${m}:${String(s).padStart(2, '0')}`;
  }

  function togglePlay() {
    if (!videoEl) return;
    if (videoEl.paused) {
      videoEl.play().catch(() => {});
    } else {
      videoEl.pause();
    }
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
    if (e.key === ' ' || e.key === 'k') { e.preventDefault(); togglePlay(); }
    if (e.key === 'f') { e.preventDefault(); toggleFullscreen(); }
    if (e.key === 'm') { e.preventDefault(); toggleMute(); }
    if (e.key === 'ArrowRight') { if (videoEl) videoEl.currentTime = Math.min(videoEl.currentTime + 10, duration); }
    if (e.key === 'ArrowLeft') { if (videoEl) videoEl.currentTime = Math.max(videoEl.currentTime - 10, 0); }
  }

  function toggleFullscreen() {
    if (!containerEl) return;
    if (document.fullscreenElement) {
      document.exitFullscreen();
    } else {
      containerEl.requestFullscreen();
    }
  }

  function toggleMute() {
    if (!videoEl) return;
    videoEl.muted = !videoEl.muted;
  }

  function seek(e: MouseEvent) {
    if (!progressBar || !duration) return;
    const rect = progressBar.getBoundingClientRect();
    const pct = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    if (videoEl) videoEl.currentTime = pct * duration;
  }

  function handleProgressClick(e: MouseEvent) {
    seek(e);
  }

  function handleProgressMove(e: MouseEvent) {
    if (!progressBar || !duration) return;
    const rect = progressBar.getBoundingClientRect();
    const pct = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    seekPreview = pct * duration;
    seekPos = pct * 100;
  }

  function showControlsTemp() {
    showControls = true;
    if (hideTimer) clearTimeout(hideTimer);
    if (playing && !videoEl?.paused) {
      hideTimer = setTimeout(() => { showControls = false; }, 3000);
    }
  }

  $effect(() => {
    const v = videoEl;
    if (!v) return;

    const onTime = () => { currentTime = v.currentTime; ended = v.ended; };
    const onMeta = () => { duration = v.duration; };
    const onPlay = () => { playing = true; ended = false; showControlsTemp(); };
    const onPause = () => { playing = false; showControls = true; if (hideTimer) clearTimeout(hideTimer); };
    const onVol = () => { volume = v.volume; muted = v.muted; };
    const onEnd = () => { ended = true; playing = false; showControls = true; };
    const onFullscreenChange = () => { isFullscreen = !!document.fullscreenElement; };

    v.addEventListener('timeupdate', onTime);
    v.addEventListener('loadedmetadata', onMeta);
    v.addEventListener('play', onPlay);
    v.addEventListener('pause', onPause);
    v.addEventListener('volumechange', onVol);
    v.addEventListener('ended', onEnd);
    v.addEventListener('progress', () => {
      if (v.buffered.length > 0) buffered = v.buffered.end(v.buffered.length - 1);
    });
    document.addEventListener('fullscreenchange', onFullscreenChange);
    document.addEventListener('keydown', handleKeydown);

    return () => {
      v.removeEventListener('timeupdate', onTime);
      v.removeEventListener('loadedmetadata', onMeta);
      v.removeEventListener('play', onPlay);
      v.removeEventListener('pause', onPause);
      v.removeEventListener('volumechange', onVol);
      v.removeEventListener('ended', onEnd);
      document.removeEventListener('fullscreenchange', onFullscreenChange);
      document.removeEventListener('keydown', handleKeydown);
    };
  });

  $effect(() => {
    if (!hlsUrl || !videoEl) return;

    if (hlsInstance) {
      hlsInstance.destroy();
      hlsInstance = null;
    }

    if (Hls.isSupported()) {
      const hls = new Hls({ startPosition: 0 });
      hls.loadSource(hlsUrl);
      hls.attachMedia(videoEl);
      hls.on(Hls.Events.MANIFEST_PARSED, () => {
        if (autoPlay) videoEl.play().catch(() => {});
      });
      hls.on(Hls.Events.ERROR, (_event, data) => {
        if (data.fatal) { error = 'Stream connection interrupted'; }
      });
      hlsInstance = hls;
      return () => { hls.destroy(); if (hlsInstance === hls) hlsInstance = null; };
    } else if (videoEl.canPlayType('application/vnd.apple.mpegurl')) {
      videoEl.src = hlsUrl;
    } else {
      error = 'Your browser does not support HLS playback';
    }
  });

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
      .then(r => { if (!r.ok) throw new Error('Fetch failed'); return r.json(); })
      .then(data => {
        if (cancelled) return;
        if (data.sources?.length) {
          hlsUrl = `/api/${server}/proxy/hls?url=${encodeURIComponent(data.sources[0].url)}`;
        } else {
          error = 'No stream sources available';
        }
      })
      .catch(() => { if (!cancelled) error = 'Failed to establish stable stream path'; })
      .finally(() => { if (!cancelled) loading = false; });
    return () => { cancelled = true; };
  });

  let progressPct = $derived(duration > 0 ? (currentTime / duration) * 100 : 0);
  let bufferedPct = $derived(duration > 0 ? (buffered / duration) * 100 : 0);
  let volPct = $derived(muted ? 0 : volume * 100);
</script>

<svelte:window onmousemove={showControlsTemp} />

<div
  bind:this={containerEl}
  class="relative w-full bg-black select-none group cursor-pointer"
  class:fullscreen={isFullscreen}
  role="application"
  aria-label="Video Player"
>
  <div class="relative w-full aspect-video bg-black overflow-hidden">

    <video
      bind:this={videoEl}
      autoplay={autoPlay}
      class="w-full h-full object-contain bg-black"
      title={title}
      playsinline
      preload="metadata"
      onclick={togglePlay}
    >
      <p class="text-zinc-500 text-center p-4 text-sm">Your browser does not support HLS playback.</p>
    </video>

    {#if loading}
      <div class="absolute inset-0 flex items-center justify-center bg-black/90 z-20">
        <div class="w-12 h-12 border-2 border-zinc-700 rounded-full absolute"></div>
        <div class="w-12 h-12 border-2 border-t-red-500 border-r-transparent border-b-transparent border-l-transparent rounded-full animate-spin"></div>
      </div>
    {/if}

    {#if error}
      <div class="absolute inset-0 flex items-center justify-center bg-black/95 p-6 z-20">
        <div class="text-center">
          <div class="w-10 h-10 rounded-full bg-red-500/10 border border-red-500/20 flex items-center justify-center text-red-500 mx-auto mb-3">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-5 h-5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z" />
            </svg>
          </div>
          <p class="text-zinc-400 text-sm">{error}</p>
        </div>
      </div>
    {/if}

    {#if !playing && !loading && !error}
      <div class="absolute inset-0 flex items-center justify-center z-10 cursor-pointer" onclick={togglePlay}>
        <div class="w-16 h-16 rounded-full bg-white/10 backdrop-blur flex items-center justify-center hover:bg-white/20 transition-all active:scale-95">
          {#if ended}
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="w-7 h-7 text-white ml-0.5">
              <path fill-rule="evenodd" d="M4.5 5.653c0-1.426 1.529-2.33 2.779-1.643l11.54 6.347c1.295.712 1.295 2.573 0 3.286L7.28 19.99c-1.25.687-2.779-.218-2.779-1.643V5.653Z" clip-rule="evenodd" />
            </svg>
          {:else}
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="w-7 h-7 text-white ml-0.5">
              <path fill-rule="evenodd" d="M4.5 5.653c0-1.426 1.529-2.33 2.779-1.643l11.54 6.347c1.295.712 1.295 2.573 0 3.286L7.28 19.99c-1.25.687-2.779-.218-2.779-1.643V5.653Z" clip-rule="evenodd" />
            </svg>
          {/if}
        </div>
      </div>
    {/if}

    {#if showControls || !playing}
      <div class="absolute inset-0 z-10 flex flex-col justify-end opacity-0 group-hover:opacity-100 transition-opacity duration-300"
        class:opacity-100={!playing}
      >
        <div class="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent pointer-events-none"></div>
      </div>

      <div class="absolute bottom-0 left-0 right-0 z-20 transition-opacity duration-300
        {showControls || !playing ? 'opacity-100' : 'opacity-0'}"
        onmouseenter={showControlsTemp}
      >
        <div class="px-3 pb-2 pt-8 bg-gradient-to-t from-black/80 via-black/40 to-transparent">
          <div
            bind:this={progressBar}
            class="relative w-full h-1 group/progress cursor-pointer mb-3"
            onmousedown={handleProgressClick}
            onmousemove={handleProgressMove}
          >
            <div class="absolute inset-0 bg-white/20 rounded-full"></div>
            <div class="absolute inset-y-0 left-0 bg-white/30 rounded-full" style="width: {bufferedPct}%"></div>
            <div class="absolute inset-y-0 left-0 bg-red-600 rounded-full group-hover/progress:bg-red-500 transition-colors" style="width: {progressPct}%"></div>
            <div class="absolute top-1/2 -translate-y-1/2 w-3 h-3 bg-red-600 rounded-full opacity-0 group-hover/progress:opacity-100 transition-all shadow" style="left: calc({progressPct}% - 6px)"></div>
          </div>

          <div class="flex items-center justify-between gap-2 text-white">
            <div class="flex items-center gap-2">
              <button onclick={togglePlay} class="w-8 h-8 flex items-center justify-center hover:bg-white/10 rounded-full transition-colors active:scale-95" aria-label={playing ? 'Pause' : 'Play'}>
                {#if playing}
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="w-5 h-5">
                    <path fill-rule="evenodd" d="M6.75 5.25a.75.75 0 0 1 .75-.75H9a.75.75 0 0 1 .75.75v13.5a.75.75 0 0 1-.75.75H7.5a.75.75 0 0 1-.75-.75V5.25Zm7.5 0A.75.75 0 0 1 15 5.25h1.5a.75.75 0 0 1 .75.75v13.5a.75.75 0 0 1-.75.75H15a.75.75 0 0 1-.75-.75V5.25Z" clip-rule="evenodd" />
                  </svg>
                {:else}
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="w-5 h-5">
                    <path fill-rule="evenodd" d="M4.5 5.653c0-1.426 1.529-2.33 2.779-1.643l11.54 6.347c1.295.712 1.295 2.573 0 3.286L7.28 19.99c-1.25.687-2.779-.218-2.779-1.643V5.653Z" clip-rule="evenodd" />
                  </svg>
                {/if}
              </button>

              <span class="text-[13px] font-medium text-white/90 tracking-wide tabular-nums min-w-[90px]">
                {formatTime(currentTime)} / {formatTime(duration)}
              </span>
            </div>

            <div class="flex items-center gap-1">
              <button onclick={toggleMute} class="w-8 h-8 flex items-center justify-center hover:bg-white/10 rounded-full transition-colors active:scale-95" aria-label={muted ? 'Unmute' : 'Mute'}>
                {#if muted || volume === 0}
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="w-5 h-5">
                    <path d="M13.5 4.06c0-1.336-1.616-2.005-2.56-1.06l-4.5 4.5H4.508c-1.141 0-2.318.664-2.66 1.905A9.76 9.76 0 0 0 1.5 12c0 .898.121 1.768.35 2.595.341 1.24 1.518 1.905 2.659 1.905h1.93l4.5 4.5c.945.945 2.561.276 2.561-1.06V4.06ZM17.78 9.22a.75.75 0 1 0-1.06 1.06L18.44 12l-1.72 1.72a.75.75 0 1 0 1.06 1.06l1.72-1.72 1.72 1.72a.75.75 0 1 0 1.06-1.06L20.56 12l1.72-1.72a.75.75 0 1 0-1.06-1.06l-1.72 1.72-1.72-1.72Z" />
                  </svg>
                {:else if volume < 0.5}
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="w-5 h-5">
                    <path d="M11.553 3.064c-1.307-1.307-3.553-.383-3.553 1.464v13.944c0 1.847 2.246 2.771 3.553 1.464l4.416-4.416a2 2 0 0 0 .586-1.414v-1.628a2 2 0 0 0-.586-1.414l-4.416-4.416Z" />
                    <path fill-rule="evenodd" d="M15.62 8.002a.75.75 0 0 1 1.06.008 6.73 6.73 0 0 1 0 7.98.75.75 0 1 1-1.068-1.052 5.23 5.23 0 0 0 0-5.876.75.75 0 0 1 .008-1.06Z" clip-rule="evenodd" />
                  </svg>
                {:else}
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="w-5 h-5">
                    <path d="M11.553 3.064c-1.307-1.307-3.553-.383-3.553 1.464v13.944c0 1.847 2.246 2.771 3.553 1.464l4.416-4.416a2 2 0 0 0 .586-1.414v-1.628a2 2 0 0 0-.586-1.414l-4.416-4.416Z" />
                    <path fill-rule="evenodd" d="M16.434 6.343a.75.75 0 0 1 1.06 0 9.001 9.001 0 0 1 0 12.728.75.75 0 0 1-1.06-1.06 7.502 7.502 0 0 0 0-10.607.75.75 0 0 1 0-1.061Z" clip-rule="evenodd" />
                  </svg>
                {/if}
              </button>

              <div class="hidden sm:flex items-center w-0 group-hover/player:w-20 overflow-hidden transition-all duration-200">
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={volPct}
                  oninput={(e) => { if (videoEl) { videoEl.volume = Number(e.currentTarget.value) / 100; videoEl.muted = videoEl.volume === 0; } }}
                  class="w-full h-1 appearance-none bg-white/30 rounded-full cursor-pointer accent-red-600
                    [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-3 [&::-webkit-slider-thumb]:h-3 [&::-webkit-slider-thumb]:bg-white [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:shadow"
                />
              </div>

              <button onclick={toggleFullscreen} class="w-8 h-8 flex items-center justify-center hover:bg-white/10 rounded-full transition-colors active:scale-95" aria-label={isFullscreen ? 'Exit fullscreen' : 'Fullscreen'}>
                {#if isFullscreen}
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="w-5 h-5">
                    <path fill-rule="evenodd" d="M3.22 3.22a.75.75 0 0 1 1.06 0l3.97 3.97V4.5a.75.75 0 0 1 1.5 0V9a.75.75 0 0 1-.75.75H4.5a.75.75 0 0 1 0-1.5h2.69L3.22 4.28a.75.75 0 0 1 0-1.06Zm17.56 0a.75.75 0 0 1 0 1.06l-3.97 3.97h2.69a.75.75 0 0 1 0 1.5H15a.75.75 0 0 1-.75-.75V4.5a.75.75 0 0 1 1.5 0v2.69l3.97-3.97a.75.75 0 0 1 1.06 0ZM3.75 15a.75.75 0 0 1 .75-.75H9a.75.75 0 0 1 .75.75v4.5a.75.75 0 0 1-1.5 0v-2.69l-3.97 3.97a.75.75 0 0 1-1.06-1.06l3.97-3.97H4.5a.75.75 0 0 1-.75-.75Zm10.5 0a.75.75 0 0 1 .75-.75h4.5a.75.75 0 0 1 0 1.5h-2.69l3.97 3.97a.75.75 0 1 1-1.06 1.06l-3.97-3.97v2.69a.75.75 0 0 1-1.5 0V15Z" clip-rule="evenodd" />
                  </svg>
                {:else}
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="w-5 h-5">
                    <path fill-rule="evenodd" d="M4.5 3.75a.75.75 0 0 0-.75.75v4.5a.75.75 0 0 0 1.5 0V5.69l3.97 3.97a.75.75 0 1 0 1.06-1.06L5.69 4.5h2.56a.75.75 0 0 0 0-1.5H4.5Zm13.56 0a.75.75 0 0 0-.75.75v2.56l-3.97-3.97a.75.75 0 1 0-1.06 1.06l3.97 3.97H13.5a.75.75 0 0 0 0 1.5H19.5a.75.75 0 0 0 .75-.75V4.5a.75.75 0 0 0-.75-.75h-1.44Zm-16.5 15a.75.75 0 0 0 .75.75H9a.75.75 0 0 0 0-1.5H5.69l3.97-3.97a.75.75 0 1 0-1.06-1.06L4.5 17.31V14.5a.75.75 0 0 0-1.5 0v4.5a.75.75 0 0 0 .06.25Zm16.5 0a.75.75 0 0 0 .75.75h1.44a.75.75 0 0 0 .75-.75V14.5a.75.75 0 0 0-1.5 0v2.56l-3.97-3.97a.75.75 0 1 0-1.06 1.06l3.97 3.97H14.5a.75.75 0 0 0 0 1.5H18.5a.75.75 0 0 0 .56-.25Z" clip-rule="evenodd" />
                  </svg>
                {/if}
              </button>
            </div>
          </div>
        </div>
      </div>
    {/if}
  </div>
</div>

<style>
  .fullscreen {
    position: fixed !important;
    inset: 0 !important;
    z-index: 9999 !important;
    background: black !important;
    width: 100vw !important;
    height: 100vh !important;
  }
  .fullscreen video {
    width: 100%;
    height: 100%;
  }
  :global(input[type='range']) {
    -webkit-appearance: none;
    appearance: none;
    background: transparent;
    cursor: pointer;
  }
</style>
