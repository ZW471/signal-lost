/* ================================================================
   SIGNAL LOST — Background Music Engine

   Plays looping MP3 tracks for each district and the menu.
   Crossfades between tracks over 5 seconds using Web Audio API.
   ================================================================ */

const MusicEngine = (() => {
  let ctx = null;
  let masterGain = null;
  let currentTrack = null;   // { source, gain, name }
  let fadeDuration = 5;      // seconds
  let volume = 0.35;
  let muted = false;
  let _pendingTrack = null;  // track requested before ctx is ready
  const _bufferCache = {};   // name → AudioBuffer

  // MP3 file mapping: track name → URL path
  // Note: "The Resonance .mp3" has a trailing space in the filename
  const TRACK_FILES = {
    'menu':            '/assets/music/Menu.mp3',
    'The Sprawl':      '/assets/music/The Sprawl.mp3',
    'Neon Row':        '/assets/music/Neon Row.mp3',
    'The Undercroft':  '/assets/music/The Undercroft.mp3',
    'Sector 7':        '/assets/music/Sector7.mp3',
    'The Resonance':   '/assets/music/The Resonance .mp3',
    'Chrome Heights':  '/assets/music/Chrome Heights.mp3',
  };

  // District name aliases (Chinese names, etc.)
  const ALIASES = {
    '\u8513\u57CE':       'The Sprawl',      // 蔓城
    '\u9713\u8679\u8857': 'Neon Row',        // 霓虹街
    '\u5E95\u6E0A':       'The Undercroft',   // 底渊
    '\u7B2C\u4E03\u533A': 'Sector 7',        // 第七区
    '\u5171\u9E23\u6240': 'The Resonance',    // 共鸣所
    '\u5C16\u5854':       'Chrome Heights',   // 尖塔 — The Spire maps to Chrome Heights music
    'The Spire':          'Chrome Heights',
    '\u9540\u91D1\u53F0': 'Chrome Heights',   // 镀金台
  };

  // ---------------------------------------------------------------
  // AudioContext (lazy init on user gesture)
  // ---------------------------------------------------------------
  function ensureContext() {
    if (!ctx) {
      ctx = new (window.AudioContext || window.webkitAudioContext)();
      masterGain = ctx.createGain();
      masterGain.gain.value = muted ? 0 : volume;
      masterGain.connect(ctx.destination);
    }
    if (ctx.state === 'suspended') ctx.resume();
    return ctx;
  }

  // ---------------------------------------------------------------
  // Load and cache an MP3 as AudioBuffer
  // ---------------------------------------------------------------
  async function loadBuffer(name) {
    if (_bufferCache[name]) return _bufferCache[name];
    const url = TRACK_FILES[name];
    if (!url) return null;
    try {
      const resp = await fetch(url);
      if (!resp.ok) { console.warn('MusicEngine: failed to fetch', url); return null; }
      const arrayBuf = await resp.arrayBuffer();
      const audioBuf = await ctx.decodeAudioData(arrayBuf);
      _bufferCache[name] = audioBuf;
      return audioBuf;
    } catch (e) {
      console.warn('MusicEngine: error loading', url, e);
      return null;
    }
  }

  // ---------------------------------------------------------------
  // Resolve district name → canonical track name
  // ---------------------------------------------------------------
  function resolveTrack(name) {
    if (!name) return null;
    if (TRACK_FILES[name]) return name;
    if (ALIASES[name]) return ALIASES[name];
    // Case-insensitive fallback
    const lower = name.toLowerCase();
    for (const key of Object.keys(TRACK_FILES)) {
      if (key.toLowerCase() === lower) return key;
    }
    for (const [alias, canonical] of Object.entries(ALIASES)) {
      if (alias.toLowerCase() === lower) return canonical;
    }
    return null;
  }

  // ---------------------------------------------------------------
  // Core: switch track with crossfade
  // ---------------------------------------------------------------
  async function switchTo(trackName) {
    const resolved = resolveTrack(trackName);
    if (!resolved) return;

    ensureContext();

    // If AudioContext is still suspended, defer until running
    if (ctx.state !== 'running') {
      _pendingTrack = resolved;
      ctx.onstatechange = () => {
        if (ctx.state === 'running' && _pendingTrack) {
          const pending = _pendingTrack;
          _pendingTrack = null;
          ctx.onstatechange = null;
          switchTo(pending);
        }
      };
      return;
    }

    // Already playing this track
    if (currentTrack && currentTrack.name === resolved) return;

    // Load the audio buffer
    const buffer = await loadBuffer(resolved);
    if (!buffer) return;

    // Fade out current track
    if (currentTrack) {
      const old = currentTrack;
      const t = ctx.currentTime;
      old.gain.gain.setValueAtTime(old.gain.gain.value, t);
      old.gain.gain.linearRampToValueAtTime(0, t + fadeDuration);
      setTimeout(() => {
        try { old.source.stop(); } catch (e) { /* already stopped */ }
        old.gain.disconnect();
      }, fadeDuration * 1000 + 200);
      currentTrack = null;
    }

    // Create new source → gain → master
    const source = ctx.createBufferSource();
    source.buffer = buffer;
    source.loop = true;

    const gain = ctx.createGain();
    const t = ctx.currentTime;
    gain.gain.setValueAtTime(0, t);
    gain.gain.linearRampToValueAtTime(1.0, t + fadeDuration);

    source.connect(gain);
    gain.connect(masterGain);
    source.start(0);

    currentTrack = { source, gain, name: resolved };
  }

  // ---------------------------------------------------------------
  // Public API
  // ---------------------------------------------------------------

  function updateFromSession(session) {
    if (!session || !session.location) return;
    const district = session.location.district;
    if (district) switchTo(district);
  }

  function playMenu() { switchTo('menu'); }

  function stopAll() {
    if (currentTrack) {
      const old = currentTrack;
      const t = ctx.currentTime;
      old.gain.gain.setValueAtTime(old.gain.gain.value, t);
      old.gain.gain.linearRampToValueAtTime(0, t + fadeDuration);
      setTimeout(() => {
        try { old.source.stop(); } catch (e) {}
        old.gain.disconnect();
      }, fadeDuration * 1000 + 200);
      currentTrack = null;
    }
  }

  function setVolume(v) {
    volume = Math.max(0, Math.min(1, v));
    if (masterGain) masterGain.gain.value = muted ? 0 : volume;
  }

  function toggleMute() {
    muted = !muted;
    if (masterGain) masterGain.gain.value = muted ? 0 : volume;
    return muted;
  }

  function isMuted() { return muted; }
  function getVolume() { return volume; }

  // Preload all tracks in background after first user gesture
  function preloadAll() {
    ensureContext();
    if (ctx.state === 'running') {
      for (const name of Object.keys(TRACK_FILES)) {
        loadBuffer(name); // fire-and-forget
      }
    }
  }

  return {
    switchTo,
    updateFromSession,
    playMenu,
    stopAll,
    setVolume,
    getVolume,
    toggleMute,
    isMuted,
    preloadAll,
  };
})();
