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
      masterGain.gain.value = volume;
      masterGain.connect(ctx.destination);
    }
    if (ctx.state === 'suspended') ctx.resume();
    return ctx;
  }

  // ---------------------------------------------------------------
  // Track definitions — each returns { start(), stop(fadeOut) }
  // ---------------------------------------------------------------

  // Utility: create an oscillator routed through a gain node
  function osc(type, freq, gainVal, dest) {
    const ac = ensureContext();
    const o = ac.createOscillator();
    const g = ac.createGain();
    o.type = type;
    o.frequency.value = freq;
    g.gain.value = gainVal;
    o.connect(g);
    g.connect(dest || masterGain);
    return { osc: o, gain: g };
  }

  // Utility: create a noise buffer source
  function noiseSource(duration, gainVal, dest) {
    const ac = ensureContext();
    const bufferSize = ac.sampleRate * duration;
    const buffer = ac.createBuffer(1, bufferSize, ac.sampleRate);
    const data = buffer.getChannelData(0);
    for (let i = 0; i < bufferSize; i++) data[i] = Math.random() * 2 - 1;
    const src = ac.createBufferSource();
    src.buffer = buffer;
    src.loop = true;
    const g = ac.createGain();
    g.gain.value = gainVal;
    src.connect(g);
    g.connect(dest || masterGain);
    return { src, gain: g };
  }

  // Utility: create a filtered noise
  function filteredNoise(gainVal, filterType, filterFreq, Q, dest) {
    const ac = ensureContext();
    const n = noiseSource(2, 1.0, null);
    const filter = ac.createBiquadFilter();
    filter.type = filterType;
    filter.frequency.value = filterFreq;
    filter.Q.value = Q || 1;
    n.gain.disconnect();
    n.gain.connect(filter);
    const g = ac.createGain();
    g.gain.value = gainVal;
    filter.connect(g);
    g.connect(dest || masterGain);
    return { src: n.src, gain: g, filter };
  }

  // Utility: create a reverb-like effect using delay feedback
  function createDelay(delayTime, feedback, dest) {
    const ac = ensureContext();
    const delay = ac.createDelay(5);
    delay.delayTime.value = delayTime;
    const fb = ac.createGain();
    fb.gain.value = feedback;
    delay.connect(fb);
    fb.connect(delay);
    delay.connect(dest || masterGain);
    return delay;
  }

  // --- MENU: Ethereal, mysterious pad with slow sweep ---
  function trackMenu() {
    const ac = ensureContext();
    const nodes = [];
    const trackGain = ac.createGain();
    trackGain.gain.value = 1.0;
    trackGain.connect(masterGain);

    // Deep drone
    const d1 = osc('sine', 55, 0.12, trackGain); nodes.push(d1);
    const d2 = osc('sine', 82.5, 0.08, trackGain); nodes.push(d2);

    // Sweep pad
    const pad = osc('sawtooth', 110, 0.0, trackGain); nodes.push(pad);
    const padFilter = ac.createBiquadFilter();
    padFilter.type = 'lowpass';
    padFilter.frequency.value = 400;
    padFilter.Q.value = 5;
    pad.gain.disconnect();
    pad.gain.connect(padFilter);
    padFilter.connect(trackGain);
    pad.gain.gain.value = 0.04;

    // Slow LFO for filter sweep
    const lfo = ac.createOscillator();
    lfo.type = 'sine';
    lfo.frequency.value = 0.05;
    const lfoGain = ac.createGain();
    lfoGain.gain.value = 300;
    lfo.connect(lfoGain);
    lfoGain.connect(padFilter.frequency);

    // High shimmer
    const shimmer = osc('sine', 880, 0.015, trackGain); nodes.push(shimmer);
    const shimmer2 = osc('sine', 1320, 0.01, trackGain); nodes.push(shimmer2);

    // Subtle noise bed
    const wind = filteredNoise(0.02, 'bandpass', 800, 0.5, trackGain);

    return {
      start() {
        nodes.forEach(n => n.osc.start());
        lfo.start();
        wind.src.start();
      },
      stop(fade) {
        const t = ac.currentTime;
        trackGain.gain.linearRampToValueAtTime(0, t + fade);
        setTimeout(() => {
          nodes.forEach(n => { try { n.osc.stop(); } catch(e){} });
          try { lfo.stop(); } catch(e){}
          try { wind.src.stop(); } catch(e){}
          trackGain.disconnect();
        }, fade * 1000 + 100);
      },
      gain: trackGain,
    };
  }

  // --- THE SPRAWL (蔓城): Gritty urban, low hum, distant city ---
  function trackSprawl() {
    const ac = ensureContext();
    const nodes = [];
    const trackGain = ac.createGain();
    trackGain.gain.value = 1.0;
    trackGain.connect(masterGain);

    // Low city drone
    const d1 = osc('sawtooth', 45, 0.0, trackGain); nodes.push(d1);
    const dFilter = ac.createBiquadFilter();
    dFilter.type = 'lowpass'; dFilter.frequency.value = 200; dFilter.Q.value = 2;
    d1.gain.disconnect(); d1.gain.connect(dFilter); dFilter.connect(trackGain);
    d1.gain.gain.value = 0.08;

    // Mid rumble
    const d2 = osc('triangle', 65, 0.06, trackGain); nodes.push(d2);
    const d3 = osc('sine', 98, 0.04, trackGain); nodes.push(d3);

    // Industrial pulse
    const pulse = osc('square', 0.8, 0.0, trackGain); nodes.push(pulse);
    const pulseFilter = ac.createBiquadFilter();
    pulseFilter.type = 'lowpass'; pulseFilter.frequency.value = 100;
    pulse.gain.disconnect(); pulse.gain.connect(pulseFilter); pulseFilter.connect(trackGain);
    pulse.gain.gain.value = 0.03;

    // Rain/static noise
    const rain = filteredNoise(0.025, 'highpass', 3000, 0.3, trackGain);

    // Distant metallic ping (periodic)
    let pingInterval;

    return {
      start() {
        nodes.forEach(n => n.osc.start());
        rain.src.start();
        pingInterval = setInterval(() => {
          if (muted || !ctx) return;
          const p = osc('sine', 1200 + Math.random() * 800, 0, trackGain);
          p.osc.start();
          p.gain.gain.setValueAtTime(0.02, ac.currentTime);
          p.gain.gain.exponentialRampToValueAtTime(0.001, ac.currentTime + 1.5);
          setTimeout(() => { try { p.osc.stop(); } catch(e){} }, 2000);
        }, 4000 + Math.random() * 6000);
      },
      stop(fade) {
        const t = ac.currentTime;
        trackGain.gain.linearRampToValueAtTime(0, t + fade);
        clearInterval(pingInterval);
        setTimeout(() => {
          nodes.forEach(n => { try { n.osc.stop(); } catch(e){} });
          try { rain.src.stop(); } catch(e){}
          trackGain.disconnect();
        }, fade * 1000 + 100);
      },
      gain: trackGain,
    };
  }

  // --- NEON ROW (霓虹街): Vibrant, neon-drenched, synth-heavy ---
  function trackNeonRow() {
    const ac = ensureContext();
    const nodes = [];
    const trackGain = ac.createGain();
    trackGain.gain.value = 1.0;
    trackGain.connect(masterGain);

    // Warm bass
    const bass = osc('sine', 73.4, 0.1, trackGain); nodes.push(bass);
    const bass2 = osc('triangle', 146.8, 0.04, trackGain); nodes.push(bass2);

    // Synth pad chord (Dm7-ish)
    const chordNotes = [293.66, 349.23, 440, 523.25]; // D F A C
    chordNotes.forEach(freq => {
      const o = osc('sawtooth', freq, 0.0, trackGain); nodes.push(o);
      const f = ac.createBiquadFilter();
      f.type = 'lowpass'; f.frequency.value = 600; f.Q.value = 3;
      o.gain.disconnect(); o.gain.connect(f); f.connect(trackGain);
      o.gain.gain.value = 0.015;
      // Slight detune for richness
      o.osc.detune.value = (Math.random() - 0.5) * 10;
    });

    // Pulsing rhythm LFO
    const lfo = ac.createOscillator();
    lfo.type = 'square'; lfo.frequency.value = 2;
    const lfoGain = ac.createGain();
    lfoGain.gain.value = 0.02;
    lfo.connect(lfoGain);

    // Crowd/ambience noise
    const crowd = filteredNoise(0.015, 'bandpass', 1500, 0.8, trackGain);

    // Occasional neon buzz
    let buzzInterval;

    return {
      start() {
        nodes.forEach(n => n.osc.start());
        lfo.start();
        crowd.src.start();
        buzzInterval = setInterval(() => {
          if (muted || !ctx) return;
          const buzz = osc('sawtooth', 60, 0, trackGain);
          const bf = ac.createBiquadFilter();
          bf.type = 'bandpass'; bf.frequency.value = 120; bf.Q.value = 10;
          buzz.gain.disconnect(); buzz.gain.connect(bf); bf.connect(trackGain);
          buzz.osc.start();
          buzz.gain.gain.setValueAtTime(0.03, ac.currentTime);
          buzz.gain.gain.exponentialRampToValueAtTime(0.001, ac.currentTime + 0.8);
          setTimeout(() => { try { buzz.osc.stop(); } catch(e){} }, 1000);
        }, 5000 + Math.random() * 8000);
      },
      stop(fade) {
        const t = ac.currentTime;
        trackGain.gain.linearRampToValueAtTime(0, t + fade);
        clearInterval(buzzInterval);
        setTimeout(() => {
          nodes.forEach(n => { try { n.osc.stop(); } catch(e){} });
          try { lfo.stop(); } catch(e){}
          try { crowd.src.stop(); } catch(e){}
          trackGain.disconnect();
        }, fade * 1000 + 100);
      },
      gain: trackGain,
    };
  }

  // --- THE UNDERCROFT (底渊): Deep, ominous, dripping cave ---
  function trackUndercroft() {
    const ac = ensureContext();
    const nodes = [];
    const trackGain = ac.createGain();
    trackGain.gain.value = 1.0;
    trackGain.connect(masterGain);

    // Very deep sub-bass
    const sub = osc('sine', 32, 0.15, trackGain); nodes.push(sub);
    const sub2 = osc('sine', 48, 0.08, trackGain); nodes.push(sub2);

    // Eerie high tone
    const eerie = osc('sine', 660, 0.0, trackGain); nodes.push(eerie);
    const eerieFilter = ac.createBiquadFilter();
    eerieFilter.type = 'bandpass'; eerieFilter.frequency.value = 700; eerieFilter.Q.value = 15;
    eerie.gain.disconnect(); eerie.gain.connect(eerieFilter); eerieFilter.connect(trackGain);
    eerie.gain.gain.value = 0.02;

    // Slow wobble
    const lfo = ac.createOscillator();
    lfo.type = 'sine'; lfo.frequency.value = 0.15;
    const lfoGain = ac.createGain();
    lfoGain.gain.value = 8;
    lfo.connect(lfoGain);
    lfoGain.connect(eerie.osc.frequency);

    // Dark noise floor
    const dark = filteredNoise(0.02, 'lowpass', 400, 1, trackGain);

    // Water drip sounds
    let dripInterval;

    return {
      start() {
        nodes.forEach(n => n.osc.start());
        lfo.start();
        dark.src.start();
        dripInterval = setInterval(() => {
          if (muted || !ctx) return;
          const freq = 2000 + Math.random() * 2000;
          const drip = osc('sine', freq, 0, trackGain);
          drip.osc.start();
          drip.gain.gain.setValueAtTime(0.04, ac.currentTime);
          drip.gain.gain.exponentialRampToValueAtTime(0.001, ac.currentTime + 0.3);
          drip.osc.frequency.exponentialRampToValueAtTime(freq * 0.5, ac.currentTime + 0.3);
          setTimeout(() => { try { drip.osc.stop(); } catch(e){} }, 500);
        }, 2000 + Math.random() * 4000);
      },
      stop(fade) {
        const t = ac.currentTime;
        trackGain.gain.linearRampToValueAtTime(0, t + fade);
        clearInterval(dripInterval);
        setTimeout(() => {
          nodes.forEach(n => { try { n.osc.stop(); } catch(e){} });
          try { lfo.stop(); } catch(e){}
          try { dark.src.stop(); } catch(e){}
          trackGain.disconnect();
        }, fade * 1000 + 100);
      },
      gain: trackGain,
    };
  }

  // --- SECTOR 7 (第七区): Military, tense, restricted facility ---
  function trackSector7() {
    const ac = ensureContext();
    const nodes = [];
    const trackGain = ac.createGain();
    trackGain.gain.value = 1.0;
    trackGain.connect(masterGain);

    // Tense drone
    const d1 = osc('sawtooth', 55, 0.0, trackGain); nodes.push(d1);
    const df = ac.createBiquadFilter();
    df.type = 'lowpass'; df.frequency.value = 150; df.Q.value = 4;
    d1.gain.disconnect(); d1.gain.connect(df); df.connect(trackGain);
    d1.gain.gain.value = 0.07;

    // Dissonant interval
    const d2 = osc('sine', 82.4, 0.06, trackGain); nodes.push(d2);
    const d3 = osc('sine', 87.3, 0.04, trackGain); nodes.push(d3); // Tritone tension

    // Rhythmic pulse — heartbeat-like
    const pulse = osc('sine', 40, 0.0, trackGain); nodes.push(pulse);
    const pulseLfo = ac.createOscillator();
    pulseLfo.type = 'square'; pulseLfo.frequency.value = 1.2;
    const pulseLfoGain = ac.createGain();
    pulseLfoGain.gain.value = 0.06;
    pulseLfo.connect(pulseLfoGain);
    pulseLfoGain.connect(pulse.gain.gain);

    // Static / radio interference
    const staticN = filteredNoise(0.015, 'highpass', 5000, 1, trackGain);

    // Alarm-like ping
    let alarmInterval;

    return {
      start() {
        nodes.forEach(n => n.osc.start());
        pulseLfo.start();
        staticN.src.start();
        alarmInterval = setInterval(() => {
          if (muted || !ctx) return;
          const alarm = osc('sine', 1500, 0, trackGain);
          alarm.osc.start();
          alarm.gain.gain.setValueAtTime(0.025, ac.currentTime);
          alarm.gain.gain.linearRampToValueAtTime(0, ac.currentTime + 0.15);
          setTimeout(() => {
            alarm.gain.gain.setValueAtTime(0.025, ac.currentTime);
            alarm.gain.gain.linearRampToValueAtTime(0, ac.currentTime + 0.15);
          }, 200);
          setTimeout(() => { try { alarm.osc.stop(); } catch(e){} }, 600);
        }, 8000 + Math.random() * 5000);
      },
      stop(fade) {
        const t = ac.currentTime;
        trackGain.gain.linearRampToValueAtTime(0, t + fade);
        clearInterval(alarmInterval);
        setTimeout(() => {
          nodes.forEach(n => { try { n.osc.stop(); } catch(e){} });
          try { pulseLfo.stop(); } catch(e){}
          try { staticN.src.stop(); } catch(e){}
          trackGain.disconnect();
        }, fade * 1000 + 100);
      },
      gain: trackGain,
    };
  }

  // --- THE RESONANCE (共鸣所): Mystical, otherworldly, harmonic ---
  function trackResonance() {
    const ac = ensureContext();
    const nodes = [];
    const trackGain = ac.createGain();
    trackGain.gain.value = 1.0;
    trackGain.connect(masterGain);

    // Pure harmonic series on A
    const harmonics = [110, 220, 330, 440, 550, 660];
    harmonics.forEach((freq, i) => {
      const vol = 0.06 / (i + 1);
      const o = osc('sine', freq, vol, trackGain); nodes.push(o);
      // Gentle beating — slight detune
      if (i > 0) {
        const o2 = osc('sine', freq + 0.5 * (i + 1), vol * 0.6, trackGain);
        nodes.push(o2);
      }
    });

    // Ethereal shimmer
    const shimmer = osc('sine', 1760, 0.008, trackGain); nodes.push(shimmer);
    const shimLfo = ac.createOscillator();
    shimLfo.type = 'sine'; shimLfo.frequency.value = 0.3;
    const shimLfoG = ac.createGain();
    shimLfoG.gain.value = 0.008;
    shimLfo.connect(shimLfoG);
    shimLfoG.connect(shimmer.gain.gain);

    // Breath-like wind
    const breath = filteredNoise(0.01, 'bandpass', 2000, 2, trackGain);

    // Crystal chime
    let chimeInterval;

    return {
      start() {
        nodes.forEach(n => n.osc.start());
        shimLfo.start();
        breath.src.start();
        chimeInterval = setInterval(() => {
          if (muted || !ctx) return;
          const notes = [523.25, 659.25, 783.99, 1046.5, 1318.5];
          const note = notes[Math.floor(Math.random() * notes.length)];
          const chime = osc('sine', note, 0, trackGain);
          chime.osc.start();
          chime.gain.gain.setValueAtTime(0.035, ac.currentTime);
          chime.gain.gain.exponentialRampToValueAtTime(0.001, ac.currentTime + 2.5);
          setTimeout(() => { try { chime.osc.stop(); } catch(e){} }, 3000);
        }, 3000 + Math.random() * 5000);
      },
      stop(fade) {
        const t = ac.currentTime;
        trackGain.gain.linearRampToValueAtTime(0, t + fade);
        clearInterval(chimeInterval);
        setTimeout(() => {
          nodes.forEach(n => { try { n.osc.stop(); } catch(e){} });
          try { shimLfo.stop(); } catch(e){}
          try { breath.src.stop(); } catch(e){}
          trackGain.disconnect();
        }, fade * 1000 + 100);
      },
      gain: trackGain,
    };
  }

  // --- THE SPIRE (尖塔): Corporate, cold, digital, high-tech ---
  function trackSpire() {
    const ac = ensureContext();
    const nodes = [];
    const trackGain = ac.createGain();
    trackGain.gain.value = 1.0;
    trackGain.connect(masterGain);

    // Clean digital bass
    const bass = osc('sine', 65.4, 0.1, trackGain); nodes.push(bass);

    // Cold chord (Cm add9)
    const chordFreqs = [130.8, 155.6, 196, 293.66]; // C Eb G D
    chordFreqs.forEach(freq => {
      const o = osc('triangle', freq, 0.025, trackGain); nodes.push(o);
    });

    // High frequency data stream
    const data = osc('square', 8000, 0.0, trackGain); nodes.push(data);
    const dataFilter = ac.createBiquadFilter();
    dataFilter.type = 'bandpass'; dataFilter.frequency.value = 8000; dataFilter.Q.value = 20;
    data.gain.disconnect(); data.gain.connect(dataFilter); dataFilter.connect(trackGain);
    data.gain.gain.value = 0.005;

    // LFO for data stream
    const dataLfo = ac.createOscillator();
    dataLfo.type = 'sine'; dataLfo.frequency.value = 0.08;
    const dataLfoG = ac.createGain();
    dataLfoG.gain.value = 4000;
    dataLfo.connect(dataLfoG);
    dataLfoG.connect(dataFilter.frequency);

    // Clinical hum
    const hum = filteredNoise(0.008, 'bandpass', 400, 5, trackGain);

    // Digital blip
    let blipInterval;

    return {
      start() {
        nodes.forEach(n => n.osc.start());
        dataLfo.start();
        hum.src.start();
        blipInterval = setInterval(() => {
          if (muted || !ctx) return;
          const blip = osc('sine', 2400 + Math.random() * 1200, 0, trackGain);
          blip.osc.start();
          blip.gain.gain.setValueAtTime(0.02, ac.currentTime);
          blip.gain.gain.exponentialRampToValueAtTime(0.001, ac.currentTime + 0.08);
          setTimeout(() => {
            const blip2 = osc('sine', 1800 + Math.random() * 600, 0, trackGain);
            blip2.osc.start();
            blip2.gain.gain.setValueAtTime(0.015, ac.currentTime);
            blip2.gain.gain.exponentialRampToValueAtTime(0.001, ac.currentTime + 0.06);
            setTimeout(() => { try { blip2.osc.stop(); } catch(e){} }, 200);
          }, 100);
          setTimeout(() => { try { blip.osc.stop(); } catch(e){} }, 300);
        }, 3000 + Math.random() * 4000);
      },
      stop(fade) {
        const t = ac.currentTime;
        trackGain.gain.linearRampToValueAtTime(0, t + fade);
        clearInterval(blipInterval);
        setTimeout(() => {
          nodes.forEach(n => { try { n.osc.stop(); } catch(e){} });
          try { dataLfo.stop(); } catch(e){}
          try { hum.src.stop(); } catch(e){}
          trackGain.disconnect();
        }, fade * 1000 + 100);
      },
      gain: trackGain,
    };
  }

  // ---------------------------------------------------------------
  // Track registry — maps district names to factory functions
  // ---------------------------------------------------------------
  const TRACKS = {
    'menu':            trackMenu,
    'The Sprawl':      trackSprawl,
    '蔓城':            trackSprawl,
    'Neon Row':        trackNeonRow,
    '霓虹街':          trackNeonRow,
    'The Undercroft':  trackUndercroft,
    '底渊':            trackUndercroft,
    'Sector 7':        trackSector7,
    '第七区':          trackSector7,
    'The Resonance':   trackResonance,
    '共鸣所':          trackResonance,
    'The Spire':       trackSpire,
    '尖塔':            trackSpire,
  };

  // Normalize district name to canonical key
  function resolveTrack(name) {
    if (!name) return null;
    if (TRACKS[name]) return name;
    // Check lowercase
    const lower = name.toLowerCase();
    for (const key of Object.keys(TRACKS)) {
      if (key.toLowerCase() === lower) return key;
    }
    return null;
  }

  // ---------------------------------------------------------------
  // Public API
  // ---------------------------------------------------------------

  /** Switch to a track by district name. Crossfades over fadeDuration. */
  function switchTo(trackName) {
    const resolved = resolveTrack(trackName);
    if (!resolved || resolved === currentTrackName) return;

    ensureContext();

    // Fade out current track
    if (currentTrack) {
      currentTrack.stop(fadeDuration);
      currentTrack = null;
    }

    // Start new track with fade in
    const factory = TRACKS[resolved];
    if (!factory) return;

    const track = factory();
    track.gain.gain.setValueAtTime(0, ctx.currentTime);
    track.gain.gain.linearRampToValueAtTime(1.0, ctx.currentTime + fadeDuration);
    track.start();

    currentTrack = track;
    currentTrackName = resolved;
  }

  /** Update based on current game district */
  function updateFromSession(session) {
    if (!session || !session.location) return;
    const district = session.location.district || '';
    if (district) switchTo(district);
  }

  /** Play menu music */
  function playMenu() { switchTo('menu'); }

  /** Stop all music with fade */
  function stopAll() {
    if (currentTrack) {
      currentTrack.stop(fadeDuration);
      currentTrack = null;
      currentTrackName = null;
    }
  }

  /** Set volume 0.0 - 1.0 */
  function setVolume(v) {
    volume = Math.max(0, Math.min(1, v));
    if (masterGain) masterGain.gain.value = muted ? 0 : volume;
  }

  /** Toggle mute */
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
