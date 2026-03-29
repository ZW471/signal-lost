/* ================================================================
   SIGNAL LOST — Background Music Engine

   Plays looping MP3 tracks for each district and the menu.
   Uses HTML Audio elements for reliability, with JS crossfade.
   Crossfade duration: 5 seconds.
   ================================================================ */

const MusicEngine = (() => {
  const FADE_MS = 5000;
  const FADE_STEP = 50;  // ms per step
  let volume = 0.35;
  let muted = false;
  let currentAudio = null;   // currently playing Audio element
  let currentName = null;
  let _fadeOutTimer = null;
  let _fadeInTimer = null;

  // MP3 file mapping: track name → URL path
  const TRACK_FILES = {
    'menu':            '/assets/music/Menu.mp3',
    'The Sprawl':      '/assets/music/The%20Sprawl.mp3',
    'Neon Row':        '/assets/music/Neon%20Row.mp3',
    'The Undercroft':  '/assets/music/The%20Undercroft.mp3',
    'Sector 7':        '/assets/music/Sector7.mp3',
    'The Resonance':   '/assets/music/The%20Resonance%20.mp3',
    'Chrome Heights':  '/assets/music/Chrome%20Heights.mp3',
    'The Spire':       '/assets/music/The%20Spire.mp3',
  };

  // Aliases for Chinese district names
  const ALIASES = {
    '\u8513\u57CE':       'The Sprawl',      // 蔓城
    '\u9713\u8679\u8857': 'Neon Row',        // 霓虹街
    '\u5E95\u6E0A':       'The Undercroft',   // 底渊
    '\u7B2C\u4E03\u533A': 'Sector 7',        // 第七区
    '\u5171\u9E23\u6240': 'The Resonance',    // 共鸣所
    '\u5C16\u5854':       'The Spire',        // 尖塔
    '\u9540\u91D1\u53F0': 'Chrome Heights',   // 镀金台
  };

  // Audio element cache
  const _audioCache = {};

  function resolveTrack(name) {
    if (!name) return null;
    if (TRACK_FILES[name]) return name;
    if (ALIASES[name]) return ALIASES[name];
    const lower = name.toLowerCase();
    for (const key of Object.keys(TRACK_FILES)) {
      if (key.toLowerCase() === lower) return key;
    }
    for (const [alias, canonical] of Object.entries(ALIASES)) {
      if (alias.toLowerCase() === lower) return canonical;
    }
    return null;
  }

  /** Get or create a cached Audio element for a track */
  function getAudio(name) {
    if (_audioCache[name]) return _audioCache[name];
    const url = TRACK_FILES[name];
    if (!url) return null;
    const audio = new Audio(url);
    audio.loop = true;
    audio.preload = 'auto';
    audio.volume = 0;
    _audioCache[name] = audio;
    return audio;
  }

  /** Fade an audio element's volume from current to target over duration */
  function fade(audio, targetVol, durationMs, onDone) {
    if (!audio) { if (onDone) onDone(); return; }
    const startVol = audio.volume;
    const diff = targetVol - startVol;
    const steps = Math.max(1, Math.floor(durationMs / FADE_STEP));
    let step = 0;
    const timer = setInterval(() => {
      step++;
      if (step >= steps) {
        audio.volume = targetVol;
        clearInterval(timer);
        if (onDone) onDone();
      } else {
        audio.volume = Math.max(0, Math.min(1, startVol + diff * (step / steps)));
      }
    }, FADE_STEP);
    return timer;
  }

  function effectiveVolume() {
    return muted ? 0 : volume;
  }

  /** Switch to a new track with crossfade */
  function switchTo(trackName) {
    const resolved = resolveTrack(trackName);
    if (!resolved) return;
    if (resolved === currentName && currentAudio) return;

    const newAudio = getAudio(resolved);
    if (!newAudio) return;

    // Clear any ongoing fades
    if (_fadeOutTimer) clearInterval(_fadeOutTimer);
    if (_fadeInTimer) clearInterval(_fadeInTimer);

    // Fade out current
    const oldAudio = currentAudio;
    const oldName = currentName;
    if (oldAudio) {
      _fadeOutTimer = fade(oldAudio, 0, FADE_MS, () => {
        oldAudio.pause();
        oldAudio.currentTime = 0;
        _fadeOutTimer = null;
      });
    }

    // Start and fade in new
    newAudio.volume = 0;
    const playPromise = newAudio.play();
    if (playPromise) {
      playPromise.then(() => {
        _fadeInTimer = fade(newAudio, effectiveVolume(), FADE_MS, () => {
          _fadeInTimer = null;
        });
      }).catch(err => {
        // Autoplay blocked — retry on next user interaction
        console.warn('MusicEngine: play blocked, will retry on click', err);
        const retry = () => {
          newAudio.play().then(() => {
            _fadeInTimer = fade(newAudio, effectiveVolume(), FADE_MS, () => {
              _fadeInTimer = null;
            });
          }).catch(() => {});
          document.removeEventListener('click', retry);
        };
        document.addEventListener('click', retry, { once: true });
      });
    }

    currentAudio = newAudio;
    currentName = resolved;
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
    if (_fadeOutTimer) clearInterval(_fadeOutTimer);
    if (_fadeInTimer) clearInterval(_fadeInTimer);
    if (currentAudio) {
      _fadeOutTimer = fade(currentAudio, 0, FADE_MS, () => {
        currentAudio.pause();
        currentAudio.currentTime = 0;
        _fadeOutTimer = null;
      });
      currentAudio = null;
      currentName = null;
    }
  }

  function setVolume(v) {
    volume = Math.max(0, Math.min(1, v));
    if (currentAudio && !muted) {
      currentAudio.volume = volume;
    }
  }

  function toggleMute() {
    muted = !muted;
    if (currentAudio) {
      currentAudio.volume = muted ? 0 : volume;
    }
    return muted;
  }

  function isMuted() { return muted; }
  function getVolume() { return volume; }

  /** Preload all tracks */
  function preloadAll() {
    for (const name of Object.keys(TRACK_FILES)) {
      getAudio(name); // creates Audio element which starts preloading
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
