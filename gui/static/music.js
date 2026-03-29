/* ================================================================
   SIGNAL LOST — Procedural Ambient Music Engine

   Uses Web Audio API to generate cyberpunk ambient soundscapes.
   Each district has a unique generative composition.
   Crossfades between tracks over 5 seconds.
   ================================================================ */

const MusicEngine = (() => {
  let ctx = null;         // AudioContext (lazy-init on user gesture)
  let masterGain = null;  // Master volume node
  let currentTrack = null;
  let currentTrackName = null;
  let _pendingTrack = null; // Track requested while ctx was suspended
  let fadeDuration = 5;   // seconds
  let volume = 0.35;      // default volume
  let muted = false;

  // ---------------------------------------------------------------
  // Lazy AudioContext init (browsers require user gesture)
  // ---------------------------------------------------------------
  function ensureContext() {
    if (!ctx) {
      ctx = new (window.AudioContext || window.webkitAudioContext)();
      masterGain = ctx.createGain();
      masterGain.gain.value = muted ? 0 : volume;
      masterGain.connect(ctx.destination);
    }
    if (ctx.state === 'suspended') {
      ctx.resume();
    }
    return ctx;
  }

  /** True if audio is actually able to play right now */
  function isReady() {
    return ctx && ctx.state === 'running';
  }

  // ---------------------------------------------------------------
  // Utility helpers
  // ---------------------------------------------------------------

  /** Create an oscillator → gain → destination */
  function osc(type, freq, gainVal, dest) {
    const ac = ctx;
    const o = ac.createOscillator();
    const g = ac.createGain();
    o.type = type;
    o.frequency.value = freq;
    g.gain.value = gainVal;
    o.connect(g);
    g.connect(dest);
    return { osc: o, gain: g };
  }

  /** Create filtered noise: noise → filter → gain → destination.
   *  Everything stays internal — nothing leaks to masterGain. */
  function filteredNoise(gainVal, filterType, filterFreq, Q, dest) {
    const ac = ctx;
    // Create a short looping noise buffer
    const bufLen = ac.sampleRate * 2;
    const buf = ac.createBuffer(1, bufLen, ac.sampleRate);
    const data = buf.getChannelData(0);
    for (let i = 0; i < bufLen; i++) data[i] = Math.random() * 2 - 1;
    const src = ac.createBufferSource();
    src.buffer = buf;
    src.loop = true;

    // Route: src → filter → outputGain → dest (no intermediate masterGain leak)
    const filter = ac.createBiquadFilter();
    filter.type = filterType;
    filter.frequency.value = filterFreq;
    filter.Q.value = Q || 1;

    const g = ac.createGain();
    g.gain.value = gainVal;

    src.connect(filter);
    filter.connect(g);
    g.connect(dest);
    return { src, gain: g, filter };
  }

  /** Safely stop an oscillator or buffer source */
  function safeStop(node) {
    try { node.stop(); } catch (e) { /* already stopped */ }
  }

  // ---------------------------------------------------------------
  // Track factory — each returns { start(), stop(fadeSec), gain }
  // ---------------------------------------------------------------

  // --- MENU: Ethereal, mysterious, slow-breathing pad ---
  function trackMenu() {
    const ac = ctx;
    const nodes = [];
    const extras = []; // LFOs and noise sources to stop
    const tg = ac.createGain();
    tg.gain.value = 0;
    tg.connect(masterGain);

    // Deep warm drone (sine only — clean)
    nodes.push(osc('sine', 55, 0.10, tg));
    nodes.push(osc('sine', 82.5, 0.06, tg));

    // Soft filtered pad — triangle through heavy lowpass
    const pad = osc('triangle', 110, 0.03, null);
    const padF = ac.createBiquadFilter();
    padF.type = 'lowpass'; padF.frequency.value = 300; padF.Q.value = 1;
    pad.gain.connect(padF); padF.connect(tg);
    nodes.push(pad);

    // Slow LFO sweeps the pad filter
    const lfo = ac.createOscillator();
    lfo.type = 'sine'; lfo.frequency.value = 0.04;
    const lfoG = ac.createGain(); lfoG.gain.value = 150;
    lfo.connect(lfoG); lfoG.connect(padF.frequency);
    extras.push(lfo);

    // Gentle high shimmer
    nodes.push(osc('sine', 880, 0.008, tg));
    nodes.push(osc('sine', 1320, 0.005, tg));

    // Very quiet filtered wind
    const wind = filteredNoise(0.006, 'bandpass', 600, 3, tg);
    extras.push(wind.src);

    return {
      start() {
        nodes.forEach(n => n.osc.start());
        extras.forEach(e => e.start());
      },
      stop(fade) {
        const t = ac.currentTime;
        tg.gain.setValueAtTime(tg.gain.value, t);
        tg.gain.linearRampToValueAtTime(0, t + fade);
        setTimeout(() => {
          nodes.forEach(n => safeStop(n.osc));
          extras.forEach(e => safeStop(e));
          tg.disconnect();
        }, fade * 1000 + 200);
      },
      gain: tg,
    };
  }

  // --- THE SPRAWL: Gritty urban hum, distant city ---
  function trackSprawl() {
    const ac = ctx;
    const nodes = [];
    const extras = [];
    const tg = ac.createGain();
    tg.gain.value = 0;
    tg.connect(masterGain);

    // Low city drone — filtered triangle
    const d1 = osc('triangle', 45, 0.06, null);
    const dF = ac.createBiquadFilter();
    dF.type = 'lowpass'; dF.frequency.value = 120; dF.Q.value = 1;
    d1.gain.connect(dF); dF.connect(tg);
    nodes.push(d1);

    // Mid warmth
    nodes.push(osc('sine', 65, 0.04, tg));
    nodes.push(osc('sine', 98, 0.025, tg));

    // Quiet rain/static — heavily filtered
    const rain = filteredNoise(0.005, 'bandpass', 4000, 8, tg);
    extras.push(rain.src);

    // Distant metallic ping (periodic)
    let pingTimer;

    return {
      start() {
        nodes.forEach(n => n.osc.start());
        extras.forEach(e => e.start());
        const schedulePing = () => {
          if (!ctx || muted) { pingTimer = setTimeout(schedulePing, 5000); return; }
          const p = osc('sine', 1200 + Math.random() * 600, 0, tg);
          p.osc.start();
          const t = ac.currentTime;
          p.gain.gain.setValueAtTime(0.012, t);
          p.gain.gain.exponentialRampToValueAtTime(0.0001, t + 2);
          setTimeout(() => safeStop(p.osc), 2500);
          pingTimer = setTimeout(schedulePing, 5000 + Math.random() * 7000);
        };
        pingTimer = setTimeout(schedulePing, 3000);
      },
      stop(fade) {
        clearTimeout(pingTimer);
        const t = ac.currentTime;
        tg.gain.setValueAtTime(tg.gain.value, t);
        tg.gain.linearRampToValueAtTime(0, t + fade);
        setTimeout(() => {
          nodes.forEach(n => safeStop(n.osc));
          extras.forEach(e => safeStop(e));
          tg.disconnect();
        }, fade * 1000 + 200);
      },
      gain: tg,
    };
  }

  // --- NEON ROW: Warm synth pad, vibrant ---
  function trackNeonRow() {
    const ac = ctx;
    const nodes = [];
    const extras = [];
    const tg = ac.createGain();
    tg.gain.value = 0;
    tg.connect(masterGain);

    // Warm bass
    nodes.push(osc('sine', 73.4, 0.07, tg));
    nodes.push(osc('sine', 146.8, 0.025, tg));

    // Filtered synth chord (Dm7) — triangle through lowpass for warmth
    [293.66, 349.23, 440, 523.25].forEach(freq => {
      const o = osc('triangle', freq, 0.01, null);
      const f = ac.createBiquadFilter();
      f.type = 'lowpass'; f.frequency.value = 500; f.Q.value = 1;
      o.gain.connect(f); f.connect(tg);
      o.osc.detune.value = (Math.random() - 0.5) * 8;
      nodes.push(o);
    });

    // Very subtle crowd ambience
    const crowd = filteredNoise(0.004, 'bandpass', 1200, 6, tg);
    extras.push(crowd.src);

    // Occasional soft neon hum
    let buzzTimer;

    return {
      start() {
        nodes.forEach(n => n.osc.start());
        extras.forEach(e => e.start());
        const scheduleBuzz = () => {
          if (!ctx || muted) { buzzTimer = setTimeout(scheduleBuzz, 6000); return; }
          const b = osc('sine', 120, 0, tg);
          b.osc.start();
          const t = ac.currentTime;
          b.gain.gain.setValueAtTime(0.015, t);
          b.gain.gain.exponentialRampToValueAtTime(0.0001, t + 1.2);
          setTimeout(() => safeStop(b.osc), 1500);
          buzzTimer = setTimeout(scheduleBuzz, 6000 + Math.random() * 8000);
        };
        buzzTimer = setTimeout(scheduleBuzz, 4000);
      },
      stop(fade) {
        clearTimeout(buzzTimer);
        const t = ac.currentTime;
        tg.gain.setValueAtTime(tg.gain.value, t);
        tg.gain.linearRampToValueAtTime(0, t + fade);
        setTimeout(() => {
          nodes.forEach(n => safeStop(n.osc));
          extras.forEach(e => safeStop(e));
          tg.disconnect();
        }, fade * 1000 + 200);
      },
      gain: tg,
    };
  }

  // --- THE UNDERCROFT: Deep, ominous, cavernous ---
  function trackUndercroft() {
    const ac = ctx;
    const nodes = [];
    const extras = [];
    const tg = ac.createGain();
    tg.gain.value = 0;
    tg.connect(masterGain);

    // Deep sub-bass
    nodes.push(osc('sine', 35, 0.10, tg));
    nodes.push(osc('sine', 52, 0.05, tg));

    // Eerie wobbling tone
    const eerie = osc('sine', 330, 0.012, tg);
    nodes.push(eerie);
    const lfo = ac.createOscillator();
    lfo.type = 'sine'; lfo.frequency.value = 0.12;
    const lfoG = ac.createGain(); lfoG.gain.value = 6;
    lfo.connect(lfoG); lfoG.connect(eerie.osc.frequency);
    extras.push(lfo);

    // Dark low rumble noise
    const dark = filteredNoise(0.006, 'lowpass', 200, 2, tg);
    extras.push(dark.src);

    // Water drip sounds
    let dripTimer;

    return {
      start() {
        nodes.forEach(n => n.osc.start());
        extras.forEach(e => e.start());
        const scheduleDrip = () => {
          if (!ctx || muted) { dripTimer = setTimeout(scheduleDrip, 3000); return; }
          const freq = 1800 + Math.random() * 1500;
          const d = osc('sine', freq, 0, tg);
          d.osc.start();
          const t = ac.currentTime;
          d.gain.gain.setValueAtTime(0.02, t);
          d.gain.gain.exponentialRampToValueAtTime(0.0001, t + 0.4);
          d.osc.frequency.exponentialRampToValueAtTime(freq * 0.6, t + 0.4);
          setTimeout(() => safeStop(d.osc), 600);
          dripTimer = setTimeout(scheduleDrip, 2500 + Math.random() * 5000);
        };
        dripTimer = setTimeout(scheduleDrip, 2000);
      },
      stop(fade) {
        clearTimeout(dripTimer);
        const t = ac.currentTime;
        tg.gain.setValueAtTime(tg.gain.value, t);
        tg.gain.linearRampToValueAtTime(0, t + fade);
        setTimeout(() => {
          nodes.forEach(n => safeStop(n.osc));
          extras.forEach(e => safeStop(e));
          tg.disconnect();
        }, fade * 1000 + 200);
      },
      gain: tg,
    };
  }

  // --- SECTOR 7: Tense, restricted, military ---
  function trackSector7() {
    const ac = ctx;
    const nodes = [];
    const extras = [];
    const tg = ac.createGain();
    tg.gain.value = 0;
    tg.connect(masterGain);

    // Tense filtered drone
    const d1 = osc('triangle', 55, 0.05, null);
    const dF = ac.createBiquadFilter();
    dF.type = 'lowpass'; dF.frequency.value = 100; dF.Q.value = 1;
    d1.gain.connect(dF); dF.connect(tg);
    nodes.push(d1);

    // Dissonant interval — close frequencies for unease
    nodes.push(osc('sine', 82.4, 0.04, tg));
    nodes.push(osc('sine', 87.3, 0.025, tg));

    // Slow heartbeat-like pulse via amplitude modulation
    const pulse = osc('sine', 40, 0, tg);
    nodes.push(pulse);
    const pulseLfo = ac.createOscillator();
    pulseLfo.type = 'sine'; pulseLfo.frequency.value = 0.8;
    const pulseLfoG = ac.createGain(); pulseLfoG.gain.value = 0.03;
    pulseLfo.connect(pulseLfoG); pulseLfoG.connect(pulse.gain.gain);
    extras.push(pulseLfo);

    // Very quiet high static
    const staticN = filteredNoise(0.003, 'bandpass', 6000, 12, tg);
    extras.push(staticN.src);

    // Distant alarm ping
    let alarmTimer;

    return {
      start() {
        nodes.forEach(n => n.osc.start());
        extras.forEach(e => e.start());
        const scheduleAlarm = () => {
          if (!ctx || muted) { alarmTimer = setTimeout(scheduleAlarm, 8000); return; }
          const a = osc('sine', 1500, 0, tg);
          a.osc.start();
          const t = ac.currentTime;
          a.gain.gain.setValueAtTime(0.015, t);
          a.gain.gain.linearRampToValueAtTime(0.0001, t + 0.12);
          setTimeout(() => safeStop(a.osc), 400);
          alarmTimer = setTimeout(scheduleAlarm, 8000 + Math.random() * 6000);
        };
        alarmTimer = setTimeout(scheduleAlarm, 5000);
      },
      stop(fade) {
        clearTimeout(alarmTimer);
        const t = ac.currentTime;
        tg.gain.setValueAtTime(tg.gain.value, t);
        tg.gain.linearRampToValueAtTime(0, t + fade);
        setTimeout(() => {
          nodes.forEach(n => safeStop(n.osc));
          extras.forEach(e => safeStop(e));
          tg.disconnect();
        }, fade * 1000 + 200);
      },
      gain: tg,
    };
  }

  // --- THE RESONANCE: Mystical, harmonic, otherworldly ---
  function trackResonance() {
    const ac = ctx;
    const nodes = [];
    const extras = [];
    const tg = ac.createGain();
    tg.gain.value = 0;
    tg.connect(masterGain);

    // Pure harmonic series on A — with gentle beating
    [110, 220, 330, 440, 550].forEach((freq, i) => {
      const vol = 0.04 / (i + 1);
      nodes.push(osc('sine', freq, vol, tg));
      if (i > 0) {
        nodes.push(osc('sine', freq + 0.4 * (i + 1), vol * 0.5, tg));
      }
    });

    // Slow shimmer modulation
    const shimmer = osc('sine', 1760, 0.005, tg);
    nodes.push(shimmer);
    const shimLfo = ac.createOscillator();
    shimLfo.type = 'sine'; shimLfo.frequency.value = 0.2;
    const shimLfoG = ac.createGain(); shimLfoG.gain.value = 0.005;
    shimLfo.connect(shimLfoG); shimLfoG.connect(shimmer.gain.gain);
    extras.push(shimLfo);

    // Quiet breath noise
    const breath = filteredNoise(0.003, 'bandpass', 1500, 8, tg);
    extras.push(breath.src);

    // Crystal chime
    let chimeTimer;

    return {
      start() {
        nodes.forEach(n => n.osc.start());
        extras.forEach(e => e.start());
        const scheduleChime = () => {
          if (!ctx || muted) { chimeTimer = setTimeout(scheduleChime, 4000); return; }
          const freqs = [523.25, 659.25, 783.99, 1046.5];
          const f = freqs[Math.floor(Math.random() * freqs.length)];
          const c = osc('sine', f, 0, tg);
          c.osc.start();
          const t = ac.currentTime;
          c.gain.gain.setValueAtTime(0.02, t);
          c.gain.gain.exponentialRampToValueAtTime(0.0001, t + 3);
          setTimeout(() => safeStop(c.osc), 3500);
          chimeTimer = setTimeout(scheduleChime, 4000 + Math.random() * 6000);
        };
        chimeTimer = setTimeout(scheduleChime, 3000);
      },
      stop(fade) {
        clearTimeout(chimeTimer);
        const t = ac.currentTime;
        tg.gain.setValueAtTime(tg.gain.value, t);
        tg.gain.linearRampToValueAtTime(0, t + fade);
        setTimeout(() => {
          nodes.forEach(n => safeStop(n.osc));
          extras.forEach(e => safeStop(e));
          tg.disconnect();
        }, fade * 1000 + 200);
      },
      gain: tg,
    };
  }

  // --- THE SPIRE: Corporate, cold, digital ---
  function trackSpire() {
    const ac = ctx;
    const nodes = [];
    const extras = [];
    const tg = ac.createGain();
    tg.gain.value = 0;
    tg.connect(masterGain);

    // Clean bass
    nodes.push(osc('sine', 65.4, 0.07, tg));

    // Cold chord (Cm add9) — sine for clarity
    [130.8, 155.6, 196, 293.66].forEach(freq => {
      nodes.push(osc('sine', freq, 0.018, tg));
    });

    // Slow filtered high tone sweep
    const hi = osc('sine', 2000, 0.004, null);
    const hiF = ac.createBiquadFilter();
    hiF.type = 'bandpass'; hiF.frequency.value = 2000; hiF.Q.value = 15;
    hi.gain.connect(hiF); hiF.connect(tg);
    nodes.push(hi);

    const hiLfo = ac.createOscillator();
    hiLfo.type = 'sine'; hiLfo.frequency.value = 0.06;
    const hiLfoG = ac.createGain(); hiLfoG.gain.value = 800;
    hiLfo.connect(hiLfoG); hiLfoG.connect(hiF.frequency);
    extras.push(hiLfo);

    // Very faint clinical hum
    const hum = filteredNoise(0.002, 'bandpass', 400, 10, tg);
    extras.push(hum.src);

    // Digital blip
    let blipTimer;

    return {
      start() {
        nodes.forEach(n => n.osc.start());
        extras.forEach(e => e.start());
        const scheduleBlip = () => {
          if (!ctx || muted) { blipTimer = setTimeout(scheduleBlip, 4000); return; }
          const b = osc('sine', 2200 + Math.random() * 800, 0, tg);
          b.osc.start();
          const t = ac.currentTime;
          b.gain.gain.setValueAtTime(0.01, t);
          b.gain.gain.exponentialRampToValueAtTime(0.0001, t + 0.1);
          setTimeout(() => safeStop(b.osc), 300);
          blipTimer = setTimeout(scheduleBlip, 3500 + Math.random() * 5000);
        };
        blipTimer = setTimeout(scheduleBlip, 3000);
      },
      stop(fade) {
        clearTimeout(blipTimer);
        const t = ac.currentTime;
        tg.gain.setValueAtTime(tg.gain.value, t);
        tg.gain.linearRampToValueAtTime(0, t + fade);
        setTimeout(() => {
          nodes.forEach(n => safeStop(n.osc));
          extras.forEach(e => safeStop(e));
          tg.disconnect();
        }, fade * 1000 + 200);
      },
      gain: tg,
    };
  }

  // ---------------------------------------------------------------
  // Track registry
  // ---------------------------------------------------------------
  const TRACKS = {
    'menu':            trackMenu,
    'The Sprawl':      trackSprawl,
    '\u8513\u57CE':    trackSprawl,
    'Neon Row':        trackNeonRow,
    '\u9713\u8679\u8857': trackNeonRow,
    'The Undercroft':  trackUndercroft,
    '\u5E95\u6E0A':    trackUndercroft,
    'Sector 7':        trackSector7,
    '\u7B2C\u4E03\u533A': trackSector7,
    'The Resonance':   trackResonance,
    '\u5171\u9E23\u6240': trackResonance,
    'The Spire':       trackSpire,
    '\u5C16\u5854':    trackSpire,
  };

  function resolveTrack(name) {
    if (!name) return null;
    if (TRACKS[name]) return name;
    const lower = name.toLowerCase();
    for (const key of Object.keys(TRACKS)) {
      if (key.toLowerCase() === lower) return key;
    }
    return null;
  }

  // ---------------------------------------------------------------
  // Core: switch track with crossfade
  // ---------------------------------------------------------------
  function switchTo(trackName) {
    const resolved = resolveTrack(trackName);
    if (!resolved) return;

    ensureContext();

    // If AudioContext is still suspended (no user gesture yet),
    // remember the request and retry when context becomes active.
    if (ctx.state !== 'running') {
      _pendingTrack = resolved;
      // Listen for context state change
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

    // Already playing this track — skip
    if (resolved === currentTrackName && currentTrack) return;

    // Fade out current
    if (currentTrack) {
      currentTrack.stop(fadeDuration);
      currentTrack = null;
    }

    // Start new track with fade in
    const factory = TRACKS[resolved];
    if (!factory) return;

    const track = factory();
    const t = ctx.currentTime;
    track.gain.gain.setValueAtTime(0, t);
    track.gain.gain.linearRampToValueAtTime(1.0, t + fadeDuration);
    track.start();

    currentTrack = track;
    currentTrackName = resolved;
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
      currentTrack.stop(fadeDuration);
      currentTrack = null;
      currentTrackName = null;
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

  return {
    switchTo,
    updateFromSession,
    playMenu,
    stopAll,
    setVolume,
    getVolume,
    toggleMute,
    isMuted,
  };
})();
