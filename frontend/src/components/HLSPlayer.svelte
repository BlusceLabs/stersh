<script lang="ts">
  import { onDestroy } from 'svelte';
  import type Hls from 'hls.js';

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
  const MAX_RETRIES = 5;
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

  // Keyboard shortcuts overlay
  let showShortcuts = $state(false);

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

  // Save progress before unload
  function saveProgress() {
    if (!videoEl || !onProgress || !videoEl.duration) return;
    onProgress({ currentTime: videoEl.currentTime, duration: videoEl.duration });
  }

  // Track all in-flight timeouts (retry timers, play-attempt retries)
  // so unmount can cancel them — otherwise they fire on a dead
  // component and bump reactive state.
  const _pendingTimeouts: Set<ReturnType<typeof setTimeout>> = new Set();

  onDestroy(() => {
    if (countdownTimer) {
      clearInterval(countdownTimer);
      countdownTimer = null;
    }
    for (const t of _pendingTimeouts) clearTimeout(t);
    _pendingTimeouts.clear();
  });

  function trackedSetTimeout(fn: () => void, ms: number): ReturnType<typeof setTimeout> {
    const t = setTimeout(() => {
      _pendingTimeouts.delete(t);
      fn();
    }, ms);
    _pendingTimeouts.add(t);
    return t;
  }

  // Playback Rate Options
  const speedOptions = [0.5, 0.75, 1, 1.25, 1.5, 2];

  // Playback Preferences Persistence
  const PREFS_KEY = 'watchfy_playback_prefs';

  type PlaybackPrefs = {
    playbackRate?: number;
    qualityIndex?: number;  // -1 for auto
    volume?: number;
    muted?: boolean;
  };

  function loadPrefs(): PlaybackPrefs {
    try {
      const stored = localStorage.getItem(PREFS_KEY);
      if (stored) return JSON.parse(stored);
    } catch {}
    return {};
  }

  function savePrefs(prefs: PlaybackPrefs) {
    try {
      localStorage.setItem(PREFS_KEY, JSON.stringify(prefs));
    } catch {}
  }

  function applySavedPrefs() {
    const prefs = loadPrefs();
    if (prefs.playbackRate && prefs.playbackRate !== 1) {
      playbackRate = prefs.playbackRate;
      if (videoEl) videoEl.playbackRate = prefs.playbackRate;
    }
    if (prefs.volume !== undefined && prefs.volume >= 0 && prefs.volume <= 1) {
      volume = prefs.volume;
      if (videoEl) videoEl.volume = prefs.volume;
    }
    if (prefs.muted !== undefined) {
      muted = prefs.muted;
      if (videoEl) videoEl.muted = prefs.muted;
    }
  }

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

  function seekToPercent(pct: number) {
    if (!duration || !videoEl) return;
    videoEl.currentTime = Math.max(0, Math.min(pct, 1)) * duration;
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
    savePrefs({ ...loadPrefs(), muted: videoEl.muted });
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
    savePrefs({ ...loadPrefs(), playbackRate: rate });
  }

  function changeQuality(index: number) {
    currentQualityIndex = index;
    if (hlsInstance) {
      hlsInstance.currentLevel = index; // -1 triggers adaptive auto resolution streaming logic
    }
    showSettings = false;
    savePrefs({ ...loadPrefs(), qualityIndex: index });
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

  function handleTimelineTouch(e: TouchEvent) {
    if (!duration || !videoEl || e.touches.length === 0) return;
    e.preventDefault();
    isScrubbing = true;
    showPreview = true;
    showControlsTemp();
    const pct = getTimelinePercentage(e.touches[0].clientX);
    seekPreview = pct * duration;
    seekPos = pct * 100;
    videoEl.currentTime = seekPreview;
  }

  function handleTimelineKeydown(e: KeyboardEvent) {
    if (!duration || !videoEl) return;
    if (e.key === 'ArrowRight') {
      e.preventDefault();
      skip(10);
    } else if (e.key === 'ArrowLeft') {
      e.preventDefault();
      skip(-10);
    } else if (e.key === 'Home') {
      e.preventDefault();
      seekToPercent(0);
    } else if (e.key === 'End') {
      e.preventDefault();
      seekToPercent(1);
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

    // Toggle shortcuts overlay with '?'
    if (e.key === '?') {
      e.preventDefault();
      showShortcuts = !showShortcuts;
      return;
    }

    // Close shortcuts overlay with Escape
    if (e.key === 'Escape' && showShortcuts) {
      e.preventDefault();
      showShortcuts = false;
      return;
    }

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
          // `track.language` is null in some browsers (notably Firefox
          // when the manifest omits the LANGUAGE attribute). Coerce to
          // empty string before calling `.toUpperCase()`.
          const lang = (track.language || '').toUpperCase();
          discoveredTracks.push({
            index: i,
            label: track.label || lang || `Track ${i + 1}`,
            language: track.language || '',
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

    // Apply saved playback preferences
    applySavedPrefs();
    
    v.addEventListener('progress', () => {
      if (v.buffered.length > 0) buffered = v.buffered.end(v.buffered.length - 1);
    });

    document.addEventListener('fullscreenchange', onFullscreenChange);
    document.addEventListener('keydown', handleKeydown);
    window.addEventListener('mouseup', handleGlobalMouseUp);
    window.addEventListener('beforeunload', saveProgress);

    let progressInterval: ReturnType<typeof setInterval> | null = null;
    if (onProgress) {
      progressInterval = setInterval(() => {
        if (v.duration > 0) {
          onProgress({ currentTime: v.currentTime, duration: v.duration });
        }
      }, 5000);
    }

    return () => {
      if (progressInterval) clearInterval(progressInterval);
      window.removeEventListener('beforeunload', saveProgress);
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

    let disposed = false;
    let localHls: Hls | null = null;

    import('hls.js').then(({ default: Hls }) => {
      if (disposed || !videoEl) return;
      if (!Hls.isSupported()) {
        if (videoEl.canPlayType('application/vnd.apple.mpegurl')) {
          videoEl.src = hlsUrl;
        } else {
          error = 'Adaptive streaming playback layer failure.';
        }
        return;
      }

      const effectiveStart = _retryStartTime > 0 ? _retryStartTime : startTime;
      const hls = new Hls({
        startPosition: effectiveStart > 0 ? effectiveStart : 0,
        capLevelToPlayerSize: true,
        xhrSetup: (xhr, url) => {
          xhr.timeout = 30000;
        },
      });
      hls.loadSource(hlsUrl);
      hls.attachMedia(videoEl);
      localHls = hls;

      hls.on(Hls.Events.MANIFEST_PARSED, () => {
        if (disposed) { hls.destroy(); return; }
        qualities = hls.levels.map((lvl, index) => ({
          index,
          label: lvl.height ? `${lvl.height}p` : `Level ${index}`
        })).reverse();

        if (effectiveStart > 0) {
          videoEl.currentTime = effectiveStart;
        }
        _retryStartTime = 0;
        // Reset retry counter on a successful manifest load so a
        // subsequent error gets a fresh budget instead of being blocked
        // by the budget of an already-resolved earlier failure.
        hlsRetries = 0;
        if (autoPlay) {
          (function tryPlay(attempts = 0) {
            if (attempts > 5) return;
            videoEl.play().catch(() => trackedSetTimeout(() => tryPlay(attempts + 1), 250));
          })();
        }
      });

      hls.on(Hls.Events.LEVEL_SWITCHED, (_, data) => {
        // Keeps the indicator perfectly synced if auto switching is operational
        if (hls.autoLevelEnabled) currentQualityIndex = -1;
      });

      hls.on(Hls.Events.ERROR, (_event, data) => {
        if (disposed) return;
        if (data.fatal) {
          const code = data.response?.code;
          const isRetryable = code === 401 || code === 403 || code === 404 || code === 410 || code === 0 || !code;
          const context = data.context;

          // Don't retry network-level fragment/segment errors if we've exceeded retries
          if (context && ('frag' in context || 'level' in context) && hlsRetries >= MAX_RETRIES) {
            error = 'Stream connection interrupted. Please try switching servers or refreshing.';
            return;
          }

          if (isRetryable && hlsRetries < MAX_RETRIES && src) {
            hlsRetries++;
            console.warn(`[HLS] Fatal error (attempt ${hlsRetries}/${MAX_RETRIES}):`, data.type, data.details, 'code:', code);
            // Capture exact playback position BEFORE teardown so the new
            // Hls instance resumes at the same timestamp instead of 0:00
            _retryStartTime = videoEl.currentTime;
            // Clear hlsUrl and bump fetchKey to re-fetch manifest with fresh tokens
            hlsUrl = '';
            // Small delay before retry to avoid hammering
            trackedSetTimeout(() => { fetchKey++; }, 500 * hlsRetries);
            return;
          }

          error = 'Stream connection interrupted. Please try switching servers or refreshing.';
        }
      });

      // Assign to the component-scoped handle only if we're still alive;
      // otherwise the cleanup function will not see this instance and
      // the Hls object would leak (and the Hls.error event would have
      // set component state on an unmounted component).
      if (disposed) {
        hls.destroy();
        return;
      }
      hlsInstance = hls;
    }).catch(() => {
      if (!disposed) error = 'Adaptive streaming playback layer failure.';
    });

    return () => {
      disposed = true;
      if (localHls) localHls.destroy();
      if (hlsInstance === localHls) hlsInstance = null;
    };
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

    // On retry (hlsRetries > 0), force refresh to get fresh tokens
    const refreshParam = hlsRetries > 0 ? '&refresh=true' : '';
    const fetchUrl = `${src}${refreshParam}`;

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 45000);

    fetch(fetchUrl, { signal: controller.signal })
      .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); })
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
      .catch((err) => {
        if (!cancelled) {
          if (err.name === 'AbortError') {
            error = 'Stream source timed out. Retrying...';
            // Auto-retry on timeout
            if (hlsRetries < MAX_RETRIES) {
              hlsRetries++;
              trackedSetTimeout(() => { fetchKey++; }, 1000);
            }
          } else {
            error = 'Failed to establish stable streaming pipeline.';
          }
        }
      })
      .finally(() => { clearTimeout(timeoutId); if (!cancelled) loading = false; });

    return () => { cancelled = true; clearTimeout(timeoutId); };
  });

  let progressPct = $derived(duration > 0 ? (currentTime / duration) * 100 : 0);
  let bufferedPct = $derived(duration > 0 ? (buffered / duration) * 100 : 0);
  let remainingTime = $derived(duration > 0 ? Math.max(duration - currentTime, 0) : 0);
  let volPct = $derived(muted ? 0 : volume * 100);
  let activeQualityLabel = $derived(currentQualityIndex === -1 ? 'Auto' : qualities.find(q => q.index === currentQualityIndex)?.label || 'Auto');
  let activeCaptionLabel = $derived(currentCaptionIndex === -1 ? 'Off' : captions.find(c => c.index === currentCaptionIndex)?.label || 'Off');
  let hlsRetries = $state(0);
  let _retryStartTime = 0;
