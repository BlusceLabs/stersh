<script lang="ts">
  import Hls from 'hls.js';

  // Props (Svelte 5 Runes)
  let { 
    src = '', 
    title = 'Video Player', 
    autoPlay = false, 
    server = 'white',
    startTime = 0,
    onNext = undefined,
    onPrev = undefined,
    onProgress = undefined
  }: {
    src?: string;
    title?: string;
    autoPlay?: boolean;
    server?: string;
    startTime?: number;
    onNext?: () => void;
    onPrev?: () => void;
    onProgress?: (data: { currentTime: number; duration: number }) => void;
  } = $props();

  // Elements & Instances
  let videoEl: HTMLVideoElement;
  let containerEl: HTMLDivElement;
  let progressBar: HTMLDivElement;
  let hlsInstance: Hls | null = null;

  // Player State Runes
  let hlsUrl = $state('');
  let loading = $state(true);
  let error = $state('');
  let fetchKey = $state(0);
  const MAX_RETRIES = 3;
  let playing = $state(false);
  let ended = $state(false);
  let currentTime = $state(0);
  let duration = $state(0);
  let buffered = $state(0);
  let volume = $state(1);
  let muted = $state(false);
  let isFullscreen = $state(false);
  let showControls = $state(true);
  let supportsPiP = $state(false);
  let isPiP = $state(false);

  // Video.js Feature Extension Runes
  let playbackRate = $state(1);
  let showSettings = $state(false);
  let currentMenuTab = $state<'main' | 'quality' | 'speed' | 'captions'>('main');
  
  type QualityLevel = { index: number; label: string };
  let qualities = $state<QualityLevel[]>([]);
  let currentQualityIndex = $state<number>(-1); // -1 is Auto

  type CaptionTrack = { index: number; label: string; language: string; trackObj: TextTrack };
  let captions = $state<CaptionTrack[]>([]);
  let currentCaptionIndex = $state<number>(-1); // -1 is Off

  // Timeline Hover & Scrubbing State Runes
  let isScrubbing = $state(false);
  let showPreview = $state(false);
  let seekPreview = $state(0);
  let seekPos = $state(0);
  let hideTimer: ReturnType<typeof setTimeout> | null = null;

  // Auto-advance countdown state
  let countdown = $state(0);
  let countdownTimer: ReturnType<typeof setInterval> | null = null;

  function startCountdown(seconds: number = 10) {
    countdown = seconds;
    if (countdownTimer) clearInterval(countdownTimer);
    countdownTimer = setInterval(() => {
      countdown -= 1;
      if (countdown <= 0) {
        if (countdownTimer) clearInterval(countdownTimer);
        countdownTimer = null;
        if (onNext) onNext();
      }
    }, 1000);
  }

  function cancelCountdown() {
    if (countdownTimer) clearInterval(countdownTimer);
    countdownTimer = null;
    countdown = 0;
  }

  // Playback Rate Options
  const speedOptions = [0.5, 0.75, 1, 1.25, 1.5, 2];

  // Helper: Format seconds into clean strings
  function formatTime(t: number): string {
    if (!t || !isFinite(t)) return '0:00';
    const h = Math.floor(t / 3600);
    const m = Math.floor((t % 3600) / 60);
    const s = Math.floor(t % 60);
    if (h > 0) return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
    return `${m}:${String(s).padStart(2, '0')}`;
  }

  // Core Playback Controls
  function togglePlay() {
    if (!videoEl) return;
    if (countdown > 0) { cancelCountdown(); }
    if (videoEl.paused) {
      videoEl.play().catch(() => {});
    } else {
      videoEl.pause();
    }
  }

  function skip(seconds: number) {
    if (!videoEl) return;
    videoEl.currentTime = Math.max(0, Math.min(videoEl.currentTime + seconds, duration));
  }

  function toggleFullscreen() {
    if (!containerEl) return;
    if (document.fullscreenElement) {
      document.exitFullscreen();
    } else {
      containerEl.requestFullscreen().catch(() => {});
    }
  }

  function toggleMute() {
    if (!videoEl) return;
    videoEl.muted = !videoEl.muted;
  }

  async function togglePiP() {
    if (!videoEl || !supportsPiP) return;
    try {
      if (document.pictureInPictureElement) {
        await document.exitPictureInPicture();
      } else {
        await videoEl.requestPictureInPicture();
      }
    } catch (err) {
      console.error(err);
    }
  }

  // Quality, Speed, and Captions Modifiers
  function changeSpeed(rate: number) {
    playbackRate = rate;
    if (videoEl) videoEl.playbackRate = rate;
    showSettings = false;
  }

  function changeQuality(index: number) {
    currentQualityIndex = index;
    if (hlsInstance) {
      hlsInstance.currentLevel = index; // -1 triggers adaptive auto resolution streaming logic
    }
    showSettings = false;
  }

  function changeCaption(index: number) {
    currentCaptionIndex = index;
    captions.forEach((cap) => {
      cap.trackObj.mode = cap.index === index ? 'showing' : 'disabled';
    });
    showSettings = false;
  }

  // Unified Scrubbing Math Helper
  function getTimelinePercentage(clientX: number): number {
    if (!progressBar) return 0;
    const rect = progressBar.getBoundingClientRect();
    return Math.max(0, Math.min(1, (clientX - rect.left) / rect.width));
  }

  function handleTimelineMouseDown(e: MouseEvent) {
    if (!duration || !videoEl) return;
    isScrubbing = true;
    showControlsTemp();
    const pct = getTimelinePercentage(e.clientX);
    videoEl.currentTime = pct * duration;
  }

  function handleTimelineMouseMove(e: MouseEvent) {
    if (!duration) return;
    showPreview = true;
    const pct = getTimelinePercentage(e.clientX);
    seekPreview = pct * duration;
    seekPos = pct * 100;

    if (isScrubbing && videoEl) {
      videoEl.currentTime = seekPreview;
    }
  }

  function handleGlobalMouseUp() {
    if (isScrubbing) {
      isScrubbing = false;
      showControlsTemp();
    }
  }

  // Accessibility Global Hotkeys
  function handleKeydown(e: KeyboardEvent) {
    if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
    
    const keyActions: Record<string, () => void> = {
      ' ': () => { e.preventDefault(); togglePlay(); },
      'k': () => { e.preventDefault(); togglePlay(); },
      'f': () => { e.preventDefault(); toggleFullscreen(); },
      'm': () => { e.preventDefault(); toggleMute(); },
      'p': () => { if (onPrev) { e.preventDefault(); onPrev(); } else { e.preventDefault(); togglePiP(); } },
      'n': () => { if (onNext) { e.preventDefault(); onNext(); } },
      'arrowright': () => { e.preventDefault(); skip(10); },
      'arrowleft': () => { e.preventDefault(); skip(-10); }
    };

    if (keyActions[e.key.toLowerCase()]) keyActions[e.key.toLowerCase()]();
  }

  function showControlsTemp() {
    showControls = true;
    if (hideTimer) clearTimeout(hideTimer);
    if (playing && !videoEl?.paused && !isScrubbing && !showSettings) {
      hideTimer = setTimeout(() => { showControls = false; }, 2800);
    }
  }

  // Sync state transitions when setting configuration layers are opened
  $effect(() => {
    if (showSettings) {
      if (hideTimer) clearTimeout(hideTimer);
    } else {
      currentMenuTab = 'main';
      showControlsTemp();
    }
  });

  // Lifecycle Effect: Element Node Event Hooks
  $effect(() => {
    const v = videoEl;
    if (!v) return;

    supportsPiP = document.pictureInPictureEnabled;

    const onTime = () => { currentTime = v.currentTime; ended = v.ended; };
    const onMeta = () => { duration = v.duration; };
    const onPlay = () => { playing = true; ended = false; showControlsTemp(); };
    const onPause = () => { playing = false; showControls = true; };
    const onVol = () => { volume = v.volume; muted = v.muted; };
    const onEnd = () => {
      ended = true; playing = false; showControls = true;
      if (onNext) startCountdown(10);
    };
    const onFullscreenChange = () => { isFullscreen = !!document.fullscreenElement; };
    const onEnterPiP = () => isPiP = true;
    const onLeavePiP = () => isPiP = false;

    // Track Parser for Subtitles/Captions
    const parseTracks = () => {
      const discoveredTracks: CaptionTrack[] = [];
      for (let i = 0; i < v.textTracks.length; i++) {
        const track = v.textTracks[i];
        if (track.kind === 'subtitles' || track.kind === 'captions') {
          discoveredTracks.push({
            index: i,
            label: track.label || track.language.toUpperCase() || `Track ${i + 1}`,
            language: track.language,
            trackObj: track
          });
          if (track.mode === 'showing') currentCaptionIndex = i;
        }
      }
      captions = discoveredTracks;
    };

    v.addEventListener('timeupdate', onTime);
    v.addEventListener('loadedmetadata', onMeta);
    v.addEventListener('play', onPlay);
    v.addEventListener('pause', onPause);
    v.addEventListener('volumechange', onVol);
    v.addEventListener('ended', onEnd);
    v.addEventListener('enterpictureinpicture', onEnterPiP);
    v.addEventListener('leavepictureinpicture', onLeavePiP);
    v.textTracks.addEventListener('addtrack', parseTracks);
    
    v.addEventListener('progress', () => {
      if (v.buffered.length > 0) buffered = v.buffered.end(v.buffered.length - 1);
    });

    document.addEventListener('fullscreenchange', onFullscreenChange);
    document.addEventListener('keydown', handleKeydown);
    window.addEventListener('mouseup', handleGlobalMouseUp);

    let progressInterval: ReturnType<typeof setInterval> | null = null;
    if (onProgress) {
      progressInterval = setInterval(() => {
        if (v.duration > 0) {
          onProgress({ currentTime: v.currentTime, duration: v.duration });
        }
      }, 15000);
    }

    return () => {
      if (progressInterval) clearInterval(progressInterval);
      v.removeEventListener('timeupdate', onTime);
      v.removeEventListener('loadedmetadata', onMeta);
      v.removeEventListener('play', onPlay);
      v.removeEventListener('pause', onPause);
      v.removeEventListener('volumechange', onVol);
      v.removeEventListener('ended', onEnd);
      v.removeEventListener('enterpictureinpicture', onEnterPiP);
      v.removeEventListener('leavepictureinpicture', onLeavePiP);
      v.textTracks.removeEventListener('addtrack', parseTracks);
      document.removeEventListener('fullscreenchange', onFullscreenChange);
      document.removeEventListener('keydown', handleKeydown);
      window.removeEventListener('mouseup', handleGlobalMouseUp);
    };
  });

  // Lifecycle Effect: Dynamic HLS Level Resolution Aggregation Core Engine
  $effect(() => {
    if (!hlsUrl || !videoEl) return;
    if (hlsInstance) { hlsInstance.destroy(); hlsInstance = null; }

    if (Hls.isSupported()) {
      const hls = new Hls({ startPosition: 0, capLevelToPlayerSize: true });
      hls.loadSource(hlsUrl);
      hls.attachMedia(videoEl);
      
      hls.on(Hls.Events.MANIFEST_PARSED, () => {
        qualities = [...hls.levels].reverse().map((lvl, index) => ({
          index,
          label: lvl.height ? `${lvl.height}p` : `Level ${index}`
        }));

        if (startTime > 0) {
          videoEl.currentTime = startTime;
        }
        if (autoPlay) videoEl.play().catch(() => {});
      });

      hls.on(Hls.Events.LEVEL_SWITCHED, (_, data) => {
        // Keeps the indicator perfectly synced if auto switching is operational
        if (hls.autoLevelEnabled) currentQualityIndex = -1;
      });

      hls.on(Hls.Events.ERROR, (_event, data) => {
        if (data.fatal) {
          const code = data.response?.code;
          if ((code === 404 || code === 410) && hlsRetries < MAX_RETRIES && src) {
            hlsRetries++;
            hlsUrl = '';
            fetchKey++;
            return;
          }
          error = 'Stream connection interrupted. Attempting recover...';
        }
      });

      hlsInstance = hls;
      return () => { hls.destroy(); if (hlsInstance === hls) hlsInstance = null; };
    } else if (videoEl.canPlayType('application/vnd.apple.mpegurl')) {
      videoEl.src = hlsUrl;
    } else {
      error = 'Adaptive streaming playback layer failure.';
    }
  });

  // Stream Endpoint Ingestion Layer (re-triggers on src change or retry via fetchKey)
  let prevSrc = $state('');
  $effect(() => {
    if (src && src !== prevSrc) { prevSrc = src; hlsRetries = 0; }
  });

  $effect(() => {
    fetchKey; if (!src) { hlsUrl = ''; return; }
    loading = true; error = ''; hlsUrl = '';
    let cancelled = false;

    fetch(src)
      .then(r => { if (!r.ok) throw new Error(); return r.json(); })
      .then(data => {
        if (cancelled) return;
        error = '';
        const master = data.master_url || (data.sources?.[0]?.url);
        if (master) {
          hlsUrl = `/api/${server}/proxy/hls?url=${encodeURIComponent(master)}`;
        } else {
          error = 'No structural streaming feeds available.';
        }
      })
      .catch(() => { if (!cancelled) error = 'Failed to establish stable streaming pipeline.'; })
      .finally(() => { if (!cancelled) loading = false; });

    return () => { cancelled = true; };
  });

  let progressPct = $derived(duration > 0 ? (currentTime / duration) * 100 : 0);
  let bufferedPct = $derived(duration > 0 ? (buffered / duration) * 100 : 0);
  let volPct = $derived(muted ? 0 : volume * 100);
  let activeQualityLabel = $derived(currentQualityIndex === -1 ? 'Auto' : qualities.find(q => q.index === currentQualityIndex)?.label || 'Auto');
  let activeCaptionLabel = $derived(currentCaptionIndex === -1 ? 'Off' : captions.find(c => c.index === currentCaptionIndex)?.label || 'Off');
  let hlsRetries = $state(0);
