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

  // MP3 file mapping: track name → URL path (opaque filenames to avoid spoilers)
  const TRACK_FILES = {
    'menu':            '/assets/music/menu.mp3',
    'The Sprawl':      '/assets/music/track_01.mp3',
    'Neon Row':        '/assets/music/track_02.mp3',
    'The Undercroft':  '/assets/music/track_03.mp3',
    'Sector 7':        '/assets/music/track_04.mp3',
    'The Resonance':   '/assets/music/track_05.mp3',
    'Chrome Heights':  '/assets/music/track_06.mp3',
    'The Spire':       '/assets/music/track_07.mp3',
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
    if (resolved === currentName && currentAudio) {
      // If audio was blocked by autoplay and is still paused, retry
      if (currentAudio.paused) {
        currentAudio.play().then(() => {
          _fadeInTimer = fade(currentAudio, effectiveVolume(), FADE_MS, () => {
            _fadeInTimer = null;
          });
        }).catch(() => {});
      }
      return;
    }

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

  // ---------------------------------------------------------------
  // Visibility / focus auto-pause
  //
  // Pause the music when the user is not looking at the page (tab
  // switch, window blur/minimize on desktop, app-switch or screen
  // lock on mobile). Resume when the page is visible/focused again,
  // but only if we were the ones who paused it and the user has not
  // manually muted in the meantime.
  // ---------------------------------------------------------------
  const VIS_FADE_MS = 250;  // short, snappy fade — page is backgrounding
  let _pausedByVisibility = false;
  let _visFadeTimer = null;

  /** True if there is a live audio element that is currently playing */
  function _isPlaying() {
    return !!(currentAudio && !currentAudio.paused);
  }

  /** Cancel a visibility-driven fade if one is in flight */
  function _clearVisFade() {
    if (_visFadeTimer) {
      clearInterval(_visFadeTimer);
      _visFadeTimer = null;
    }
  }

  /** Called when the page is hidden / window loses focus */
  function _onHide() {
    // Nothing to do if there's no track or it isn't actually playing,
    // or we've already paused it.
    if (_pausedByVisibility) return;
    if (!_isPlaying()) return;

    // Kill any in-flight crossfade/visibility fade so they can't
    // resurrect the volume after we pause.
    if (_fadeOutTimer) { clearInterval(_fadeOutTimer); _fadeOutTimer = null; }
    if (_fadeInTimer) { clearInterval(_fadeInTimer); _fadeInTimer = null; }
    _clearVisFade();

    _pausedByVisibility = true;
    const audio = currentAudio;
    _visFadeTimer = fade(audio, 0, VIS_FADE_MS, () => {
      _visFadeTimer = null;
      // Only pause if this is still the active track (guard against a
      // track switch racing in during the fade).
      if (audio) audio.pause();
    });
  }

  /** Called when the page becomes visible / window regains focus */
  function _onShow() {
    if (!_pausedByVisibility) return;
    _pausedByVisibility = false;

    _clearVisFade();

    // Respect a manual mute that may have happened while hidden, and
    // bail if nothing is around to resume.
    if (muted) return;
    if (!currentAudio) return;

    const audio = currentAudio;
    const playPromise = audio.play();
    const fadeUp = () => {
      _visFadeTimer = fade(audio, effectiveVolume(), VIS_FADE_MS, () => {
        _visFadeTimer = null;
      });
    };
    if (playPromise && typeof playPromise.then === 'function') {
      playPromise.then(fadeUp).catch(() => {});
    } else {
      fadeUp();
    }
  }

  // Page Visibility API is the primary, reliable signal (fires on
  // mobile app-switch / screen-lock and desktop tab-switch).
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) _onHide();
    else _onShow();
  });

  // Window blur/focus catches desktop un-focus without a tab switch
  // (e.g. clicking another window / minimizing). These are guarded by
  // the _pausedByVisibility flag so they don't fight visibilitychange.
  window.addEventListener('blur', _onHide);
  window.addEventListener('focus', _onShow);

  // pagehide/pageshow cover mobile bfcache transitions where
  // visibilitychange may not fire consistently.
  window.addEventListener('pagehide', _onHide);
  window.addEventListener('pageshow', _onShow);

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