</script>

<svelte:window onmousemove={showControlsTemp} />

<div
  bind:this={containerEl}
  class="relative w-full bg-black select-none group/player cursor-default overflow-hidden rounded-xl"
  class:fullscreen={isFullscreen}
  role="application"
  aria-label="Video Player"
>
  <div 
    class="relative w-full aspect-video bg-black overflow-hidden flex items-center justify-center transition-all duration-500"
    onmouseleave={() => { if (!isScrubbing) showSettings = false; }}
    role="presentation"
  >
    <video
      bind:this={videoEl}
      autoplay={autoPlay}
      class="w-full h-full object-contain bg-black cursor-pointer transition-opacity duration-300 ease-exo-out"
      class:opacity-40={loading || error}
      title={title}
      playsinline
      preload="metadata"
      onclick={togglePlay}
      ondblclick={toggleFullscreen}
    >
      <p class="text-zinc-500 text-center p-4 text-sm">Your browser does not support internal streaming layers.</p>
    </video>

    <div class="pointer-events-none absolute left-0 right-0 top-0 z-20 bg-gradient-to-b from-black/80 via-black/30 to-transparent px-4 pb-12 pt-3 transition-opacity duration-300 {showControls || !playing ? 'opacity-100' : 'opacity-0'}">
      <p class="max-w-[80%] truncate text-sm font-medium text-white sm:text-base">{title}</p>
      <p class="mt-0.5 text-xs text-white/70">{activeQualityLabel} • {formatTime(currentTime)} elapsed</p>
    </div>