</script>

<svelte:window onmousemove={showControlsTemp} />

<div
  bind:this={containerEl}
  class="relative w-full bg-zinc-950 select-none group/player cursor-default overflow-hidden rounded-2xl border border-zinc-900/80 shadow-2xl transition-all duration-300"
  class:fullscreen={isFullscreen}
  role="application"
  aria-label="Premium Video Player"
>
  <div 
    class="relative w-full aspect-video bg-black overflow-hidden flex items-center justify-center"
    onmouseleave={() => { if (!isScrubbing) showSettings = false; }}
  >
    <video
      bind:this={videoEl}
      autoplay={autoPlay}
      class="w-full h-full object-contain bg-black cursor-pointer transition-opacity duration-300"
      class:opacity-40={loading || error}
      title={title}
      playsinline
      preload="metadata"
      onclick={togglePlay}
      ondblclick={toggleFullscreen}
    >
      <p class="text-zinc-500 text-center p-4 text-sm">Your browser does not support internal streaming layers.</p>
    </video>

    {#if loading}
      <div class="absolute inset-0 flex items-center justify-center bg-zinc-950/20 backdrop-blur-md z-20 pointer-events-none">
        <div class="relative w-14 h-14 flex items-center justify-center">
          <div class="w-14 h-14 border-[3px] border-zinc-800/60 rounded-full absolute"></div>
          <div class="w-14 h-14 border-[3px] border-t-red-500 border-r-transparent border-b-transparent border-l-transparent rounded-full animate-spin absolute"></div>
        </div>
      </div>
    {/if}

    {#if error}
      <div class="absolute inset-0 flex items-center justify-center bg-zinc-950/90 backdrop-blur-xl p-6 z-20 animate-fade-in">
        <div class="text-center max-w-sm">
          <div class="w-12 h-12 rounded-2xl bg-red-500/10 border border-red-500/20 flex items-center justify-center text-red-400 mx-auto mb-4 shadow-lg">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="22" height="22" color="currentColor" fill="none">
              <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="1.5" />
              <path d="M12 7V13" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
              <circle cx="12" cy="17" r="1" fill="currentColor" />
            </svg>
          </div>
          <p class="text-zinc-200 text-sm font-medium tracking-wide leading-relaxed px-4">{error}</p>
        </div>
      </div>
    {/if}

    {#if !playing && !loading && !error}
      <div class="absolute inset-0 flex items-center justify-center z-10 bg-black/10 backdrop-blur-[1px] cursor-pointer" onclick={togglePlay}>
        {#if ended && onNext && countdown > 0}
          <div class="flex flex-col items-center gap-4" onclick={(e) => e.stopPropagation()}>
            <div class="flex flex-col items-center gap-2">
              <p class="text-sm text-zinc-300 font-medium tracking-wide">Up Next</p>
              <p class="text-[56px] font-bold text-white tabular-nums leading-none">{countdown}</p>
              <p class="text-xs text-zinc-500">starting in...</p>
            </div>
            <div class="flex gap-3">
              <button onclick={togglePlay} class="px-5 py-2 bg-white/10 hover:bg-white/20 rounded-full text-sm font-semibold text-white transition-colors active:scale-95">
                <svg class="inline-block -mt-0.5 mr-1.5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="16" height="16" color="currentColor" fill="none">
                  <path d="M6.5 5.5L18.5 12L6.5 18.5V5.5Z" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" fill="currentColor" />
                </svg>
                Replay
              </button>
              <button onclick={cancelCountdown} class="px-5 py-2 bg-white/10 hover:bg-white/20 rounded-full text-sm font-semibold text-white transition-colors active:scale-95">
                Cancel
              </button>
            </div>
          </div>
        {:else if ended}
          <button class="w-16 h-16 rounded-full bg-zinc-900/80 hover:bg-zinc-800 border border-zinc-700/50 flex items-center justify-center backdrop-blur-xl shadow-2xl text-white transition-all scale-100 hover:scale-105 active:scale-95 duration-300">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" color="currentColor" fill="none">
              <path d="M19 12H5M5 12L10 7M5 12L10 17" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
          </button>
        {:else}
          <button class="w-16 h-16 rounded-full bg-zinc-900/80 hover:bg-zinc-800 border border-zinc-700/50 flex items-center justify-center backdrop-blur-xl shadow-2xl text-white transition-all scale-100 hover:scale-105 active:scale-95 duration-300">
            <svg class="translate-x-[1px]" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" color="currentColor" fill="none">
              <path d="M6.5 5.5L18.5 12L6.5 18.5V5.5Z" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" fill="currentColor" />
            </svg>
          </button>
        {/if}
      </div>
    {/if}

    {#if showSettings}
      <div class="absolute bottom-20 right-4 w-64 bg-zinc-900/95 border border-zinc-800/80 rounded-2xl shadow-2xl backdrop-blur-xl z-30 p-2 text-zinc-200 text-xs font-medium animate-fade-in" onmouseenter={showControlsTemp}>
        {#if currentMenuTab === 'main'}
          <div class="flex flex-col">
            {#if qualities.length > 0}
              <button onclick={() => currentMenuTab = 'quality'} class="flex items-center justify-between p-2.5 hover:bg-zinc-800 rounded-xl transition-colors">
                <span class="text-zinc-400">Quality</span>
                <span class="flex items-center gap-1 text-white">{activeQualityLabel} <span class="text-zinc-600">›</span></span>
              </button>
            {/if}
            <button onclick={() => currentMenuTab = 'speed'} class="flex items-center justify-between p-2.5 hover:bg-zinc-800 rounded-xl transition-colors">
              <span class="text-zinc-400">Speed</span>
              <span class="flex items-center gap-1 text-white">{playbackRate === 1 ? 'Normal' : playbackRate + 'x'} <span class="text-zinc-600">›</span></span>
            </button>
            {#if captions.length > 0}
              <button onclick={() => currentMenuTab = 'captions'} class="flex items-center justify-between p-2.5 hover:bg-zinc-800 rounded-xl transition-colors">
                <span class="text-zinc-400">Captions</span>
                <span class="flex items-center gap-1 text-white">{activeCaptionLabel} <span class="text-zinc-600">›</span></span>
              </button>
            {/if}
          </div>
        {:else}
          <div class="flex flex-col max-h-56 overflow-y-auto">
            <button onclick={() => currentMenuTab = 'main'} class="flex items-center gap-2 p-2 mb-1 font-semibold text-zinc-400 border-b border-zinc-800/60 pb-2 hover:text-white transition-colors">
              <span>‹</span> Back
            </button>
            
            {#if currentMenuTab === 'quality'}
              <button onclick={() => changeQuality(-1)} class="flex items-center justify-between p-2 hover:bg-zinc-800 rounded-lg text-left {currentQualityIndex === -1 ? 'text-red-400' : ''}">
                <span>Auto Adaptive</span>
                {#if currentQualityIndex === -1}<span>✓</span>{/if}
              </button>
              {#each qualities as q}
                <button onclick={() => changeQuality(q.index)} class="flex items-center justify-between p-2 hover:bg-zinc-800 rounded-lg text-left {currentQualityIndex === q.index ? 'text-red-400' : ''}">
                  <span>{q.label}</span>
                  {#if currentQualityIndex === q.index}<span>✓</span>{/if}
                </button>
              {/each}
            {:else if currentMenuTab === 'speed'}
              {#each speedOptions as speed}
                <button onclick={() => changeSpeed(speed)} class="flex items-center justify-between p-2 hover:bg-zinc-800 rounded-lg text-left {playbackRate === speed ? 'text-red-400' : ''}">
                  <span>{speed === 1 ? 'Normal' : speed + 'x'}</span>
                  {#if playbackRate === speed}<span>✓</span>{/if}
                </button>
              {/each}
            {:else if currentMenuTab === 'captions'}
              <button onclick={() => changeCaption(-1)} class="flex items-center justify-between p-2 hover:bg-zinc-800 rounded-lg text-left {currentCaptionIndex === -1 ? 'text-red-400' : ''}">
                <span>Off</span>
                {#if currentCaptionIndex === -1}<span>✓</span>{/if}
              </button>
              {#each captions as cap}
                <button onclick={() => changeCaption(cap.index)} class="flex items-center justify-between p-2 hover:bg-zinc-800 rounded-lg text-left {currentCaptionIndex === cap.index ? 'text-red-400' : ''}">
                  <span>{cap.label}</span>
                  {#if currentCaptionIndex === cap.index}<span>✓</span>{/if}
                </button>
              {/each}
            {/if}
          </div>
        {/if}
      </div>
    {/if}

    <div 
      class="absolute bottom-0 left-0 right-0 z-20 transition-all duration-300 ease-out flex flex-col justify-end px-4 pb-4 pt-24 bg-gradient-to-t from-black/90 via-black/40 to-transparent
      {showControls || !playing || isScrubbing ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4 pointer-events-none'}"
      onmouseenter={showControlsTemp}
    >
      <div class="w-full flex flex-col gap-4 px-2">
        
        <div
          bind:this={progressBar}
          class="relative w-full h-3 group/progress cursor-pointer flex items-center"
          onmousedown={handleTimelineMouseDown}
          onmousemove={handleTimelineMouseMove}
          onmouseleave={() => showPreview = false}
        >
          <div class="absolute left-0 right-0 h-1 bg-zinc-600/50 rounded-full transition-all group-hover/progress:h-1.5"></div>
          <div class="absolute h-1 bg-zinc-400/50 rounded-full transition-all group-hover/progress:h-1.5" style="width: {bufferedPct}%"></div>
          <div class="absolute h-1 bg-red-500 rounded-full transition-all group-hover/progress:h-1.5 shadow-[0_0_12px_rgba(239,68,68,0.4)]" style="width: {progressPct}%"></div>
          
          <div 
            class="absolute w-3 h-3 bg-white rounded-full shadow-2xl opacity-0 group-hover/progress:opacity-100 transition-all duration-150 pointer-events-none scale-75 group-hover/progress:scale-100" 
            style="left: calc({progressPct}% - 6px)"
          ></div>

          {#if showPreview && duration}
            <div 
              class="absolute bottom-6 -translate-x-1/2 bg-zinc-900/95 backdrop-blur border border-zinc-800 text-[11px] font-semibold px-2 py-0.5 rounded-lg shadow-2xl text-zinc-100 transition-all pointer-events-none whitespace-nowrap tracking-wider animate-fade-in"
              style="left: {seekPos}%"
            >
              {formatTime(seekPreview)}
            </div>
          {/if}
        </div>

        <div class="flex items-center justify-between gap-4 text-white">
          
          <div class="flex items-center gap-1">
            
            {#if onPrev}
              <button onclick={onPrev} class="w-9 h-9 flex items-center justify-center hover:bg-zinc-800/60 rounded-xl transition-all active:scale-95 text-zinc-300 hover:text-white" aria-label="Previous Episode">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="18" height="18" color="currentColor" fill="none">
                  <path d="M4 5V19M20 5L10 12L20 19V5Z" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" fill="currentColor" />
                </svg>
              </button>
            {/if}

            <button onclick={() => skip(-10)} class="w-9 h-9 flex items-center justify-center hover:bg-zinc-800/60 rounded-xl transition-all active:scale-95 text-zinc-300 hover:text-white" aria-label="Rewind 10 Seconds">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="18" height="18" color="currentColor" fill="none">
                <path d="M14 5L5 12L14 19V5Z" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" fill="currentColor" />
                <path d="M20 6L13 12L20 18V6Z" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" fill="currentColor" />
              </svg>
            </button>

            <button onclick={togglePlay} class="w-9 h-9 flex items-center justify-center hover:bg-zinc-800/60 rounded-xl transition-all active:scale-95 text-zinc-100 hover:text-white" aria-label={playing ? 'Pause' : 'Play'}>
              {#if playing}
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="18" height="18" color="currentColor" fill="none">
                  <path d="M7 4V20M17 4V20" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
                </svg>
              {:else}
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="18" height="18" color="currentColor" fill="none">
                  <path d="M6.5 5.5L18.5 12L6.5 18.5V5.5Z" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" fill="currentColor" />
                </svg>
              {/if}
            </button>

            <button onclick={() => skip(10)} class="w-9 h-9 flex items-center justify-center hover:bg-zinc-800/60 rounded-xl transition-all active:scale-95 text-zinc-300 hover:text-white" aria-label="Forward 10 Seconds">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="18" height="18" color="currentColor" fill="none">
                <path d="M10 19L19 12L10 5V19Z" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" fill="currentColor" />
                <path d="M4 18L11 12L4 6V18Z" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" fill="currentColor" />
              </svg>
            </button>

            {#if onNext}
              <button onclick={onNext} class="w-9 h-9 flex items-center justify-center hover:bg-zinc-800/60 rounded-xl transition-all active:scale-95 text-zinc-300 hover:text-white" aria-label="Next Episode">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="18" height="18" color="currentColor" fill="none">
                  <path d="M20 5V19M4 5L14 12L4 19V5Z" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" fill="currentColor" />
                </svg>
              </button>
            {/if}

            <span class="text-[12px] font-medium text-zinc-300 tracking-wider tabular-nums ml-3 drop-shadow-md">
              {formatTime(currentTime)} <span class="text-zinc-500 font-normal px-1">/</span> {formatTime(duration)}
            </span>
          </div>

          <div class="flex items-center gap-1">
            
            <div class="flex items-center gap-0.5 group/volume">
              <button onclick={toggleMute} class="w-9 h-9 flex items-center justify-center hover:bg-zinc-800/60 rounded-xl transition-all active:scale-95 text-zinc-300 hover:text-white" aria-label={muted ? 'Unmute' : 'Mute'}>
                {#if muted || volume === 0}
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="18" height="18" color="currentColor" fill="none">
                    <path d="M2 9V15H6L11 20V4L6 9H2Z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round" />
                    <path d="M16 10L20 14M20 10L16 14" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
                  </svg>
                {:else}
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="18" height="18" color="currentColor" fill="none">
                    <path d="M2 9V15H6L11 20V4L6 9H2Z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round" />
                    <path d="M15.5 8.5C16.5 9.5 16.5 11.5 15.5 12.5M18.5 6C20.5 8 20.5 14 18.5 16" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" />
                  </svg>
                {/if}
              </button>

              <div class="w-0 overflow-hidden group-hover/player:w-16 group-hover/volume:w-16 transition-all duration-300 ease-out flex items-center pr-2">
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={volPct}
                  oninput={(e) => { if (videoEl) { videoEl.volume = Number(e.currentTarget.value) / 100; videoEl.muted = videoEl.volume === 0; } }}
                  class="w-full h-1 appearance-none bg-zinc-600/60 rounded-full cursor-pointer accent-white focus:outline-none"
                />
              </div>
            </div>

            <button onclick={() => showSettings = !showSettings} class="w-9 h-9 flex items-center justify-center hover:bg-zinc-800/60 rounded-xl transition-all active:scale-95 text-zinc-300 hover:text-white" class:text-white={showSettings} aria-label="Player Settings">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="18" height="18" color="currentColor" fill="none">
                <path d="M12 15C13.6569 15 15 13.6569 15 12C15 10.3431 13.6569 9 12 9C10.3431 9 9 10.3431 9 12C9 13.6569 10.3431 15 12 15Z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round" />
                <path d="M19.6196 9.77124C19.8243 10.5181 20 11.2372 20 12C20 12.7628 19.8243 13.4819 19.6196 14.2288C19.5005 14.6633 19.441 14.8805 19.4891 15.0934C19.5372 15.3063 19.6841 15.4741 19.9778 15.8098C20.5516 16.4659 20.8385 16.794 20.8037 17.164C20.7688 17.534 20.4187 17.8841 19.7186 18.5843L18.5843 19.7186C17.8841 20.4187 17.534 20.7688 17.164 20.8037C16.794 20.8385 16.4659 20.5516 15.8098 19.9778C15.4741 19.6841 15.3063 19.5372 15.0934 19.4891C14.8805 19.441 14.6633 19.5005 14.2288 19.6196C13.4819 19.8243 12.7628 20 12 20C11.2372 20 10.5181 19.8243 9.77124 19.6196C9.33671 19.5005 9.11945 19.441 8.90656 19.4891C8.69366 19.5372 8.52589 19.6841 8.19017 19.9778C7.53406 20.5516 7.20601 20.8385 6.83603 20.8037C6.46604 20.7688 6.11593 20.4187 5.41571 19.7186L4.28138 18.5843C3.58116 17.8841 3.23105 17.534 3.19622 17.164C3.16139 16.794 3.44836 16.4659 4.02221 15.8098C4.31593 15.4741 4.46279 15.3063 4.51089 15.0934C4.55899 14.8805 4.49947 14.6633 4.38043 14.2288C4.17572 13.4819 4 12.7628 4 12C4 11.2372 4.17572 10.5181 4.38043 9.77124C4.49947 9.33671 4.55899 9.11945 4.51089 8.90656C4.46279 8.69366 4.31593 8.52589 4.02221 8.19017C3.44836 7.53406 3.16139 7.20601 3.19622 6.83603C3.23105 6.46604 3.58116 6.11593 4.28138 5.41571L5.41571 4.28138C6.11593 3.58116 6.46604 3.23105 6.83603 3.19622C7.20601 3.16139 7.53406 3.44836 8.19017 4.02221C8.52589 4.31593 8.69366 4.46279 8.90656 4.51089C9.11945 4.55899 9.33671 4.49947 9.77124 4.38043C10.5181 4.17572 11.2372 4 12 4C12.7628 4 13.4819 4.17572 14.2288 4.38043C14.6633 4.48126 14.8805 4.53167 15.0934 4.48358C15.3063 4.43548 15.4741 4.29367 15.8098 4.01005C16.4659 3.45607 16.794 3.17908 17.164 3.21271C17.534 3.24635 17.8841 3.58434 18.5843 4.26033L19.7186 5.35824C20.4187 6.03423 20.7688 6.37222 20.8037 6.72945C20.8385 7.08668 20.5516 7.40334 19.9778 8.03666C19.6841 8.36142 19.5372 8.52379 19.4891 8.72932C19.441 8.93484 19.5005 9.14457 19.6196 9.77124Z" stroke="currentColor" stroke-width="1.5" />
              </svg>
            </button>

            {#if supportsPiP}
              <button onclick={togglePiP} class="w-9 h-9 flex items-center justify-center hover:bg-zinc-800/60 rounded-xl transition-all active:scale-95 text-zinc-300 hover:text-white" class:text-red-400={isPiP} aria-label="Picture-in-Picture">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="18" height="18" color="currentColor" fill="none">
                  <path d="M3 5C3 3.89543 3.89543 3 5 3H19C20.1046 3 21 3.89543 21 5V13C21 14.1046 20.1046 15 19 15H13V19C13 20.1046 12.1046 21 11 21H5C3.89543 21 3 20.1046 3 19V5Z" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
                  <rect x="13" y="13" width="8" height="6" rx="1" stroke="currentColor" stroke-width="1.5" fill="currentColor" fill-opacity="0.1" />
                </svg>
              </button>
            {/if}

            <button onclick={toggleFullscreen} class="w-9 h-9 flex items-center justify-center hover:bg-zinc-800/60 rounded-xl transition-all active:scale-95 text-zinc-300 hover:text-white" aria-label={isFullscreen ? 'Exit fullscreen' : 'Fullscreen'}>
              {#if isFullscreen}
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="18" height="18" color="currentColor" fill="none">
                  <path d="M4 14H10M10 14V20M10 14L3 21M20 10H14M14 10V4M14 10L21 3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
                </svg>
              {:else}
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="18" height="18" color="currentColor" fill="none">
                  <path d="M9 3H4C3.44772 3 3 3.44772 3 4V9M15 3H20C20.5523 3 21 3.44772 21 4V9M9 21H4C3.44772 21 3 20.5523 3 20V15M15 21H20C20.5523 21 21 20.5523 21 20V15" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
                </svg>
              {/if}
            </button>
          </div>

        </div>
      </div>
    </div>

  </div>
</div>

<style>
  .fullscreen {
    position: fixed !important;
    inset: 0 !important;
    z-index: 9999 !important;
    background: #09090b !important;
    width: 100vw !important;
    height: 100vh !important;
    border-radius: 0px !important;
    border: none !important;
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
  :global(input[type='range']::-webkit-slider-thumb) {
    -webkit-appearance: none;
    appearance: none;
    width: 8px;
    height: 8px;
    background-color: #ffffff;
    border-radius: 9999px;
    transition: transform 0.15s ease;
  }
  :global(input[type='range']:hover::-webkit-slider-thumb) {
    transform: scale(1.4);
  }

  @keyframes fadeIn {
    from { opacity: 0; transform: scale(0.98) translateY(4px); }
    to { opacity: 1; transform: scale(1) translateY(0); }
  }
  .animate-fade-in {
    animation: fadeIn 0.15s cubic-bezier(0.16, 1, 0.3, 1) forwards;
  }
</style>