{#if loading}
       <div class="absolute inset-0 flex items-center justify-center bg-black/40 z-20 pointer-events-none">
         <div class="flex flex-col items-center gap-3">
           <div class="relative w-12 h-12 flex items-center justify-center">
             <div class="w-12 h-12 border-[3px] border-white/10 rounded-full absolute"></div>
             <div class="w-12 h-12 border-[3px] border-t-white border-r-transparent border-b-transparent border-l-transparent rounded-full animate-spin absolute"></div>
           </div>
           <p class="text-xs font-medium text-white/70">Opening stream</p>
         </div>
       </div>
     {/if}

     {#if error}
       <div class="absolute inset-0 flex items-center justify-center bg-black/80 p-6 z-20">
         <div class="text-center max-w-sm">
           <div class="w-12 h-12 rounded-full bg-white/10 flex items-center justify-center text-white mx-auto mb-4">
             <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="22" height="22" color="currentColor" fill="none">
               <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="1.5" />
               <path d="M12 7V13" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
               <circle cx="12" cy="17" r="1" fill="currentColor" />
             </svg>
           </div>
           <p class="text-white text-sm leading-relaxed px-4">{error}</p>
           {#if src}
             <button
               onclick={(e) => { e.stopPropagation(); hlsRetries = 0; fetchKey++; }}
               class="mt-4 px-5 py-2 rounded-full bg-white text-black text-sm font-medium hover:bg-white/90 transition-colors duration-100"
             >
               Retry
             </button>
           {/if}
         </div>
       </div>
     {/if}

    {#if !playing && !loading && !error}
      <div
        class="absolute inset-0 flex items-center justify-center z-10 cursor-pointer"
        onclick={togglePlay}
        onkeydown={(event) => {
          if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            togglePlay();
          }
        }}
        role="button"
        tabindex="0"
        aria-label={ended ? 'Replay video' : 'Play video'}
      >
        {#if ended && onNext && countdown > 0}
          <div class="flex flex-col items-center gap-4">
            <div class="flex flex-col items-center gap-2">
              <p class="text-sm text-white/80 font-medium">Up Next</p>
              <p class="text-5xl font-bold text-white tabular-nums leading-none">{countdown}</p>
              <p class="text-xs text-white/60">starting in...</p>
            </div>
            <div class="flex gap-2">
              <button onclick={(event) => { event.stopPropagation(); togglePlay(); }} class="px-5 py-2 bg-white/10 hover:bg-white/20 rounded-full text-sm font-medium text-white transition-colors duration-100">
                <svg class="inline-block -mt-0.5 mr-1.5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="16" height="16" color="currentColor" fill="none">
                  <path d="M6.5 5.5L18.5 12L6.5 18.5V5.5Z" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" fill="currentColor" />
                </svg>
                Replay
              </button>
              <button onclick={(event) => { event.stopPropagation(); cancelCountdown(); }} class="px-5 py-2 bg-white/10 hover:bg-white/20 rounded-full text-sm font-medium text-white transition-colors duration-100">
                Cancel
              </button>
            </div>
          </div>
        {:else if ended}
          <button class="w-16 h-16 rounded-full bg-black/60 hover:bg-black/80 flex items-center justify-center text-white transition-colors duration-100" aria-label="Replay video">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" color="currentColor" fill="none">
              <path d="M19 12H5M5 12L10 7M5 12L10 17" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
          </button>
        {:else}
          <button class="w-16 h-16 rounded-full bg-black/60 hover:bg-black/80 flex items-center justify-center text-white transition-colors duration-100" aria-label="Play video">
            <svg class="translate-x-[1px]" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" color="currentColor" fill="none">
              <path d="M6.5 5.5L18.5 12L6.5 18.5V5.5Z" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" fill="currentColor" />
            </svg>
          </button>
        {/if}
      </div>
    {/if}

{#if showSettings}
       <div class="absolute bottom-20 right-4 w-64 bg-[#282828] rounded-lg z-30 p-2 text-white text-sm font-medium" onmouseenter={showControlsTemp} role="presentation">
         {#if currentMenuTab === 'main'}
           <div class="flex flex-col">
             {#if qualities.length > 0}
               <button onclick={() => currentMenuTab = 'quality'} class="flex items-center justify-between p-3 hover:bg-white/10 rounded-md transition-colors duration-100">
                 <span>Quality</span>
                 <span class="flex items-center gap-1 text-white/80">{activeQualityLabel} <span class="text-white/60">›</span></span>
               </button>
             {/if}
             <button onclick={() => currentMenuTab = 'speed'} class="flex items-center justify-between p-3 hover:bg-white/10 rounded-md transition-colors duration-100">
               <span>Speed</span>
               <span class="flex items-center gap-1 text-white/80">{playbackRate === 1 ? 'Normal' : playbackRate + 'x'} <span class="text-white/60">›</span></span>
             </button>
             {#if captions.length > 0}
               <button onclick={() => currentMenuTab = 'captions'} class="flex items-center justify-between p-3 hover:bg-white/10 rounded-md transition-colors duration-100">
                 <span>Captions</span>
                 <span class="flex items-center gap-1 text-white/80">{activeCaptionLabel} <span class="text-white/60">›</span></span>
               </button>
             {/if}
           </div>
         {:else}
           <div class="flex flex-col max-h-56 overflow-y-auto">
             <button onclick={() => currentMenuTab = 'main'} class="flex items-center gap-2 p-3 mb-1 font-semibold text-white/80 border-b border-white/10 hover:text-white transition-colors duration-100">
               <span>‹</span> Back
             </button>

             {#if currentMenuTab === 'quality'}
               <button onclick={() => changeQuality(-1)} class="flex items-center justify-between p-2 hover:bg-white/10 rounded text-left {currentQualityIndex === -1 ? 'text-white' : ''} transition-colors duration-100">
                 <span>Auto ({qualities.length > 0 ? qualities[qualities.length - 1]?.label : 'Auto'})</span>
                 {#if currentQualityIndex === -1}<span>✓</span>{/if}
               </button>
               {#each qualities as q}
                 <button onclick={() => changeQuality(q.index)} class="flex items-center justify-between p-2 hover:bg-white/10 rounded text-left {currentQualityIndex === q.index ? 'text-white' : ''} transition-colors duration-100">
                   <span>{q.label}</span>
                   {#if currentQualityIndex === q.index}<span>✓</span>{/if}
                 </button>
               {/each}
             {:else if currentMenuTab === 'speed'}
               {#each speedOptions as speed}
                 <button onclick={() => changeSpeed(speed)} class="flex items-center justify-between p-2 hover:bg-white/10 rounded text-left {playbackRate === speed ? 'text-white' : ''} transition-colors duration-100">
                   <span>{speed === 1 ? 'Normal' : speed + 'x'}</span>
                   {#if playbackRate === speed}<span>✓</span>{/if}
                 </button>
               {/each}
             {:else if currentMenuTab === 'captions'}
               <button onclick={() => changeCaption(-1)} class="flex items-center justify-between p-2 hover:bg-white/10 rounded text-left {currentCaptionIndex === -1 ? 'text-white' : ''} transition-colors duration-100">
                 <span>Off</span>
                 {#if currentCaptionIndex === -1}<span>✓</span>{/if}
               </button>
               {#each captions as cap}
                 <button onclick={() => changeCaption(cap.index)} class="flex items-center justify-between p-2 hover:bg-white/10 rounded text-left {currentCaptionIndex === cap.index ? 'text-white' : ''} transition-colors duration-100">
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
      class="absolute bottom-0 left-0 right-0 z-20 transition-all duration-300 ease-out flex flex-col justify-end px-4 pb-3 pt-12 bg-gradient-to-t from-black/90 via-black/40 to-transparent
      {showControls || !playing || isScrubbing ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4 pointer-events-none'}"
      onmouseenter={showControlsTemp}
      role="presentation"
    >
      <div class="w-full flex flex-col gap-2 px-2">

<div
           bind:this={progressBar}
           class="relative w-full h-3 group/progress cursor-pointer flex items-center"
           onmousedown={handleTimelineMouseDown}
           onmousemove={handleTimelineMouseMove}
           ontouchstart={handleTimelineTouch}
           ontouchmove={handleTimelineTouch}
           ontouchend={() => { isScrubbing = false; showPreview = false; showControlsTemp(); }}
           onmouseleave={() => showPreview = false}
           onkeydown={handleTimelineKeydown}
           role="slider"
           aria-label="Seek"
           aria-valuemin="0"
           aria-valuemax={Math.max(duration, 0)}
           aria-valuenow={Math.min(currentTime, duration || currentTime)}
           tabindex="0"
         >
           <div class="absolute left-0 right-0 h-0.5 bg-white/20 rounded-full transition-all duration-100 group-hover/progress:h-1 group-hover/progress:bg-white/30"></div>
           <div class="absolute h-0.5 bg-white/40 rounded-full transition-all duration-100 group-hover/progress:h-1" style="width: {bufferedPct}%"></div>
           <div class="absolute h-0.5 bg-[#ff0000] rounded-full transition-all duration-100 group-hover/progress:h-1" style="width: {progressPct}%"></div>

           <div
             class="absolute w-3 h-3 bg-[#ff0000] rounded-full opacity-0 group-hover/progress:opacity-100 transition-opacity duration-100 pointer-events-none"
             style="left: calc({progressPct}% - 6px)"
           ></div>

           {#if showPreview && duration}
             <div
               class="absolute bottom-4 -translate-x-1/2 bg-black/90 text-white text-xs font-medium px-2 py-1 rounded pointer-events-none whitespace-nowrap tabular-nums"
               style="left: {seekPos}%"
             >
               {formatTime(seekPreview)}
             </div>
           {/if}
         </div>

        <div class="flex items-center justify-between gap-2 text-white">

<div class="flex items-center gap-1">

            {#if onPrev}
              <button onclick={onPrev} class="w-10 h-10 flex items-center justify-center hover:bg-white/10 rounded-full text-white" aria-label="Previous Episode">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="22" height="22" color="currentColor" fill="none">
                  <path d="M4 5V19M20 5L10 12L20 19V5Z" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" fill="currentColor" />
                </svg>
              </button>
            {/if}

            <button onclick={() => skip(-10)} class="w-10 h-10 flex items-center justify-center hover:bg-white/10 rounded-full text-white" aria-label="Rewind 10 Seconds">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="22" height="22" color="currentColor" fill="none">
                <path d="M14 5L5 12L14 19V5Z" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" fill="currentColor" />
                <path d="M20 6L13 12L20 18V6Z" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" fill="currentColor" />
              </svg>
            </button>

            <button onclick={togglePlay} class="w-10 h-10 flex items-center justify-center hover:bg-white/10 rounded-full text-white" aria-label={playing ? 'Pause' : 'Play'}>
              {#if playing}
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="22" height="22" color="currentColor" fill="none">
                  <path d="M7 4V20M17 4V20" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
                </svg>
              {:else}
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="22" height="22" color="currentColor" fill="none">
                  <path d="M6.5 5.5L18.5 12L6.5 18.5V5.5Z" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" fill="currentColor" />
                </svg>
              {/if}
            </button>

            <button onclick={() => skip(10)} class="w-10 h-10 flex items-center justify-center hover:bg-white/10 rounded-full text-white" aria-label="Forward 10 Seconds">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="22" height="22" color="currentColor" fill="none">
                <path d="M10 19L19 12L10 5V19Z" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" fill="currentColor" />
                <path d="M4 18L11 12L4 6V18Z" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" fill="currentColor" />
              </svg>
            </button>

            {#if onNext}
              <button onclick={onNext} class="w-10 h-10 flex items-center justify-center hover:bg-white/10 rounded-full text-white" aria-label="Next Episode">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="22" height="22" color="currentColor" fill="none">
                  <path d="M20 5V19M4 5L14 12L4 19V5Z" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" fill="currentColor" />
                </svg>
              </button>
            {/if}

            <span class="text-xs font-medium text-white tabular-nums ml-2">
              {formatTime(currentTime)} <span class="text-white/60 px-0.5">/</span> {formatTime(duration)}
            </span>
            {#if remainingTime > 0}
              <span class="hidden text-xs text-white/60 tabular-nums sm:inline">
                -{formatTime(remainingTime)}
              </span>
            {/if}
          </div>

          <div class="flex items-center gap-1">

<div class="flex items-center gap-0.5 group/volume">
               <button onclick={toggleMute} class="w-10 h-10 flex items-center justify-center hover:bg-white/10 rounded-full text-white" aria-label={muted ? 'Unmute' : 'Mute'}>
                 {#if muted || volume === 0}
                   <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="22" height="22" color="currentColor" fill="none">
                     <path d="M2 9V15H6L11 20V4L6 9H2Z" stroke="currentColor" stroke-width="1.75" stroke-linejoin="round" />
                     <path d="M16 10L20 14M20 10L16 14" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" />
                   </svg>
                 {:else}
                   <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="22" height="22" color="currentColor" fill="none">
                     <path d="M2 9V15H6L11 20V4L6 9H2Z" stroke="currentColor" stroke-width="1.75" stroke-linejoin="round" />
                     <path d="M15.5 8.5C16.5 9.5 16.5 11.5 15.5 12.5M18.5 6C20.5 8 20.5 14 18.5 16" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" />
                   </svg>
                 {/if}
               </button>

               <div class="w-0 overflow-hidden group-hover/player:w-16 group-hover/volume:w-16 transition-all duration-200 ease-out flex items-center pr-1">
                 <input
                   type="range"
                   min="0"
                   max="100"
                   value={volPct}
                    oninput={(e) => { if (videoEl) { const v = Number(e.currentTarget.value) / 100; videoEl.volume = v; videoEl.muted = v === 0; savePrefs({ ...loadPrefs(), volume: v, muted: v === 0 }); } }}
                   class="w-full h-1 appearance-none bg-white/30 rounded-full cursor-pointer accent-white focus:outline-none"
                 />
               </div>
             </div>

              <button onclick={() => showSettings = !showSettings} class="w-10 h-10 flex items-center justify-center hover:bg-white/10 rounded-full text-white" class:text-white={showSettings} aria-label="Player Settings">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="22" height="22" color="currentColor" fill="none">
                  <path d="M12 15C13.6569 15 15 13.6569 15 12C15 10.3431 13.6569 9 12 9C10.3431 9 9 10.3431 9 12C9 13.6569 10.3431 15 12 15Z" stroke="currentColor" stroke-width="1.75" stroke-linejoin="round" />
                  <path d="M19.6196 9.77124C19.8243 10.5181 20 11.2372 20 12C20 12.7628 19.8243 13.4819 19.6196 14.2288C19.5005 14.6633 19.441 14.8805 19.4891 15.0934C19.5372 15.3063 19.6841 15.4741 19.9778 15.8098C20.5516 16.4659 20.8385 16.794 20.8037 17.164C20.7688 17.534 20.4187 17.8841 19.7186 18.5843L18.5843 19.7186C17.8841 20.4187 17.534 20.7688 17.164 20.8037C16.794 20.8385 16.4659 20.5516 15.8098 19.9778C15.4741 19.6841 15.3063 19.5372 15.0934 19.4891C14.8805 19.441 14.6633 19.5005 14.2288 19.6196C13.4819 19.8243 12.7628 20 12 20C11.2372 20 10.5181 19.8243 9.77124 19.6196C9.33671 19.5005 9.11945 19.441 8.90656 19.4891C8.69366 19.5372 8.52589 19.6841 8.19017 19.9778C7.53406 20.5516 7.20601 20.8385 6.83603 20.8037C6.46604 20.7688 6.11593 20.4187 5.41571 19.7186L4.28138 18.5843C3.58116 17.8841 3.23105 17.534 3.19622 17.164C3.16139 16.794 3.44836 16.4659 4.02221 15.8098C4.31593 15.4741 4.46279 15.3063 4.51089 15.0934C4.55899 14.8805 4.49947 14.6633 4.38043 14.2288C4.17572 13.4819 4 12.7628 4 12C4 11.2372 4.17572 10.5181 4.38043 9.77124C4.49947 9.33671 4.55899 9.11945 4.51089 8.90656C4.46279 8.69366 4.31593 8.52589 4.02221 8.19017C3.44836 7.53406 3.16139 7.20601 3.19622 6.83603C3.23105 6.46604 3.58116 6.11593 4.28138 5.41571L5.41571 4.28138C6.11593 3.58116 6.46604 3.23105 6.83603 3.19622C7.20601 3.16139 7.53406 3.44836 8.19017 4.02221C8.52589 4.31593 8.69366 4.46279 8.90656 4.51089C9.11945 4.55899 9.33671 4.49947 9.77124 4.38043C10.5181 4.17572 11.23724 4 12 4C12.7628 4 13.4819 4.17572 14.2288 4.38043C14.6633 4.48126 14.8805 4.53167 15.0934 4.48358C15.3063 4.43548 15.4741 4.29367 15.8098 4.01005C16.4659 3.45607 16.794 3.17908 17.164 3.21271C17.534 3.24635 17.8841 3.58434 18.5843 4.26033L19.7186 5.35824C20.4187 6.03423 20.7688 6.37222 20.8037 6.72945C20.8385 7.08668 20.5516 7.40334 19.9778 8.03666C19.6841 8.36142 19.5372 8.52379 19.4891 8.72932C19.441 8.93484 19.5005 9.14457 19.6196 9.77124Z" stroke="currentColor" stroke-width="1.75" />
                </svg>
              </button>

              <button onclick={() => showShortcuts = !showShortcuts} class="w-10 h-10 flex items-center justify-center hover:bg-white/10 rounded-full text-white" aria-label="Keyboard shortcuts">
                <span class="text-xs font-bold">?</span>
              </button>

             {#if supportsPiP}
               <button onclick={togglePiP} class="w-10 h-10 flex items-center justify-center hover:bg-white/10 rounded-full text-white" aria-label="Picture-in-Picture">
                 <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="22" height="22" color="currentColor" fill="none">
                   <path d="M3 5C3 3.89543 3.89543 3 5 3H19C20.1046 3 21 3.89543 21 5V13C21 14.1046 20.1046 15 19 15H13V19C13 20.1046 12.1046 21 11 21H5C3.89543 21 3 20.1046 3 19V5Z" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" />
                   <rect x="13" y="13" width="8" height="6" rx="1" stroke="currentColor" stroke-width="1.75" fill="currentColor" fill-opacity="0.2" />
                 </svg>
               </button>
             {/if}

            <button onclick={toggleFullscreen} class="w-10 h-10 flex items-center justify-center hover:bg-white/10 rounded-full text-white" aria-label={isFullscreen ? 'Exit fullscreen' : 'Fullscreen'}>
              {#if isFullscreen}
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="22" height="22" color="currentColor" fill="none">
                  <path d="M4 14H10M10 14V20M10 14L3 21M20 10H14M14 10V4M14 10L21 3" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" />
                </svg>
              {:else}
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="22" height="22" color="currentColor" fill="none">
                  <path d="M9 3H4C3.44772 3 3 3.44772 3 4V9M15 3H20C20.5523 3 21 3.44772 21 4V9M9 21H4C3.44772 21 3 20.5523 3 20V15M15 21H20C20.5523 21 21 20.5523 21 20V15" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" />
                </svg>
              {/if}
            </button>
          </div>

        </div>
      </div>
    </div>

  </div>
</div>

<!-- Keyboard Shortcuts Overlay -->
{#if showShortcuts}
  <div class="fixed inset-0 z-[10000] flex items-center justify-center bg-black/80" onclick={() => showShortcuts = false} role="dialog" aria-label="Keyboard Shortcuts" aria-modal="true">
    <div class="bg-[#282828] rounded-xl p-6 max-w-md w-full mx-4" onclick={(e) => e.stopPropagation()}>
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-lg font-bold text-white">Keyboard shortcuts</h2>
        <button onclick={() => showShortcuts = false} class="w-8 h-8 flex items-center justify-center hover:bg-white/10 rounded-full text-white" aria-label="Close">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="18" height="18" color="currentColor" fill="none">
            <path d="M18 6L6 18M6 6l12 12" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
        </button>
      </div>
      <div class="space-y-2.5">
        {#each [
          { key: 'Space / K', action: 'Play / Pause' },
          { key: 'F', action: 'Toggle fullscreen' },
          { key: 'M', action: 'Toggle mute' },
          { key: '← / →', action: 'Seek ±10 seconds' },
          { key: 'N', action: 'Next episode' },
          { key: 'P', action: 'Previous episode / PiP' },
          { key: '?', action: 'Toggle this help' },
          { key: 'Esc', action: 'Close overlay' },
        ] as shortcut}
          <div class="flex items-center justify-between">
            <span class="text-sm text-white/80">{shortcut.action}</span>
            <kbd class="px-2 py-1 bg-white/10 rounded text-xs font-mono text-white">{shortcut.key}</kbd>
          </div>
        {/each}
      </div>
    </div>
  </div>
{/if}

<style>
  .fullscreen {
    position: fixed !important;
    inset: 0 !important;
    z-index: 9999 !important;
    background: #000 !important;
    width: 100vw !important;
    height: 100vh !important;
    border-radius: 0 !important;
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
    width: 12px;
    height: 12px;
    background-color: #ffffff;
    border-radius: 9999px;
  }
</style>
