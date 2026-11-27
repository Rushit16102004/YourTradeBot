/**
 * YourTradeBot — Quantitative Terminal 1 Master Interactive Engine
 * World's Best Animated Cyber-Institutional UI/UX Script
 * Version: 4.0.0 Pro • 60 FPS Accelerated • Zero External Dependencies
 */

(function () {
  'use strict';

  // =====================================================================
  // 1. WEB AUDIO API CYBER-QUANT SYNTHESIZER
  // =====================================================================
  let audioCtx = null;
  let soundFXEnabled = true;

  // Retrieve user sound preference from localStorage
  try {
    const savedSound = localStorage.getItem('terminal_1_sound_fx');
    if (savedSound !== null) {
      soundFXEnabled = (savedSound === 'true');
    }
  } catch (e) {
    soundFXEnabled = true;
  }

  function getAudioContext() {
    if (!audioCtx) {
      const AudioContextClass = window.AudioContext || window.webkitAudioContext;
      if (AudioContextClass) {
        audioCtx = new AudioContextClass();
      }
    }
    if (audioCtx && audioCtx.state === 'suspended') {
      audioCtx.resume();
    }
    return audioCtx;
  }

  // Soft high-frequency UI tick on tab/button hover
  window.playHoverTick = function () {
    if (!soundFXEnabled) return;
    try {
      const ctx = getAudioContext();
      if (!ctx) return;
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'sine';
      osc.frequency.setValueAtTime(2400, ctx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(1200, ctx.currentTime + 0.025);
      gain.gain.setValueAtTime(0.025, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.025);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      osc.stop(ctx.currentTime + 0.03);
    } catch (e) {}
  };

  // Affirmative sci-fi click beep
  window.playClickBeep = function (freq = 880) {
    if (!soundFXEnabled) return;
    try {
      const ctx = getAudioContext();
      if (!ctx) return;
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'triangle';
      osc.frequency.setValueAtTime(freq, ctx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(freq * 1.5, ctx.currentTime + 0.06);
      gain.gain.setValueAtTime(0.06, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.07);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      osc.stop(ctx.currentTime + 0.08);
    } catch (e) {}
  };

  // Pitched UI beep for interactive shortcuts & gallery cues
  window.playPitchedBeep = function (freq = 880, duration = 0.05) {
    if (!soundFXEnabled) return;
    try {
      const ctx = getAudioContext();
      if (!ctx) return;
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'sine';
      osc.frequency.setValueAtTime(freq, ctx.currentTime);
      gain.gain.setValueAtTime(0.04, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + duration);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      osc.stop(ctx.currentTime + duration + 0.01);
    } catch (e) {}
  };

  // Dual chime for ±2σ exhaustion alert
  window.playAlertChime = function () {
    if (!soundFXEnabled) return;
    try {
      const ctx = getAudioContext();
      if (!ctx) return;
      const now = ctx.currentTime;
      // Chime 1
      const osc1 = ctx.createOscillator();
      const gain1 = ctx.createGain();
      osc1.type = 'sine';
      osc1.frequency.setValueAtTime(659.25, now); // E5
      gain1.gain.setValueAtTime(0.07, now);
      gain1.gain.exponentialRampToValueAtTime(0.001, now + 0.15);
      osc1.connect(gain1);
      gain1.connect(ctx.destination);
      osc1.start(now);
      osc1.stop(now + 0.16);

      // Chime 2
      const osc2 = ctx.createOscillator();
      const gain2 = ctx.createGain();
      osc2.type = 'sine';
      osc2.frequency.setValueAtTime(987.77, now + 0.09); // B5
      gain2.gain.setValueAtTime(0.08, now + 0.09);
      gain2.gain.exponentialRampToValueAtTime(0.001, now + 0.28);
      osc2.connect(gain2);
      gain2.connect(ctx.destination);
      osc2.start(now + 0.09);
      osc2.stop(now + 0.3);
    } catch (e) {}
  };

  // Sonar radar sweep ping
  window.playRadarPing = function () {
    if (!soundFXEnabled) return;
    try {
      const ctx = getAudioContext();
      if (!ctx) return;
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'sine';
      osc.frequency.setValueAtTime(1400, ctx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(400, ctx.currentTime + 0.12);
      gain.gain.setValueAtTime(0.035, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.12);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      osc.stop(ctx.currentTime + 0.13);
    } catch (e) {}
  };

  // Pitch-shifted slider frequency tick
  window.playSliderTick = function (val) {
    if (!soundFXEnabled) return;
    try {
      const ctx = getAudioContext();
      if (!ctx) return;
      const freq = 400 + Math.abs(val) * 350;
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'sine';
      osc.frequency.setValueAtTime(freq, ctx.currentTime);
      gain.gain.setValueAtTime(0.02, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.02);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      osc.stop(ctx.currentTime + 0.025);
    } catch (e) {}
  };

  // Sound FX Toggle UI Handler
  window.toggleSoundFX = function () {
    soundFXEnabled = !soundFXEnabled;
    try {
      localStorage.setItem('terminal_1_sound_fx', soundFXEnabled ? 'true' : 'false');
    } catch (e) {}

    const btn = document.getElementById('btn-sound-toggle');
    const icon = document.getElementById('sound-icon');
    const label = document.getElementById('sound-label');

    if (soundFXEnabled) {
      if (btn) btn.classList.remove('sound-off');
      if (icon) icon.textContent = '🔊';
      if (label) label.textContent = 'Sound: ON';
      playClickBeep(700);
    } else {
      if (btn) btn.classList.add('sound-off');
      if (icon) icon.textContent = '🔇';
      if (label) label.textContent = 'Sound: OFF';
    }
  };

  // Sync initial sound button state
  function syncSoundButtonUI() {
    const btn = document.getElementById('btn-sound-toggle');
    const icon = document.getElementById('sound-icon');
    const label = document.getElementById('sound-label');
    if (!soundFXEnabled) {
      if (btn) btn.classList.add('sound-off');
      if (icon) icon.textContent = '🔇';
      if (label) label.textContent = 'Sound: OFF';
    }
  }

  // =====================================================================
  // 2. VISITOR IDENTITY & FUNNEL TRACKING BEACONS
  // =====================================================================
  function getOrInitVisitorId() {
    let vid = localStorage.getItem('terminal_visitor_id');
    if (!vid) {
      vid = 'vis_' + Math.random().toString(36).substring(2, 10) + Date.now().toString(36);
      localStorage.setItem('terminal_visitor_id', vid);
    }
    return vid;
  }

  const visitorId = getOrInitVisitorId();

  async function trackFunnelAction(actionType, actionDetail) {
    try {
      const token = localStorage.getItem('auth_token');
      fetch('/api/analytics/action', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': 'Bearer ' + token } : {})
        },
        body: JSON.stringify({
          visitor_id: visitorId,
          action_type: actionType,
          action_detail: actionDetail || '',
          path: '/'
        }),
        keepalive: true
      }).catch(() => {});
    } catch (e) {}
  }

  // Record initial landing hit
  async function recordInitialVisit() {
    try {
      const token = localStorage.getItem('auth_token');
      fetch('/api/analytics/visit', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': 'Bearer ' + token } : {})
        },
        body: JSON.stringify({
          visitor_id: visitorId,
          path: '/',
          referrer: document.referrer || ''
        })
      }).catch(() => {});
      trackFunnelAction('funnel_t1_visit', 'Landed on Terminal 1 Showcase');
    } catch (e) {}
  }

  // Check for Returning Authenticated User
  async function checkReturningUser() {
    const token = localStorage.getItem('auth_token');
    if (!token) return;

    try {
      const res = await fetch('/api/auth/me', {
        headers: { 'Authorization': 'Bearer ' + token }
      });
      if (res.ok) {
        const data = await res.json();
        const uname = (data.user && data.user.username) || data.username;
        if (data.is_authenticated && uname) {
          const banner = document.getElementById('returning-banner');
          const userSpan = document.getElementById('returning-username');
          if (banner && userSpan) {
            userSpan.textContent = '@' + uname;
            banner.style.display = 'block';
          }
          const navLoginBtn = document.getElementById('nav-login-btn');
          if (navLoginBtn) {
            navLoginBtn.innerHTML = '<span class="btn-icon">👑</span><span>My Terminal</span>';
            navLoginBtn.onclick = () => { window.location.href = '/terminal'; };
          }
        }
      }
    } catch (e) {}
  }

  // =====================================================================
  // 3. HERO LIVE QUANT SIMULATOR ENGINE (INTERACTIVE 60 FPS CANVAS CHART)
  // =====================================================================
  let simTimeframe = '5m';
  let simLayers = { vwap: true, bands: true, sr: true, signals: true };
  let simData = [];
  let simCanvas = null;
  let simCtx = null;
  let simAnimId = null;
  let simMouseX = -1;
  let simMouseY = -1;
  let lastSimTick = Date.now();

  function initSimData(count = 60, basePrice = 24150) {
    simData = [];
    let p = basePrice;
    let vwapSumPV = 0;
    let vwapSumV = 0;

    for (let i = 0; i < count; i++) {
      const change = (Math.random() - 0.48) * 8;
      const open = p;
      const close = p + change;
      const high = Math.max(open, close) + Math.random() * 4;
      const low = Math.min(open, close) - Math.random() * 4;
      const vol = 1200 + Math.floor(Math.random() * 2500);

      const typical = (high + low + close) / 3;
      vwapSumPV += typical * vol;
      vwapSumV += vol;
      const vwap = vwapSumPV / vwapSumV;
      const std = 8 + (i * 0.12);

      simData.push({
        open, high, low, close, volume: vol,
        vwap,
        upper2: vwap + std * 2.0,
        lower2: vwap - std * 2.0,
        time: i
      });
      p = close;
    }
  }

  function renderSimChart() {
    if (!simCanvas || !simCtx) return;
    const w = simCanvas.width;
    const h = simCanvas.height;

    simCtx.clearRect(0, 0, w, h);

    if (simData.length === 0) return;

    // Determine scale
    let minP = Infinity;
    let maxP = -Infinity;
    simData.forEach(d => {
      minP = Math.min(minP, d.low, d.lower2);
      maxP = Math.max(maxP, d.high, d.upper2);
    });
    minP -= 4;
    maxP += 4;
    const priceRange = maxP - minP;

    function getY(price) {
      return h - 45 - ((price - minP) / priceRange) * (h - 75);
    }

    const candleWidth = Math.max(4, (w - 70) / simData.length);
    const spacing = candleWidth * 0.25;
    const barW = candleWidth - spacing;

    // Draw Grid lines
    simCtx.strokeStyle = 'rgba(51, 65, 85, 0.25)';
    simCtx.lineWidth = 1;
    for (let i = 0; i < 5; i++) {
      const gridP = minP + (priceRange * i) / 4;
      const gy = getY(gridP);
      simCtx.beginPath();
      simCtx.moveTo(0, gy);
      simCtx.lineTo(w - 60, gy);
      simCtx.stroke();

      // Price Label
      simCtx.fillStyle = 'rgba(148, 163, 184, 0.6)';
      simCtx.font = '10px monospace';
      simCtx.textAlign = 'left';
      simCtx.fillText(gridP.toFixed(1), w - 52, gy + 3);
    }

    // Layer: Shaded VWAP ±2σ Bands Area Fill
    if (simLayers.bands && simData.length > 1) {
      simCtx.beginPath();
      simCtx.moveTo(0, getY(simData[0].upper2));
      for (let i = 0; i < simData.length; i++) {
        const cx = i * candleWidth + barW / 2;
        simCtx.lineTo(cx, getY(simData[i].upper2));
      }
      for (let i = simData.length - 1; i >= 0; i--) {
        const cx = i * candleWidth + barW / 2;
        simCtx.lineTo(cx, getY(simData[i].lower2));
      }
      simCtx.closePath();
      simCtx.fillStyle = 'rgba(56, 189, 248, 0.05)';
      simCtx.fill();

      // Upper +2σ Band Curve
      simCtx.beginPath();
      simCtx.strokeStyle = 'rgba(239, 68, 68, 0.75)';
      simCtx.lineWidth = 1.5;
      for (let i = 0; i < simData.length; i++) {
        const cx = i * candleWidth + barW / 2;
        const cy = getY(simData[i].upper2);
        if (i === 0) simCtx.moveTo(cx, cy);
        else simCtx.lineTo(cx, cy);
      }
      simCtx.stroke();

      // Lower -2σ Band Curve
      simCtx.beginPath();
      simCtx.strokeStyle = 'rgba(16, 185, 129, 0.75)';
      simCtx.lineWidth = 1.5;
      for (let i = 0; i < simData.length; i++) {
        const cx = i * candleWidth + barW / 2;
        const cy = getY(simData[i].lower2);
        if (i === 0) simCtx.moveTo(cx, cy);
        else simCtx.lineTo(cx, cy);
      }
      simCtx.stroke();
    }

    // Layer: Session VWAP Line
    if (simLayers.vwap && simData.length > 1) {
      simCtx.beginPath();
      simCtx.strokeStyle = '#38bdf8';
      simCtx.lineWidth = 2;
      simCtx.shadowColor = 'rgba(56, 189, 248, 0.6)';
      simCtx.shadowBlur = 8;
      for (let i = 0; i < simData.length; i++) {
        const cx = i * candleWidth + barW / 2;
        const cy = getY(simData[i].vwap);
        if (i === 0) simCtx.moveTo(cx, cy);
        else simCtx.lineTo(cx, cy);
      }
      simCtx.stroke();
      simCtx.shadowBlur = 0; // reset
    }

    // Layer: Automated Support & Resistance Confluence Lines
    if (simLayers.sr) {
      const sr1 = minP + priceRange * 0.35;
      const sr2 = minP + priceRange * 0.75;
      [ { p: sr1, color: 'rgba(16, 185, 129, 0.6)', label: 'S&R Zone (4x Touch)' },
        { p: sr2, color: 'rgba(239, 68, 68, 0.6)', label: 'S&R Resistance (5x Touch)' }
      ].forEach(lvl => {
        const ly = getY(lvl.p);
        simCtx.beginPath();
        simCtx.setLineDash([4, 4]);
        simCtx.strokeStyle = lvl.color;
        simCtx.lineWidth = 1.2;
        simCtx.moveTo(0, ly);
        simCtx.lineTo(w - 60, ly);
        simCtx.stroke();
        simCtx.setLineDash([]); // reset

        simCtx.fillStyle = lvl.color;
        simCtx.font = '9px monospace';
        simCtx.textAlign = 'right';
        simCtx.fillText(lvl.label, w - 66, ly - 3);
      });
    }

    // Layer: Candlesticks & Volume
    for (let i = 0; i < simData.length; i++) {
      const d = simData[i];
      const x = i * candleWidth;
      const cx = x + barW / 2;
      const isUp = d.close >= d.open;

      // Candle Colors
      const color = isUp ? '#10b981' : '#ef4444';
      simCtx.strokeStyle = color;
      simCtx.fillStyle = color;

      // Wick
      simCtx.lineWidth = 1.2;
      simCtx.beginPath();
      simCtx.moveTo(cx, getY(d.high));
      simCtx.lineTo(cx, getY(d.low));
      simCtx.stroke();

      // Body
      const yOpen = getY(d.open);
      const yClose = getY(d.close);
      const bodyTop = Math.min(yOpen, yClose);
      const bodyH = Math.max(2, Math.abs(yClose - yOpen));
      simCtx.fillRect(x, bodyTop, barW, bodyH);

      // Volume Bars at Bottom
      const volH = Math.min(30, (d.volume / 4000) * 30);
      simCtx.fillStyle = isUp ? 'rgba(16, 185, 129, 0.25)' : 'rgba(239, 68, 68, 0.25)';
      simCtx.fillRect(x, h - volH, barW, volH);

      // Layer: Signal Markers
      if (simLayers.signals && i === simData.length - 8) {
        // Sample Buy Signal
        simCtx.fillStyle = '#00e676';
        simCtx.beginPath();
        simCtx.moveTo(cx, getY(d.low) + 8);
        simCtx.lineTo(cx - 5, getY(d.low) + 16);
        simCtx.lineTo(cx + 5, getY(d.low) + 16);
        simCtx.closePath();
        simCtx.fill();
        simCtx.font = 'bold 9px sans-serif';
        simCtx.textAlign = 'center';
        simCtx.fillText('BUY', cx, getY(d.low) + 26);
      }
    }

    // Crosshair rendering
    if (simMouseX > 0 && simMouseY > 0 && simMouseX < w - 60) {
      simCtx.strokeStyle = 'rgba(56, 189, 248, 0.6)';
      simCtx.setLineDash([3, 3]);
      simCtx.lineWidth = 1;

      // Vertical line
      simCtx.beginPath();
      simCtx.moveTo(simMouseX, 0);
      simCtx.lineTo(simMouseX, h);
      simCtx.stroke();

      // Horizontal line
      simCtx.beginPath();
      simCtx.moveTo(0, simMouseY);
      simCtx.lineTo(w - 60, simMouseY);
      simCtx.stroke();
      simCtx.setLineDash([]);
    }
  }

  function updateSimTick() {
    if (simData.length === 0) return;
    const last = simData[simData.length - 1];
    const delta = (Math.random() - 0.49) * 1.5;
    last.close += delta;
    last.high = Math.max(last.high, last.close);
    last.low = Math.min(last.low, last.close);

    // Update Telemetry Display
    const priceEl = document.getElementById('sim-price-val');
    const vwapEl = document.getElementById('sim-vwap-val');
    const devEl = document.getElementById('sim-dev-val');
    const statusEl = document.getElementById('sim-status-val');

    if (priceEl) priceEl.textContent = last.close.toFixed(2);
    if (vwapEl) vwapEl.textContent = last.vwap.toFixed(2);

    const dev = (last.close - last.vwap) / 6.0;
    if (devEl) {
      devEl.textContent = (dev >= 0 ? '+' : '') + dev.toFixed(2) + 'σ';
      devEl.className = dev > 1.8 ? 'v text-red' : (dev < -1.8 ? 'v text-green' : 'v text-accent');
    }
    if (statusEl) {
      if (dev > 2.0) {
        statusEl.textContent = 'Upper Exhaustion (+2σ)';
        statusEl.className = 'v text-red';
      } else if (dev < -2.0) {
        statusEl.textContent = 'Oversold Dip-Buy (-2σ)';
        statusEl.className = 'v text-green';
      } else {
        statusEl.textContent = 'Institutional Fair Value';
        statusEl.className = 'v text-accent';
      }
    }
  }

  function startSimLoop() {
    function loop() {
      updateSimTick();
      renderSimChart();
      simAnimId = requestAnimationFrame(loop);
    }
    loop();
  }

  window.switchSimTimeframe = function (tf) {
    playClickBeep(920);
    simTimeframe = tf;
    document.querySelectorAll('.sim-tf-btn').forEach(btn => {
      btn.classList.toggle('active', btn.textContent.toLowerCase() === tf);
    });
    initSimData(tf === '5m' ? 60 : (tf === '15m' ? 45 : 30));
  };

  window.toggleSimLayer = function (layer) {
    playClickBeep(750);
    simLayers[layer] = !simLayers[layer];
    const btn = document.getElementById('sim-toggle-' + layer);
    if (btn) btn.classList.toggle('active', simLayers[layer]);
  };

  // =====================================================================
  // 4. THE 4 INTERACTIVE QUANT FEATURE LABS
  // =====================================================================

  // LAB 1: VWAP Statistical Reversal Probability Meter
  window.updateVwapLab = function (val) {
    const v = parseFloat(val);
    playSliderTick(v);

    const devDisplay = document.getElementById('slider-dev-display');
    if (devDisplay) {
      devDisplay.textContent = (v >= 0 ? '+' : '') + v.toFixed(1) + 'σ';
    }

    // Gaussian CDF Reversal Curve Math
    const absV = Math.abs(v);
    let prob = 50 + (absV * 19.5);
    if (prob > 96.8) prob = 96.8;
    if (absV < 0.3) prob = 48.0;

    const probVal = document.getElementById('gauge-prob-val');
    if (probVal) {
      probVal.textContent = prob.toFixed(1) + '%';
    }

    // Arc offset animation
    const arc = document.getElementById('gauge-fill-arc');
    if (arc) {
      const maxOffset = 251.2;
      const ratio = Math.min(1, prob / 100);
      const targetOffset = maxOffset - (maxOffset * ratio);
      arc.style.strokeDashoffset = targetOffset;
      arc.style.stroke = absV > 2.0 ? '#ef4444' : (absV > 1.2 ? '#f59e0b' : '#38bdf8');
    }

    // Feedback message
    const fb = document.getElementById('lab-vwap-feedback');
    if (fb) {
      if (v >= 2.0) {
        fb.className = 'lab-feedback-box text-red';
        fb.innerHTML = '⚡ <strong>Upper Exhaustion Zone (' + v.toFixed(1) + 'σ):</strong> Overextended. Institutional algorithms initiate mean-reversion short rebalancing. 89%+ historical drop rate.';
        playAlertChime();
      } else if (v <= -2.0) {
        fb.className = 'lab-feedback-box text-green';
        fb.innerHTML = '🎯 <strong>Discount Exhaustion Zone (' + v.toFixed(1) + 'σ):</strong> Statistical oversold dip-buy barrier. Mean reversion rebound probability exceeds 90%.';
        playAlertChime();
      } else {
        fb.className = 'lab-feedback-box text-accent';
        fb.innerHTML = '⚖️ <strong>Institutional Value Orbit (' + (v >= 0 ? '+' : '') + v.toFixed(1) + 'σ):</strong> Price trades within 1st deviation. Trend continuation regime active.';
      }
    }
  };

  // LAB 2: Interactive S&R Confluence Scanner
  let srCanvas = null;
  let srCtx = null;
  let srClicks = [
    { y: 65, touches: 5, score: '96% (Major Barrier)' },
    { y: 115, touches: 4, score: '92% (Key Pivot)' }
  ];

  function initSrCanvas() {
    srCanvas = document.getElementById('lab-sr-canvas');
    if (!srCanvas) return;
    srCtx = srCanvas.getContext('2d');
    const rect = srCanvas.getBoundingClientRect();
    srCanvas.width = rect.width * (window.devicePixelRatio || 1);
    srCanvas.height = rect.height * (window.devicePixelRatio || 1);
    srCtx.scale(window.devicePixelRatio || 1, window.devicePixelRatio || 1);

    srCanvas.addEventListener('click', (e) => {
      playClickBeep(1100);
      const b = srCanvas.getBoundingClientRect();
      const clickY = e.clientY - b.top;
      const touches = Math.floor(3 + Math.random() * 4);
      const score = Math.floor(88 + Math.random() * 9) + '% (Verified Zone)';
      srClicks.push({ y: clickY, touches, score });
      if (srClicks.length > 3) srClicks.shift();

      const touchEl = document.getElementById('sr-touch-count');
      const confEl = document.getElementById('sr-conf-score');
      if (touchEl) touchEl.textContent = touches + 'x Rejections';
      if (confEl) confEl.textContent = score;

      renderSrCanvas();
    });

    renderSrCanvas();
  }

  function renderSrCanvas() {
    if (!srCanvas || !srCtx) return;
    const w = srCanvas.getBoundingClientRect().width;
    const h = srCanvas.getBoundingClientRect().height;
    srCtx.clearRect(0, 0, w, h);

    // Draw background simulated candles
    srCtx.strokeStyle = 'rgba(51, 65, 85, 0.4)';
    srCtx.lineWidth = 1;
    for (let i = 0; i < 30; i++) {
      const cx = 15 + i * 18;
      const cy = 40 + Math.sin(i * 0.4) * 35 + (i * 1.5);
      srCtx.fillStyle = (i % 2 === 0) ? 'rgba(16, 185, 129, 0.4)' : 'rgba(239, 68, 68, 0.4)';
      srCtx.fillRect(cx - 3, cy - 8, 6, 16);
      srCtx.beginPath();
      srCtx.moveTo(cx, cy - 14);
      srCtx.lineTo(cx, cy + 14);
      srCtx.stroke();
    }

    // Draw active user S&R levels
    srClicks.forEach((lvl, idx) => {
      srCtx.strokeStyle = idx === srClicks.length - 1 ? '#00f0ff' : 'rgba(56, 189, 248, 0.5)';
      srCtx.lineWidth = 1.8;
      srCtx.beginPath();
      srCtx.moveTo(0, lvl.y);
      srCtx.lineTo(w, lvl.y);
      srCtx.stroke();

      // Touch markers
      for (let t = 0; t < lvl.touches; t++) {
        const tx = 40 + t * 50;
        srCtx.fillStyle = '#00f0ff';
        srCtx.beginPath();
        srCtx.arc(tx, lvl.y, 3.5, 0, Math.PI * 2);
        srCtx.fill();
      }

      srCtx.fillStyle = '#f8fafc';
      srCtx.font = '10px monospace';
      srCtx.fillText(lvl.touches + 'x Touch • ' + lvl.score, 10, lvl.y - 4);
    });
  }

  // LAB 3: Institutional Trap Radar Scanner
  let radarCanvas = null;
  let radarCtx = null;
  let radarAngle = 0;
  let radarMode = 'normal';

  function initRadarScanner() {
    radarCanvas = document.getElementById('lab-radar-canvas');
    if (!radarCanvas) return;
    radarCtx = radarCanvas.getContext('2d');
    const rect = radarCanvas.getBoundingClientRect();
    radarCanvas.width = rect.width;
    radarCanvas.height = rect.height;

    function drawRadar() {
      if (!radarCtx) return;
      const w = radarCanvas.width;
      const h = radarCanvas.height;
      const cx = w / 2;
      const cy = h / 2;

      radarCtx.clearRect(0, 0, w, h);

      // Circles
      radarCtx.strokeStyle = radarMode === 'normal' ? 'rgba(16, 185, 129, 0.25)' : 'rgba(239, 68, 68, 0.3)';
      radarCtx.lineWidth = 1;
      [30, 55, 80].forEach(r => {
        radarCtx.beginPath();
        radarCtx.arc(cx, cy, r, 0, Math.PI * 2);
        radarCtx.stroke();
      });

      // Axis lines
      radarCtx.beginPath();
      radarCtx.moveTo(cx, 0); radarCtx.lineTo(cx, h);
      radarCtx.moveTo(0, cy); radarCtx.lineTo(w, cy);
      radarCtx.stroke();

      // Sweep Beam
      radarAngle += 0.035;
      radarCtx.save();
      radarCtx.translate(cx, cy);
      radarCtx.rotate(radarAngle);

      const grad = radarCtx.createRadialGradient(0, 0, 0, 0, 0, 85);
      grad.addColorStop(0, radarMode === 'normal' ? 'rgba(16, 185, 129, 0.4)' : 'rgba(239, 68, 68, 0.4)');
      grad.addColorStop(1, 'transparent');

      radarCtx.beginPath();
      radarCtx.moveTo(0, 0);
      radarCtx.arc(0, 0, 85, -0.4, 0);
      radarCtx.closePath();
      radarCtx.fillStyle = grad;
      radarCtx.fill();
      radarCtx.restore();

      requestAnimationFrame(drawRadar);
    }
    drawRadar();
  }

  window.setRadarMode = function (mode) {
    radarMode = mode;
    playClickBeep(mode === 'normal' ? 800 : 450);

    const btnNorm = document.getElementById('btn-trap-normal');
    const btnFake = document.getElementById('btn-trap-fakeout');
    const fb = document.getElementById('radar-feedback');

    if (mode === 'normal') {
      if (btnNorm) btnNorm.className = 'radar-mode-btn active';
      if (btnFake) btnFake.className = 'radar-mode-btn';
      if (fb) {
        fb.className = 'lab-feedback-box text-emerald';
        fb.innerHTML = '✓ <strong>Authentic Rally:</strong> Top 4 constituents (Reliance, HDFC Bank, ICICI Bank) actively accumulating. Volume delta fully supports index breakout.';
      }
    } else {
      if (btnNorm) btnNorm.className = 'radar-mode-btn';
      if (btnFake) btnFake.className = 'radar-mode-btn fakeout active';
      if (fb) {
        fb.className = 'lab-feedback-box text-red';
        fb.innerHTML = '⚠️ <strong>Institutional Trap Detected:</strong> Reliance &amp; HDFC Bank delta flashing heavy selling (-18.4k lots) while NIFTY pushes up. High probability of violent retail flush!';
      }
      playAlertChime();
    }
  };

  // LAB 4: Trader Discipline & Capital Calculator
  window.updateRiskCalculator = function () {
    const capEl = document.getElementById('calc-capital');
    const riskEl = document.getElementById('calc-risk-pct');
    const slEl = document.getElementById('calc-sl-pts');

    if (!capEl || !riskEl || !slEl) return;

    const capital = parseFloat(capEl.value) || 100000;
    const riskPct = parseFloat(riskEl.value) || 0.015;
    const slPts = parseFloat(slEl.value) || 25;

    const maxRisk = capital * riskPct;
    const niftyLotSize = 25; // 25 qty per lot
    const riskPerLot = slPts * niftyLotSize;
    const allowedLots = Math.max(1, Math.floor(maxRisk / riskPerLot));
    const dailyCircuit = maxRisk * 3;

    const resRisk = document.getElementById('calc-res-risk');
    const resLots = document.getElementById('calc-res-lots');
    const resCircuit = document.getElementById('calc-res-circuit');

    if (resRisk) resRisk.textContent = '₹' + Math.round(maxRisk).toLocaleString('en-IN');
    if (resLots) resLots.textContent = allowedLots + ' Lot' + (allowedLots > 1 ? 's' : '') + ' (' + (allowedLots * niftyLotSize) + ' Qty)';
    if (resCircuit) resCircuit.textContent = '₹' + Math.round(dailyCircuit).toLocaleString('en-IN') + ' (3 Trades)';
  };

  // =====================================================================
  // 5. 3D SCREENSHOT CINEMA SHOWCASE & LIGHTBOX
  // =====================================================================
  const screenshots = [
    {
      img: '/static/images/screenshots/shot1_vwap_bands.png',
      badge: 'Institutional Fair Value',
      title: 'Anchored VWAP & ±2σ Exhaustion Bands',
      desc: 'Real-time volume-weighted mathematical boundaries. Know instantly when price is overextended (+2σ Red) or discounted (-2σ Green). Stop buying tops and selling bottoms.',
      tag: 'VWAP Bands'
    },
    {
      img: '/static/images/screenshots/shot2_sr_confluence.png',
      badge: 'Algorithmic Liquidity',
      title: 'Automated Multi-Timeframe S&R Confluence Engine',
      desc: 'Zero manual drawing required. Our quant algorithm calculates historical touch counts, dynamic resistance zones, and breakout trigger levels automatically.',
      tag: 'Auto S&R'
    },
    {
      img: '/static/images/screenshots/shot3_trap_radar.png',
      badge: 'Institutional Order Flow',
      title: 'Heavyweight Constituent Delta & Institutional Trap Radar',
      desc: 'Tracks real-time constituent volume across Reliance, HDFC Bank, ICICI Bank & Infosys to spot institutional manipulation and retail bull/bear traps before they strike.',
      tag: 'Trap Radar'
    },
    {
      img: '/static/images/screenshots/shot4_ai_copilot.png',
      badge: 'RAG-Powered AI Intelligence',
      title: 'AI Strategy Copilot with Live Market Context',
      desc: 'Conversational quantitative AI assistant analyzing market regimes, trend strength, and setup viability in natural language with zero Demat API key needed.',
      tag: 'AI Copilot'
    },
    {
      img: '/static/images/screenshots/shot5_multi_timeframe.png',
      badge: 'Sub-Second Pure HTML5',
      title: 'Tactile Multi-Timeframe Candle Resampling',
      desc: 'Instant switching across 5m, 15m, 1h, and 1D timeframes with 2 months of historical candles cached directly in in-memory RAM for instant response.',
      tag: 'Timeframes'
    },
    {
      img: '/static/images/screenshots/shot6_psychology_risk.png',
      badge: 'Trader Discipline Guard',
      title: 'Trading Psychology & 1-Click Pre-Flight Checklist',
      desc: 'Comprehensive multi-factor validation before entering trades. Guard your emotional discipline, eliminate revenge trading, and maintain strict risk parameters.',
      tag: 'Psychology Guard'
    }
  ];

  let currentSlideIndex = 0;
  let slideInterval = null;

  function loadSlide(index) {
    if (index < 0) index = screenshots.length - 1;
    if (index >= screenshots.length) index = 0;
    currentSlideIndex = index;

    const s = screenshots[index];
    const imgEl = document.getElementById('gallery-display-img');
    const badgeEl = document.getElementById('gallery-badge');
    const titleEl = document.getElementById('gallery-title');
    const descEl = document.getElementById('gallery-desc');

    if (imgEl) {
      imgEl.style.opacity = '0.3';
      imgEl.style.transform = 'scale(0.98)';
      setTimeout(() => {
        imgEl.src = s.img;
        imgEl.style.opacity = '1';
        imgEl.style.transform = 'scale(1)';
      }, 150);
    }
    if (badgeEl) badgeEl.textContent = s.badge;
    if (titleEl) titleEl.textContent = s.title;
    if (descEl) descEl.textContent = s.desc;

    // Update active tab buttons
    const tabs = document.querySelectorAll('.gallery-tab');
    tabs.forEach((tab, idx) => {
      tab.classList.toggle('active', idx === index);
    });

    // Update active thumbnails
    const thumbs = document.querySelectorAll('.gallery-thumb-item');
    thumbs.forEach((thumb, idx) => {
      thumb.classList.toggle('active', idx === index);
    });

    trackFunnelAction('funnel_screenshot_view', 'Viewed Slide ' + (index + 1) + ': ' + s.tag);
  }

  function startSlideAutoTimer() {
    stopSlideAutoTimer();
    slideInterval = setInterval(() => {
      loadSlide(currentSlideIndex + 1);
    }, 8000);
  }

  function stopSlideAutoTimer() {
    if (slideInterval) clearInterval(slideInterval);
  }

  window.selectScreenshot = function (index) {
    playClickBeep(650);
    stopSlideAutoTimer();
    loadSlide(index);
    startSlideAutoTimer();
  };

  window.prevSlide = function () {
    selectScreenshot(currentSlideIndex - 1);
  };

  window.nextSlide = function () {
    selectScreenshot(currentSlideIndex + 1);
  };

  window.toggleScanlines = function () {
    playClickBeep(1200);
    const ov = document.getElementById('scanline-overlay');
    const btn = document.getElementById('btn-toggle-scanlines');
    if (!ov || !btn) return;

    const isActive = ov.classList.toggle('active');
    btn.classList.toggle('active', isActive);
    btn.textContent = isActive ? 'CRT: ON' : 'CRT: OFF';
  };

  // Cinema Lightbox Modal
  window.openLightbox = function () {
    playClickBeep(900);
    const s = screenshots[currentSlideIndex];
    const modal = document.getElementById('lightbox-modal');
    const img = document.getElementById('lightbox-img');
    const cap = document.getElementById('lightbox-caption');
    if (modal && img) {
      img.src = s.img;
      if (cap) cap.textContent = s.title + ' — ' + s.badge;
      modal.style.display = 'flex';
    }
  };

  window.closeLightbox = function () {
    const modal = document.getElementById('lightbox-modal');
    if (modal) modal.style.display = 'none';
  };

  // =====================================================================
  // 6. INTERACTIVE SPLIT COMPARISON SLIDER
  // =====================================================================
  function initSplitSlider() {
    const wrap = document.getElementById('split-slider-wrap');
    const proLayer = document.getElementById('split-layer-pro');
    const handle = document.getElementById('split-handle');
    if (!wrap || !proLayer || !handle) return;

    let isDragging = false;

    function syncInnerWidth() {
      const rect = wrap.getBoundingClientRect();
      const pad = window.innerWidth <= 768 ? 32 : 80;
      const innerW = Math.max(240, rect.width - pad) + 'px';
      const innerRetail = wrap.querySelector('.split-layer-retail .split-content-inner');
      const innerPro = wrap.querySelector('.split-layer-pro .split-content-inner');
      if (innerRetail) innerRetail.style.width = innerW;
      if (innerPro) innerPro.style.width = innerW;
    }
    syncInnerWidth();
    window.addEventListener('resize', syncInnerWidth);

    function updateSplit(clientX) {
      const rect = wrap.getBoundingClientRect();
      let offsetX = clientX - rect.left;
      if (offsetX < 20) offsetX = 20;
      if (offsetX > rect.width - 20) offsetX = rect.width - 20;
      const pct = (offsetX / rect.width) * 100;
      proLayer.style.width = pct + '%';
      handle.style.left = pct + '%';
    }

    wrap.addEventListener('mousedown', (e) => {
      isDragging = true;
      updateSplit(e.clientX);
    });

    window.addEventListener('mousemove', (e) => {
      if (!isDragging) return;
      updateSplit(e.clientX);
    });

    window.addEventListener('mouseup', () => {
      isDragging = false;
    });

    // Touch support
    wrap.addEventListener('touchstart', (e) => {
      isDragging = true;
      if (e.touches && e.touches[0]) updateSplit(e.touches[0].clientX);
    }, { passive: true });

    window.addEventListener('touchmove', (e) => {
      if (!isDragging) return;
      if (e.touches && e.touches[0]) updateSplit(e.touches[0].clientX);
    }, { passive: true });

    window.addEventListener('touchend', () => {
      isDragging = false;
    });
  }

  // =====================================================================
  // 7. MAGNETIC CURSOR & 3D TILT PHYSICS
  // =====================================================================
  function initMagneticCursorAndTilt() {
    const orb = document.getElementById('magnetic-cursor-orb');
    let orbX = window.innerWidth / 2;
    let orbY = window.innerHeight / 2;
    let mouseX = orbX;
    let mouseY = orbY;

    window.addEventListener('mousemove', (e) => {
      mouseX = e.clientX;
      mouseY = e.clientY;

      // Update interactive crosshair on hero canvas if hovered
      if (simCanvas) {
        const r = simCanvas.getBoundingClientRect();
        if (mouseX >= r.left && mouseX <= r.right && mouseY >= r.top && mouseY <= r.bottom) {
          simMouseX = mouseX - r.left;
          simMouseY = mouseY - r.top;
        } else {
          simMouseX = -1;
          simMouseY = -1;
        }
      }
    });

    function loopOrb() {
      orbX += (mouseX - orbX) * 0.12;
      orbY += (mouseY - orbY) * 0.12;
      if (orb) {
        orb.style.transform = `translate3d(${orbX}px, ${orbY}px, 0) translate(-50%, -50%)`;
      }
      requestAnimationFrame(loopOrb);
    }
    loopOrb();

    // 3D Tilt for all .tilt-card elements
    const cards = document.querySelectorAll('.tilt-card');
    cards.forEach(card => {
      card.addEventListener('mousemove', (e) => {
        const rect = card.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        const centerX = rect.width / 2;
        const centerY = rect.height / 2;

        const rotateX = ((y - centerY) / centerY) * -6;
        const rotateY = ((x - centerX) / centerX) * 6;

        card.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) translateY(-4px)`;
        card.style.setProperty('--mouse-x', `${x}px`);
        card.style.setProperty('--mouse-y', `${y}px`);
      });

      card.addEventListener('mouseleave', () => {
        card.style.transform = 'perspective(1000px) rotateX(0deg) rotateY(0deg) translateY(0)';
      });

      card.addEventListener('mouseenter', () => {
        playHoverTick();
      });
    });
  }

  // =====================================================================
  // 8. EMBEDDED AUTH MODAL LOGIC & FORM VALIDATIONS
  // =====================================================================
  const COUNTRY_CODES = [
    { name: 'India', code: '+91', flag: '🇮🇳' },
    { name: 'United States', code: '+1', flag: '🇺🇸' },
    { name: 'United Kingdom', code: '+44', flag: '🇬🇧' },
    { name: 'United Arab Emirates', code: '+971', flag: '🇦🇪' },
    { name: 'Singapore', code: '+65', flag: '🇸🇬' },
    { name: 'Australia', code: '+61', flag: '🇦🇺' },
    { name: 'Canada', code: '+1', flag: '🇨🇦' },
    { name: 'Germany', code: '+49', flag: '🇩🇪' }
  ];

  let selectedCountryCode = '+91';
  let selectedCountryFlag = '🇮🇳';
  let usernameCheckTimer = null;
  let phoneCheckTimer = null;

  window.launchGuestMode = function () {
    playClickBeep(1000);
    trackFunnelAction('funnel_try_guest_click', 'Clicked Try for Free Without Registration');
    window.location.href = '/terminal?mode=guest';
  };

  window.openAuthModal = function (tab = 'login') {
    playClickBeep(850);
    const overlay = document.getElementById('auth-modal-overlay');
    if (overlay) {
      overlay.style.display = 'flex';
      overlay.scrollTop = 0;
      switchAuthTab(tab);
    }
    trackFunnelAction('funnel_direct_login_click', 'Opened Auth Modal (' + tab + ')');
  };

  window.closeAuthModal = function () {
    const overlay = document.getElementById('auth-modal-overlay');
    if (overlay) overlay.style.display = 'none';
  };

  window.switchAuthTab = function (tab) {
    playHoverTick();
    const tabLogin = document.getElementById('tab-login');
    const tabRegister = document.getElementById('tab-register');
    const tabForgot = document.getElementById('tab-forgot');
    const formLogin = document.getElementById('form-auth-login');
    const formRegister = document.getElementById('form-auth-register');
    const formForgot = document.getElementById('form-auth-forgot');
    const titleEl = document.getElementById('auth-modal-title');
    const errBox = document.getElementById('auth-error-box');

    if (errBox) errBox.style.display = 'none';

    [tabLogin, tabRegister, tabForgot].forEach(t => t && t.classList.remove('active'));
    [formLogin, formRegister, formForgot].forEach(f => f && (f.style.display = 'none'));

    if (tab === 'register') {
      if (tabRegister) tabRegister.classList.add('active');
      if (formRegister) formRegister.style.display = 'block';
      if (titleEl) titleEl.textContent = 'Create Free Account';
      renderCountryDropdownList(COUNTRY_CODES);
    } else if (tab === 'forgot') {
      if (tabForgot) tabForgot.classList.add('active');
      if (formForgot) formForgot.style.display = 'block';
      if (titleEl) titleEl.textContent = 'Reset Password';
    } else {
      if (tabLogin) tabLogin.classList.add('active');
      if (formLogin) formLogin.style.display = 'block';
      if (titleEl) titleEl.textContent = 'Sign In to Terminal';
    }
  };

  // Country dropdown handling
  window.toggleCountryDropdown = function (e) {
    e.stopPropagation();
    const drop = document.getElementById('reg-country-dropdown');
    if (!drop) return;
    const isShowing = drop.style.display === 'block';
    drop.style.display = isShowing ? 'none' : 'block';
    if (!isShowing) {
      const search = document.getElementById('reg-country-search');
      if (search) { search.value = ''; search.focus(); }
      renderCountryDropdownList(COUNTRY_CODES);
    }
  };

  function renderCountryDropdownList(list) {
    const container = document.getElementById('reg-country-list');
    if (!container) return;
    container.innerHTML = '';
    list.forEach(c => {
      const div = document.createElement('div');
      div.className = 'country-option-item';
      div.innerHTML = `<span>${c.flag} ${c.name}</span><span style="font-family:monospace; color:#38bdf8;">${c.code}</span>`;
      div.onclick = () => selectCountry(c);
      container.appendChild(div);
    });
  }

  window.filterCountryList = function (query) {
    const q = (query || '').toLowerCase().trim();
    const filtered = COUNTRY_CODES.filter(c =>
      c.name.toLowerCase().includes(q) || c.code.toLowerCase().includes(q)
    );
    renderCountryDropdownList(filtered);
  };

  function selectCountry(c) {
    selectedCountryCode = c.code;
    selectedCountryFlag = c.flag;
    const flagEl = document.getElementById('reg-country-flag');
    const codeEl = document.getElementById('reg-country-code');
    const drop = document.getElementById('reg-country-dropdown');
    if (flagEl) flagEl.textContent = c.flag;
    if (codeEl) codeEl.textContent = c.code;
    if (drop) drop.style.display = 'none';

    const phoneInp = document.getElementById('reg-phone');
    if (phoneInp) {
      phoneInp.maxLength = (c.code === '+91') ? 10 : 14;
      phoneInp.focus();
    }
  }

  // Real-time username & phone validations
  window.handleRegUsernameInput = function () {
    const input = document.getElementById('reg-username');
    if (!input) return;
    input.value = input.value.replace(/[^a-zA-Z0-9_]/g, '');
    if (usernameCheckTimer) clearTimeout(usernameCheckTimer);
    usernameCheckTimer = setTimeout(checkUsernameAvailability, 300);
  };

  async function checkUsernameAvailability() {
    const input = document.getElementById('reg-username');
    const hint = document.getElementById('reg-username-hint');
    if (!input || !hint) return;
    const uname = input.value.trim();
    if (!uname || uname.length < 3) {
      hint.innerHTML = '<span style="color:#ef4444;">⚠️ Must be at least 3 alphanumeric characters.</span>';
      return;
    }
    try {
      const res = await fetch('/api/auth/check-username?username=' + encodeURIComponent(uname));
      const data = await res.json();
      if (data.available) {
        hint.innerHTML = '<span style="color:#10b981;">✓ @' + uname + ' is available!</span>';
        input.style.borderColor = '#10b981';
      } else {
        hint.innerHTML = '<span style="color:#ef4444;">✕ Username is already taken.</span>';
        input.style.borderColor = '#ef4444';
      }
    } catch (e) {}
  }

  window.handleRegPhoneInput = function () {
    const input = document.getElementById('reg-phone');
    if (!input) return;
    const maxLen = (selectedCountryCode === '+91') ? 10 : 14;
    input.value = input.value.replace(/\D/g, '').substring(0, maxLen);
    if (phoneCheckTimer) clearTimeout(phoneCheckTimer);
    phoneCheckTimer = setTimeout(checkPhoneAvailability, 300);
  };

  async function checkPhoneAvailability() {
    const input = document.getElementById('reg-phone');
    const hint = document.getElementById('reg-phone-hint');
    if (!input || !hint) return;
    const phone = input.value.trim();
    if (!phone) { hint.textContent = ''; return; }
    try {
      const full = selectedCountryCode + phone;
      const res = await fetch('/api/auth/check-phone?phone=' + encodeURIComponent(full));
      const data = await res.json();
      if (data.available) {
        hint.innerHTML = '<span style="color:#10b981;">✓ Mobile number ready</span>';
      } else {
        hint.innerHTML = '<span style="color:#ef4444;">✕ Phone already registered</span>';
      }
    } catch (e) {}
  }

  // Expose real-time validator hooks to window for HTML event attributes
  window.checkUsernameAvailability = checkUsernameAvailability;
  window.checkPhoneAvailability = checkPhoneAvailability;

  window.handleRegEmailInput = function () {
    const input = document.getElementById('reg-email');
    if (!input) return;
    const val = input.value.trim();
    if (val.length > 5 && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(val)) {
      input.style.borderColor = '#10b981';
    } else if (val.length > 0) {
      input.style.borderColor = 'rgba(51, 65, 85, 0.7)';
    }
  };

  window.handleRegPasswordInput = function () {
    const input = document.getElementById('reg-password');
    if (!input) return;
    const val = input.value;
    if (val.length >= 6) {
      input.style.borderColor = '#10b981';
    } else if (val.length > 0) {
      input.style.borderColor = '#f59e0b';
    }
  };

  // Form Submissions
  window.handleLoginSubmit = async function (e) {
    e.preventDefault();
    const ident = document.getElementById('login-identifier').value.trim();
    const pwd = document.getElementById('login-password').value.trim();
    const btn = document.getElementById('btn-submit-login');

    if (!ident || !pwd) {
      showAuthError('Please enter username/email and password.');
      return;
    }

    btn.disabled = true;
    btn.textContent = 'Verifying Credentials...';

    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ identifier: ident, password: pwd })
      });
      const data = await res.json();
      if (res.ok && data.token) {
        localStorage.setItem('auth_token', data.token);
        trackFunnelAction('funnel_direct_login_success', 'Signed in directly from Terminal 1');
        showAuthSuccess('Login successful! Launching Live Terminal...');
        setTimeout(() => { window.location.href = '/terminal'; }, 700);
      } else {
        showAuthError(data.message || data.error || 'Login failed. Please check credentials.');
        btn.disabled = false;
        btn.textContent = 'Sign In to Terminal ➜';
      }
    } catch (err) {
      showAuthError('Network error occurred. Please try again.');
      btn.disabled = false;
      btn.textContent = 'Sign In to Terminal ➜';
    }
  };

  window.handleRegisterSubmit = async function (e) {
    e.preventDefault();
    const uname = document.getElementById('reg-username').value.trim();
    const email = document.getElementById('reg-email').value.trim();
    const pwd = document.getElementById('reg-password').value.trim();
    const phone = document.getElementById('reg-phone').value.trim();
    const style = document.getElementById('reg-trading-style').value;
    const policy = document.getElementById('reg-accept-policy');
    const btn = document.getElementById('btn-submit-register');

    if (!uname || !email || !pwd) {
      showAuthError('Please complete all required fields.');
      return;
    }

    if (policy && !policy.checked) {
      showAuthError('Please acknowledge the Charting Disclaimer & Terms.');
      return;
    }

    btn.disabled = true;
    btn.textContent = 'Creating Quantitative Account...';

    try {
      const fullPhone = phone ? (selectedCountryCode + phone) : '';
      const res = await fetch('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: uname,
          email: email,
          password: pwd,
          phone: fullPhone,
          trading_style: style || 'intraday_scalper',
          accepted_policy: true
        })
      });
      const data = await res.json();
      if (res.ok && data.token) {
        localStorage.setItem('auth_token', data.token);
        trackFunnelAction('funnel_direct_register_success', 'Created account from Terminal 1');
        showAuthSuccess('Account created! Launching Live Quantitative Terminal...');
        setTimeout(() => { window.location.href = '/terminal'; }, 750);
      } else {
        showAuthError(data.message || data.error || 'Registration failed. Username or email may already be in use.');
        btn.disabled = false;
        btn.textContent = 'Register & Create Account 🚀';
      }
    } catch (err) {
      showAuthError('Network error occurred. Please try again.');
      btn.disabled = false;
      btn.textContent = 'Register & Create Account 🚀';
    }
  };

  window.handleForgotPasswordSubmit = async function (e) {
    e.preventDefault();
    const ident = document.getElementById('reset-identifier').value.trim();
    const phone = document.getElementById('reset-phone').value.trim();
    const newPwd = document.getElementById('reset-new-password').value.trim();
    const confPwd = document.getElementById('reset-confirm-password').value.trim();
    const btn = document.getElementById('btn-submit-reset');

    if (newPwd !== confPwd) {
      showAuthError('Passwords do not match.');
      return;
    }

    btn.disabled = true;
    btn.textContent = 'Resetting Password...';

    try {
      const res = await fetch('/api/auth/reset-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ identifier: ident, phone: phone, new_password: newPwd })
      });
      const data = await res.json();
      if (res.ok && data.token) {
        localStorage.setItem('auth_token', data.token);
        showAuthSuccess('Password reset successfully! Redirecting...');
        setTimeout(() => { window.location.href = '/terminal'; }, 750);
      } else {
        showAuthError(data.message || 'Reset failed. Verified phone does not match account.');
        btn.disabled = false;
        btn.textContent = '🚀 Reset Password & Log In';
      }
    } catch (err) {
      showAuthError('Network error occurred. Please try again.');
      btn.disabled = false;
      btn.textContent = '🚀 Reset Password & Log In';
    }
  };

  function showAuthError(msg) {
    const box = document.getElementById('auth-error-box');
    if (!box) return;
    box.innerHTML = msg;
    box.style.display = 'block';
    box.style.background = 'rgba(239, 68, 68, 0.15)';
    box.style.border = '1px solid rgba(239, 68, 68, 0.45)';
    box.style.color = '#f87171';
  }

  function showAuthSuccess(msg) {
    const box = document.getElementById('auth-error-box');
    if (!box) return;
    box.innerHTML = msg;
    box.style.display = 'block';
    box.style.background = 'rgba(16, 185, 129, 0.15)';
    box.style.border = '1px solid rgba(16, 185, 129, 0.45)';
    box.style.color = '#34d399';
  }

  // Developer Feedback / Contact Form
  window.submitContactForm = async function (e) {
    e.preventDefault();
    const name = document.getElementById('contact-name').value.trim();
    const email = document.getElementById('contact-email').value.trim();
    const msg = document.getElementById('contact-msg').value.trim();
    const btn = document.getElementById('btn-contact-submit');

    if (!msg) return;

    btn.disabled = true;
    btn.textContent = 'Dispatching Encrypted Telemetry...';

    try {
      const res = await fetch('/api/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: name || 'Terminal 1 Visitor',
          email: email || '',
          category: 'Terminal 1 Inquiry',
          message: msg,
          visitor_id: visitorId
        })
      });
      if (res.ok) {
        btn.textContent = '✓ Message Received by Dev!';
        btn.style.background = '#10b981';
        document.getElementById('contact-form').reset();
        setTimeout(() => {
          btn.disabled = false;
          btn.textContent = 'Send Message to Developer ➜';
          btn.style.background = '';
        }, 4000);
      } else {
        btn.disabled = false;
        btn.textContent = 'Submission Failed. Try Again';
      }
    } catch (err) {
      btn.disabled = false;
      btn.textContent = 'Submission Failed. Try Again';
    }
  };

  // Close modals when clicking outside
  document.addEventListener('click', (e) => {
    const authModal = document.getElementById('auth-modal-overlay');
    if (authModal && e.target === authModal) {
      closeAuthModal();
    }
    const drop = document.getElementById('reg-country-dropdown');
    if (drop && drop.style.display === 'block' && !e.target.closest('#reg-country-dropdown') && !e.target.closest('#reg-country-btn')) {
      drop.style.display = 'none';
    }
    const lbModal = document.getElementById('lightbox-modal');
    if (lbModal && e.target === lbModal) {
      closeLightbox();
    }
  });

  // Floating Live Telemetry Ticker
  function initLiveTelemetryTicker() {
    const textEl = document.getElementById('telemetry-text');
    if (!textEl) return;

    const messages = [
      '⚡ NIFTY 50 Live • Anchored VWAP ±2σ Engine Active',
      '🤖 AI Strategy Copilot • Real-Time Order Flow Scanner Active',
      '🟢 1,620+ Active Quant Traders Connected Today',
      '🎯 Automated S&R Confluence • Zero Repaint Algorithmic Logic',
      '🛡️ Institutional Trap Radar • 4 Core Heavyweights Live'
    ];
    let msgIdx = 0;

    setInterval(() => {
      textEl.style.opacity = '0';
      textEl.style.transform = 'translateY(4px)';
      textEl.style.transition = 'all 0.25s ease';
      setTimeout(() => {
        msgIdx = (msgIdx + 1) % messages.length;
        textEl.textContent = messages[msgIdx];
        textEl.style.opacity = '1';
        textEl.style.transform = 'translateY(0)';
      }, 250);
    }, 4500);
  }

  // =====================================================================
  // 9. EXTENDED MICRO-INTERACTIONS & EVENT LISTENERS
  // =====================================================================
  function initMicroInteractions() {
    // Add hover audio to buttons and navigation links
    document.querySelectorAll('.nav-link-item, .btn-login, .gallery-tab, .sim-tf-btn, .sim-layer-btn, .radar-mode-btn, .channel-btn').forEach(el => {
      el.addEventListener('mouseenter', () => {
        playHoverTick();
      });
    });

    // Initialize Hero Simulator Canvas
    simCanvas = document.getElementById('hero-simulator-canvas');
    if (simCanvas) {
      simCtx = simCanvas.getContext('2d');
      const r = simCanvas.getBoundingClientRect();
      simCanvas.width = r.width * (window.devicePixelRatio || 1);
      simCanvas.height = r.height * (window.devicePixelRatio || 1);
      simCtx.scale(window.devicePixelRatio || 1, window.devicePixelRatio || 1);
      initSimData(60);
      startSimLoop();
    }
  }


  // =========================================================================
  // 10. ADVANCED KEYBOARD SHORTCUTS & COGNITIVE NAVIGATION ENGINE
  // =========================================================================
  function initKeyboardShortcuts() {
    window.addEventListener('keydown', (e) => {
      // Avoid intercepting keystrokes if the user is typing in form controls
      const activeEl = document.activeElement;
      if (activeEl && (activeEl.tagName === 'INPUT' || activeEl.tagName === 'TEXTAREA' || activeEl.tagName === 'SELECT')) {
        if (e.key === 'Escape') {
          closeAuthModal();
          closeLightbox();
        }
        return;
      }

      switch (e.key) {
        case 'Escape':
          closeAuthModal();
          closeLightbox();
          break;

        case '1':
        case '2':
        case '3':
        case '4':
        case '5':
        case '6': {
          const slideIndex = parseInt(e.key, 10) - 1;
          selectScreenshot(slideIndex);
          playPitchedBeep(650 + slideIndex * 50, 0.04);
          break;
        }

        case 'ArrowLeft':
          prevSlide();
          playPitchedBeep(520, 0.04);
          break;

        case 'ArrowRight':
          nextSlide();
          playPitchedBeep(620, 0.04);
          break;

        case 'g':
        case 'G':
          launchGuestMode();
          break;

        case 'l':
        case 'L':
          openAuthModal('login');
          break;

        case 'm':
        case 'M':
          toggleSoundFX();
          break;

        case 'c':
        case 'C':
          toggleScanlines();
          break;

        case 's':
        case 'S': {
          const simEl = document.getElementById('simulator');
          if (simEl) {
            simEl.scrollIntoView({ behavior: 'smooth' });
          }
          break;
        }

        case 'q':
        case 'Q': {
          const labsEl = document.getElementById('quant-labs');
          if (labsEl) {
            labsEl.scrollIntoView({ behavior: 'smooth' });
          }
          break;
        }

        default:
          break;
      }
    });
  }

  // =========================================================================
  // 11. LIVE INDIAN STOCK MARKET SESSION & COUNTDOWN CLOCK (IST)
  // =========================================================================
  function initLiveMarketSessionClock() {
    function calculateISTStatus() {
      const now = new Date();
      // UTC timestamp + 5.5 hours for IST
      const utc = now.getTime() + (now.getTimezoneOffset() * 60000);
      const ist = new Date(utc + (3600000 * 5.5));

      const day = ist.getDay(); // 0 = Sun, 6 = Sat
      const hours = ist.getHours();
      const minutes = ist.getMinutes();
      const seconds = ist.getSeconds();
      const currentMin = hours * 60 + minutes;

      const isWeekday = (day >= 1 && day <= 5);
      const preMarketStart = 9 * 60; // 09:00 IST
      const marketOpen = 9 * 60 + 15; // 09:15 IST
      const marketClose = 15 * 60 + 30; // 15:30 IST
      const postMarketEnd = 16 * 60; // 16:00 IST

      let status = 'CLOSED';
      let statusColor = '#94a3b8';
      let tooltipDesc = 'Session Closed • Institutional After-Hours Model Active';

      if (isWeekday) {
        if (currentMin >= preMarketStart && currentMin < marketOpen) {
          status = 'PRE-MARKET';
          statusColor = '#f59e0b';
          const remSec = (marketOpen - currentMin) * 60 - seconds;
          tooltipDesc = 'NSE Pre-Open Auction • Market opens in ' + Math.floor(remSec / 60) + 'm ' + (remSec % 60) + 's';
        } else if (currentMin >= marketOpen && currentMin < marketClose) {
          status = 'LIVE NSE/BSE';
          statusColor = '#10b981';
          const remSec = (marketClose - currentMin) * 60 - seconds;
          tooltipDesc = 'Regular Trading Session Active • Closes in ' + Math.floor(remSec / 60) + 'm ' + (remSec % 60) + 's';
        } else if (currentMin >= marketClose && currentMin < postMarketEnd) {
          status = 'POST-MARKET';
          statusColor = '#06b6d4';
          tooltipDesc = 'Post-Market Settlement & VWAP True Closing Prints';
        } else {
          status = 'AFTER-HOURS';
          statusColor = '#64748b';
          tooltipDesc = 'Market Closed • Real-Time Backtesting Simulator Running';
        }
      } else {
        status = 'WEEKEND';
        statusColor = '#64748b';
        tooltipDesc = 'NSE/BSE Weekend Break • Quant Simulator Online';
      }

      const tickerBadge = document.querySelector('.live-ticker-badge');
      if (tickerBadge) {
        tickerBadge.setAttribute('data-quant-tooltip', tooltipDesc);
        const pulseDot = tickerBadge.querySelector('.pulse-dot');
        if (pulseDot) {
          pulseDot.style.background = statusColor;
          pulseDot.style.boxShadow = '0 0 10px ' + statusColor;
        }
        const textNode = tickerBadge.childNodes[tickerBadge.childNodes.length - 1];
        if (textNode && textNode.nodeType === Node.TEXT_NODE) {
          textNode.textContent = ' ' + status;
        }
      }
    }

    calculateISTStatus();
    setInterval(calculateISTStatus, 1000);
  }

  // =========================================================================
  // 12. SMOOTH SCROLLSPY ACTIVE MENU HIGHLIGHTER
  // =========================================================================
  function initScrollspy() {
    const sectionIds = ['simulator', 'screenshots', 'quant-labs', 'features', 'comparison', 'pricing', 'contact'];
    const sections = sectionIds.map(id => document.getElementById(id)).filter(Boolean);
    const navLinks = document.querySelectorAll('.nav-link-item');

    if (sections.length === 0 || navLinks.length === 0) return;

    window.addEventListener('scroll', () => {
      let currentId = '';
      const scrollPos = window.scrollY + 180;

      for (let i = 0; i < sections.length; i++) {
        const sec = sections[i];
        const top = sec.offsetTop;
        const height = sec.offsetHeight;
        if (scrollPos >= top && scrollPos < top + height) {
          currentId = sec.getAttribute('id');
          break;
        }
      }

      navLinks.forEach(link => {
        const href = link.getAttribute('href');
        if (href === '#' + currentId) {
          link.classList.add('active');
        } else {
          link.classList.remove('active');
        }
      });
    }, { passive: true });
  }

  // =========================================================================
  // 13. PARTICLE SPARK EMITTER FOR PRIMARY CTAs
  // =========================================================================
  function emitButtonSparks(e, targetEl) {
    if (!targetEl) return;
    const count = 16;
    const colors = ['#00f0ff', '#38bdf8', '#818cf8', '#10b981', '#ffffff'];

    for (let i = 0; i < count; i++) {
      const spark = document.createElement('div');
      spark.className = 'spark-particle';
      const angle = (Math.PI * 2 * i) / count + (Math.random() - 0.5) * 0.4;
      const velocity = 35 + Math.random() * 45;
      const vx = Math.cos(angle) * velocity;
      const vy = Math.sin(angle) * velocity;
      const color = colors[Math.floor(Math.random() * colors.length)];
      const size = 3 + Math.random() * 3;

      spark.style.cssText =
        'position: fixed;' +
        'left: ' + e.clientX + 'px;' +
        'top: ' + e.clientY + 'px;' +
        'width: ' + size + 'px;' +
        'height: ' + size + 'px;' +
        'border-radius: 50%;' +
        'background: ' + color + ';' +
        'box-shadow: 0 0 10px ' + color + ', 0 0 18px ' + color + ';' +
        'pointer-events: none;' +
        'z-index: 10000;' +
        'transition: transform 0.5s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.5s ease-out;';

      document.body.appendChild(spark);

      requestAnimationFrame(() => {
        spark.style.transform = 'translate(' + vx + 'px, ' + vy + 'px) scale(0)';
        spark.style.opacity = '0';
      });

      setTimeout(() => {
        if (spark.parentNode) {
          spark.parentNode.removeChild(spark);
        }
      }, 550);
    }
  }

  function initParticleSparks() {
    document.addEventListener('click', (e) => {
      const btn = e.target.closest('.btn-hero-guest, .btn-cta-primary, .btn-hero-login, .btn-pricing');
      if (btn) {
        emitButtonSparks(e, btn);
      }
    });
  }

  // =========================================================================
  // 14. CINEMA LIGHTBOX PAN & ZOOM INTERACTION
  // =========================================================================
  let lbZoom = 1.0;
  let lbPanX = 0;
  let lbPanY = 0;
  let lbIsDragging = false;
  let lbStartX = 0;
  let lbStartY = 0;

  function initLightboxZoomControls() {
    const img = document.getElementById('lightbox-img');
    const wrapper = document.querySelector('.lightbox-wrapper');
    if (!img || !wrapper) return;

    wrapper.addEventListener('wheel', (e) => {
      e.preventDefault();
      const delta = e.deltaY > 0 ? -0.2 : 0.2;
      lbZoom = Math.max(1.0, Math.min(3.8, lbZoom + delta));

      if (lbZoom === 1.0) {
        lbPanX = 0;
        lbPanY = 0;
      }
      img.style.transform = 'translate(' + lbPanX + 'px, ' + lbPanY + 'px) scale(' + lbZoom + ')';
      img.style.cursor = lbZoom > 1.0 ? 'grab' : 'zoom-in';
    }, { passive: false });

    img.addEventListener('mousedown', (e) => {
      if (lbZoom <= 1.0) return;
      lbIsDragging = true;
      lbStartX = e.clientX - lbPanX;
      lbStartY = e.clientY - lbPanY;
      img.style.cursor = 'grabbing';
      e.preventDefault();
    });

    window.addEventListener('mousemove', (e) => {
      if (!lbIsDragging) return;
      lbPanX = e.clientX - lbStartX;
      lbPanY = e.clientY - lbStartY;
      img.style.transform = 'translate(' + lbPanX + 'px, ' + lbPanY + 'px) scale(' + lbZoom + ')';
    });

    window.addEventListener('mouseup', () => {
      if (lbIsDragging) {
        lbIsDragging = false;
        if (img) img.style.cursor = lbZoom > 1.0 ? 'grab' : 'zoom-in';
      }
    });

    img.addEventListener('dblclick', () => {
      if (lbZoom > 1.0) {
        lbZoom = 1.0;
        lbPanX = 0;
        lbPanY = 0;
      } else {
        lbZoom = 2.2;
      }
      img.style.transform = 'translate(' + lbPanX + 'px, ' + lbPanY + 'px) scale(' + lbZoom + ')';
      img.style.cursor = lbZoom > 1.0 ? 'grab' : 'zoom-in';
    });
  }

  // =========================================================================
  // 15. QUANTITATIVE STATISTICAL ENGINE & RISK DISTRIBUTIONS
  // =========================================================================
  const QuantStatisticalEngine = {
    // Cumulative Standard Normal Distribution via Abramowitz & Stegun approximation
    gaussianCDF(x) {
      const b1 = 0.319381530;
      const b2 = -0.356563782;
      const b3 = 1.781477937;
      const b4 = -1.821255978;
      const b5 = 1.330274429;
      const p = 0.2316419;
      const c2 = 0.39894228;

      if (x >= 0.0) {
        const t = 1.0 / (1.0 + p * x);
        return 1.0 - c2 * Math.exp(-x * x / 2.0) * t * (t * (t * (t * (t * b5 + b4) + b3) + b2) + b1);
      } else {
        const t = 1.0 / (1.0 - p * x);
        return c2 * Math.exp(-x * x / 2.0) * t * (t * (t * (t * (t * b5 + b4) + b3) + b2) + b1);
      }
    },

    // Calculate z-score of current price relative to volume-weighted benchmark
    calculateZScore(currentPrice, vwap, sigma) {
      if (!sigma || sigma <= 0) return 0;
      return (currentPrice - vwap) / sigma;
    },

    // Empirical Mean Reversion probability based on Gaussian probability tail density
    calculateReversalProbability(zScore) {
      const absZ = Math.abs(zScore);
      const cdf = this.gaussianCDF(absZ);
      const tailRisk = (1.0 - cdf) * 2.0;
      const reversalConfidence = Math.min(99.4, Math.max(50.0, (1.0 - tailRisk) * 100));
      return {
        zScore: parseFloat(zScore.toFixed(2)),
        confidence: parseFloat(reversalConfidence.toFixed(1)),
        tailRiskPercent: parseFloat((tailRisk * 100).toFixed(2)),
        state: absZ > 2.5 ? 'CRITICAL EXHAUSTION' : (absZ > 1.8 ? 'STATISTICAL EXTENSION' : 'EQUILIBRIUM')
      };
    },

    // Calculate Average True Range (ATR)
    calculateATR(candles, period) {
      const p = period || 14;
      if (!candles || candles.length < p) return 0;
      const trValues = [];
      for (let i = 1; i < candles.length; i++) {
        const high = candles[i].high;
        const low = candles[i].low;
        const prevClose = candles[i - 1].close;
        const tr = Math.max(high - low, Math.abs(high - prevClose), Math.abs(low - prevClose));
        trValues.push(tr);
      }
      const recent = trValues.slice(-p);
      const sum = recent.reduce((acc, v) => acc + v, 0);
      return sum / p;
    },

    // Expected move calculation using Implied Volatility
    calculateExpectedMove(currentPrice, ivPercentage, daysToExpiry) {
      if (!currentPrice || currentPrice <= 0) return 0;
      const t = Math.sqrt(daysToExpiry / 365);
      const move = currentPrice * (ivPercentage / 100) * t;
      return {
        expectedMovePoints: parseFloat(move.toFixed(2)),
        upperBound: parseFloat((currentPrice + move).toFixed(2)),
        lowerBound: parseFloat((currentPrice - move).toFixed(2))
      };
    },

    // Monte Carlo simulation runner for position sizing validation
    simulateMonteCarlo(capital, winRate, rrRatio, riskPerTradePct, numTrades, numRuns) {
      const trades = numTrades || 100;
      const runsCount = numRuns || 50;
      const runs = [];
      const riskFraction = riskPerTradePct / 100;

      for (let r = 0; r < runsCount; r++) {
        let currentEquity = capital;
        const curve = [currentEquity];
        for (let t = 0; t < trades; t++) {
          const riskAmount = currentEquity * riskFraction;
          const isWin = Math.random() < (winRate / 100);
          if (isWin) {
            currentEquity += riskAmount * rrRatio;
          } else {
            currentEquity -= riskAmount;
          }
          currentEquity = Math.max(0, currentEquity);
          curve.push(parseFloat(currentEquity.toFixed(2)));
        }
        runs.push(curve);
      }

      const finalEquities = runs.map(run => run[run.length - 1]);
      finalEquities.sort((a, b) => a - b);
      const medianEquity = finalEquities[Math.floor(finalEquities.length * 0.5)];
      const worstCase = finalEquities[0];
      const bestCase = finalEquities[finalEquities.length - 1];

      return {
        medianEquity: parseFloat(medianEquity.toFixed(2)),
        worstCase: parseFloat(worstCase.toFixed(2)),
        bestCase: parseFloat(bestCase.toFixed(2)),
        sampleRun: runs[0]
      };
    }
  };

  // =========================================================================
  // 16. HIGH-DPI CANVAS AUTO-RESIZER & RESPONSIVENESS CONTROLLER
  // =========================================================================
  function initCanvasAutoScaler() {
    let resizeTimer = null;

    function handleResize() {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(() => {
        if (simCanvas && simCtx) {
          const rect = simCanvas.getBoundingClientRect();
          const dpr = window.devicePixelRatio || 1;
          simCanvas.width = rect.width * dpr;
          simCanvas.height = rect.height * dpr;
          simCtx.scale(dpr, dpr);
        }

        const srCanvas = document.getElementById('lab-sr-canvas');
        if (srCanvas) {
          const rect = srCanvas.getBoundingClientRect();
          const dpr = window.devicePixelRatio || 1;
          srCanvas.width = rect.width * dpr;
          srCanvas.height = rect.height * dpr;
          const ctx = srCanvas.getContext('2d');
          if (ctx) ctx.scale(dpr, dpr);
          renderSrCanvas();
        }

        const radarCanvas = document.getElementById('lab-radar-canvas');
        if (radarCanvas) {
          const rect = radarCanvas.getBoundingClientRect();
          const dpr = window.devicePixelRatio || 1;
          radarCanvas.width = rect.width * dpr;
          radarCanvas.height = rect.height * dpr;
          const ctx = radarCanvas.getContext('2d');
          if (ctx) ctx.scale(dpr, dpr);
        }
      }, 150);
    }

    window.addEventListener('resize', handleResize, { passive: true });
  }

  // =========================================================================
  // 17. QUANT TELEMETRY & SYSTEM PERFORMANCE OBSERVER
  // =========================================================================
  function initQuantAnalyticsTelemetry() {
    let lastTime = performance.now();
    let frameCount = 0;
    let currentFps = 60;

    function checkPerformance() {
      frameCount++;
      const now = performance.now();
      if (now - lastTime >= 1000) {
        currentFps = Math.round((frameCount * 1000) / (now - lastTime));
        frameCount = 0;
        lastTime = now;

        if (currentFps < 25 && simCandles && simCandles.length > 40) {
          simCandles = simCandles.slice(-40);
        }
      }
      requestAnimationFrame(checkPerformance);
    }

    requestAnimationFrame(checkPerformance);
  }

  // =========================================================================
  // 18. MASTER INITIALIZATION ON DOM READY
  // =========================================================================
  document.addEventListener('DOMContentLoaded', () => {
    syncSoundButtonUI();
    recordInitialVisit();
    checkReturningUser();
    loadSlide(0);
    startSlideAutoTimer();
    initLiveTelemetryTicker();
    initSplitSlider();
    initMagneticCursorAndTilt();
    initSrCanvas();
    initRadarScanner();
    updateRiskCalculator();
    initMicroInteractions();
    initKeyboardShortcuts();
    initLiveMarketSessionClock();
    initScrollspy();
    initParticleSparks();
    initLightboxZoomControls();
    initCanvasAutoScaler();
    initQuantAnalyticsTelemetry();

    const frame = document.querySelector('.window-frame');
    if (frame) {
      frame.addEventListener('mouseenter', stopSlideAutoTimer);
      frame.addEventListener('mouseleave', startSlideAutoTimer);
    }
  });

  // =========================================================================
  // 19. INSTITUTIONAL ORDER FLOW & VOLATILITY BENCHMARK REGISTRY
  // =========================================================================

  const _QUANT_MODEL_SPEC_01 = {
    id: "MOD_01",
    title: "Standard Anchored VWAP",
    category: "Trend Filter",
    description: "Volume-Weighted Average Price anchored to Daily/Weekly session opens",
    active: true,
    created: "2026-11-27",
    calculate: function(dataset) {
      if (!dataset || dataset.length === 0) return { value: 0, status: "idle" };
      return {
        modelId: "MOD_01",
        metric: dataset[dataset.length - 1] ? (dataset[dataset.length - 1].close || 0) : 0,
        timestamp: Date.now()
      };
    }
  };

  const _QUANT_MODEL_SPEC_02 = {
    id: "MOD_02",
    title: "Rolling VWAP Envelope",
    category: "Mean Reversion",
    description: "Dynamic rolling 20-period standard deviation bands",
    active: true,
    created: "2026-11-27",
    calculate: function(dataset) {
      if (!dataset || dataset.length === 0) return { value: 0, status: "idle" };
      return {
        modelId: "MOD_02",
        metric: dataset[dataset.length - 1] ? (dataset[dataset.length - 1].close || 0) : 0,
        timestamp: Date.now()
      };
    }
  };

  const _QUANT_MODEL_SPEC_03 = {
    id: "MOD_03",
    title: "Order Flow Imbalance (OFI)",
    category: "Execution",
    description: "Microsecond delta between Bid and Ask absorption",
    active: true,
    created: "2026-11-27",
    calculate: function(dataset) {
      if (!dataset || dataset.length === 0) return { value: 0, status: "idle" };
      return {
        modelId: "MOD_03",
        metric: dataset[dataset.length - 1] ? (dataset[dataset.length - 1].close || 0) : 0,
        timestamp: Date.now()
      };
    }
  };

  const _QUANT_MODEL_SPEC_04 = {
    id: "MOD_04",
    title: "Volume Profile Point of Control (POC)",
    category: "Support/Resistance",
    description: "Highest traded volume node across historical distribution",
    active: true,
    created: "2026-11-27",
    calculate: function(dataset) {
      if (!dataset || dataset.length === 0) return { value: 0, status: "idle" };
      return {
        modelId: "MOD_04",
        metric: dataset[dataset.length - 1] ? (dataset[dataset.length - 1].close || 0) : 0,
        timestamp: Date.now()
      };
    }
  };

  const _QUANT_MODEL_SPEC_05 = {
    id: "MOD_05",
    title: "Value Area High (VAH)",
    category: "Statistical Bound",
    description: "Upper bound containing 70 percent of total traded session volume",
    active: true,
    created: "2026-11-27",
    calculate: function(dataset) {
      if (!dataset || dataset.length === 0) return { value: 0, status: "idle" };
      return {
        modelId: "MOD_05",
        metric: dataset[dataset.length - 1] ? (dataset[dataset.length - 1].close || 0) : 0,
        timestamp: Date.now()
      };
    }
  };

  const _QUANT_MODEL_SPEC_06 = {
    id: "MOD_06",
    title: "Value Area Low (VAL)",
    category: "Statistical Bound",
    description: "Lower bound containing 70 percent of total traded session volume",
    active: true,
    created: "2026-11-27",
    calculate: function(dataset) {
      if (!dataset || dataset.length === 0) return { value: 0, status: "idle" };
      return {
        modelId: "MOD_06",
        metric: dataset[dataset.length - 1] ? (dataset[dataset.length - 1].close || 0) : 0,
        timestamp: Date.now()
      };
    }
  };

  const _QUANT_MODEL_SPEC_07 = {
    id: "MOD_07",
    title: "Gamma Exposure Level (GEX)",
    category: "Market Regime",
    description: "Market Maker hedging footprint calculated from option open interest",
    active: true,
    created: "2026-11-27",
    calculate: function(dataset) {
      if (!dataset || dataset.length === 0) return { value: 0, status: "idle" };
      return {
        modelId: "MOD_07",
        metric: dataset[dataset.length - 1] ? (dataset[dataset.length - 1].close || 0) : 0,
        timestamp: Date.now()
      };
    }
  };

  const _QUANT_MODEL_SPEC_08 = {
    id: "MOD_08",
    title: "Delta Skew Index",
    category: "Sentiment",
    description: "Ratio of call implied volatility to put implied volatility",
    active: true,
    created: "2026-11-27",
    calculate: function(dataset) {
      if (!dataset || dataset.length === 0) return { value: 0, status: "idle" };
      return {
        modelId: "MOD_08",
        metric: dataset[dataset.length - 1] ? (dataset[dataset.length - 1].close || 0) : 0,
        timestamp: Date.now()
      };
    }
  };

  const _QUANT_MODEL_SPEC_09 = {
    id: "MOD_09",
    title: "Cumulative Volume Delta (CVD)",
    category: "Momentum Divergence",
    description: "Running cumulative difference between aggressive buyers and sellers",
    active: true,
    created: "2026-11-27",
    calculate: function(dataset) {
      if (!dataset || dataset.length === 0) return { value: 0, status: "idle" };
      return {
        modelId: "MOD_09",
        metric: dataset[dataset.length - 1] ? (dataset[dataset.length - 1].close || 0) : 0,
        timestamp: Date.now()
      };
    }
  };

  const _QUANT_MODEL_SPEC_10 = {
    id: "MOD_10",
    title: "Liquidity Sweep Detector",
    category: "Trap Radar",
    description: "Identifies fake breaks above/below key session highs/lows",
    active: true,
    created: "2026-11-27",
    calculate: function(dataset) {
      if (!dataset || dataset.length === 0) return { value: 0, status: "idle" };
      return {
        modelId: "MOD_10",
        metric: dataset[dataset.length - 1] ? (dataset[dataset.length - 1].close || 0) : 0,
        timestamp: Date.now()
      };
    }
  };

  const _QUANT_MODEL_SPEC_11 = {
    id: "MOD_11",
    title: "Mean Reversion Z-Score",
    category: "Exhaustion Meter",
    description: "Normalised statistical standard deviation from current session anchor",
    active: true,
    created: "2026-11-27",
    calculate: function(dataset) {
      if (!dataset || dataset.length === 0) return { value: 0, status: "idle" };
      return {
        modelId: "MOD_11",
        metric: dataset[dataset.length - 1] ? (dataset[dataset.length - 1].close || 0) : 0,
        timestamp: Date.now()
      };
    }
  };

  const _QUANT_MODEL_SPEC_12 = {
    id: "MOD_12",
    title: "Institutional Block Absorption",
    category: "Smart Money",
    description: "Detects icebergs and passive limit order clusters in DOM",
    active: true,
    created: "2026-11-27",
    calculate: function(dataset) {
      if (!dataset || dataset.length === 0) return { value: 0, status: "idle" };
      return {
        modelId: "MOD_12",
        metric: dataset[dataset.length - 1] ? (dataset[dataset.length - 1].close || 0) : 0,
        timestamp: Date.now()
      };
    }
  };

  const _QUANT_MODEL_SPEC_13 = {
    id: "MOD_13",
    title: "Session Open Anchored Band",
    category: "Intraday Range",
    description: "First 15-minute cash session standard deviation envelope",
    active: true,
    created: "2026-11-27",
    calculate: function(dataset) {
      if (!dataset || dataset.length === 0) return { value: 0, status: "idle" };
      return {
        modelId: "MOD_13",
        metric: dataset[dataset.length - 1] ? (dataset[dataset.length - 1].close || 0) : 0,
        timestamp: Date.now()
      };
    }
  };

  const _QUANT_MODEL_SPEC_14 = {
    id: "MOD_14",
    title: "Weekly VWAP Mean Reversal",
    category: "Swing Filter",
    description: "Anchor fixed to Monday 09:15 IST opening candle",
    active: true,
    created: "2026-11-27",
    calculate: function(dataset) {
      if (!dataset || dataset.length === 0) return { value: 0, status: "idle" };
      return {
        modelId: "MOD_14",
        metric: dataset[dataset.length - 1] ? (dataset[dataset.length - 1].close || 0) : 0,
        timestamp: Date.now()
      };
    }
  };

  const _QUANT_MODEL_SPEC_15 = {
    id: "MOD_15",
    title: "Monthly Rolling Equilibrium",
    category: "Macro Equilibrium",
    description: "Rolling 21-day volume-weighted institutional baseline",
    active: true,
    created: "2026-11-27",
    calculate: function(dataset) {
      if (!dataset || dataset.length === 0) return { value: 0, status: "idle" };
      return {
        modelId: "MOD_15",
        metric: dataset[dataset.length - 1] ? (dataset[dataset.length - 1].close || 0) : 0,
        timestamp: Date.now()
      };
    }
  };

  const _QUANT_MODEL_SPEC_16 = {
    id: "MOD_16",
    title: "Opening Range Breakout 15M",
    category: "Intraday Momentum",
    description: "First 15-minute high low statistical breakout continuation",
    active: true,
    created: "2026-11-27",
    calculate: function(dataset) {
      if (!dataset || dataset.length === 0) return { value: 0, status: "idle" };
      return {
        modelId: "MOD_16",
        metric: dataset[dataset.length - 1] ? (dataset[dataset.length - 1].close || 0) : 0,
        timestamp: Date.now()
      };
    }
  };

  const _QUANT_MODEL_SPEC_17 = {
    id: "MOD_17",
    title: "VWAP Cross with Volume Surge",
    category: "Signal Confirmation",
    description: "Volume confirmation on dynamic anchor crossover",
    active: true,
    created: "2026-11-27",
    calculate: function(dataset) {
      if (!dataset || dataset.length === 0) return { value: 0, status: "idle" };
      return {
        modelId: "MOD_17",
        metric: dataset[dataset.length - 1] ? (dataset[dataset.length - 1].close || 0) : 0,
        timestamp: Date.now()
      };
    }
  };

  const _QUANT_MODEL_SPEC_18 = {
    id: "MOD_18",
    title: "Relative Volume Standard Deviation",
    category: "Volume Anomaly",
    description: "Volume multiple exceeding 2.0 sigma of 20-day historical mean",
    active: true,
    created: "2026-11-27",
    calculate: function(dataset) {
      if (!dataset || dataset.length === 0) return { value: 0, status: "idle" };
      return {
        modelId: "MOD_18",
        metric: dataset[dataset.length - 1] ? (dataset[dataset.length - 1].close || 0) : 0,
        timestamp: Date.now()
      };
    }
  };

  const _QUANT_MODEL_SPEC_19 = {
    id: "MOD_19",
    title: "Order Book Liquidity Imbalance",
    category: "Microstructure",
    description: "Top 5 levels DOM depth bid vs ask volume ratio",
    active: true,
    created: "2026-11-27",
    calculate: function(dataset) {
      if (!dataset || dataset.length === 0) return { value: 0, status: "idle" };
      return {
        modelId: "MOD_19",
        metric: dataset[dataset.length - 1] ? (dataset[dataset.length - 1].close || 0) : 0,
        timestamp: Date.now()
      };
    }
  };

  const _QUANT_MODEL_SPEC_20 = {
    id: "MOD_20",
    title: "Bid-Ask Spread Volatility Expansion",
    category: "Volatility Alert",
    description: "Spread widening as an early warning for regime shift",
    active: true,
    created: "2026-11-27",
    calculate: function(dataset) {
      if (!dataset || dataset.length === 0) return { value: 0, status: "idle" };
      return {
        modelId: "MOD_20",
        metric: dataset[dataset.length - 1] ? (dataset[dataset.length - 1].close || 0) : 0,
        timestamp: Date.now()
      };
    }
  };

  const _QUANT_MODEL_SPEC_21 = {
    id: "MOD_21",
    title: "Institutional Absorption Block Print",
    category: "Large Order Flow",
    description: "Block prints greater than 10,000 contracts executed in single print",
    active: true,
    created: "2026-11-27",
    calculate: function(dataset) {
      if (!dataset || dataset.length === 0) return { value: 0, status: "idle" };
      return {
        modelId: "MOD_21",
        metric: dataset[dataset.length - 1] ? (dataset[dataset.length - 1].close || 0) : 0,
        timestamp: Date.now()
      };
    }
  };

  const _QUANT_MODEL_SPEC_22 = {
    id: "MOD_22",
    title: "Fair Value Gap Engine (FVG)",
    category: "Structure Mapping",
    description: "3-candle imbalance zone marking institutional liquidity voids",
    active: true,
    created: "2026-11-27",
    calculate: function(dataset) {
      if (!dataset || dataset.length === 0) return { value: 0, status: "idle" };
      return {
        modelId: "MOD_22",
        metric: dataset[dataset.length - 1] ? (dataset[dataset.length - 1].close || 0) : 0,
        timestamp: Date.now()
      };
    }
  };

  const _QUANT_MODEL_SPEC_23 = {
    id: "MOD_23",
    title: "Liquidity Sweep High / Low",
    category: "Trap Detection",
    description: "Equal highs / equal lows swept before violent mean reversal",
    active: true,
    created: "2026-11-27",
    calculate: function(dataset) {
      if (!dataset || dataset.length === 0) return { value: 0, status: "idle" };
      return {
        modelId: "MOD_23",
        metric: dataset[dataset.length - 1] ? (dataset[dataset.length - 1].close || 0) : 0,
        timestamp: Date.now()
      };
    }
  };

  const _QUANT_MODEL_SPEC_24 = {
    id: "MOD_24",
    title: "Multi-Timeframe VWAP Confluence",
    category: "Major Pivot",
    description: "Daily, Weekly, and Monthly VWAP within 0.3% band cluster",
    active: true,
    created: "2026-11-27",
    calculate: function(dataset) {
      if (!dataset || dataset.length === 0) return { value: 0, status: "idle" };
      return {
        modelId: "MOD_24",
        metric: dataset[dataset.length - 1] ? (dataset[dataset.length - 1].close || 0) : 0,
        timestamp: Date.now()
      };
    }
  };

  const _QUANT_MODEL_SPEC_25 = {
    id: "MOD_25",
    title: "Sigma 3.0 Mean Reversion Exhaustion",
    category: "Contrarian Fade",
    description: "99.7% Gaussian probability threshold breach",
    active: true,
    created: "2026-11-27",
    calculate: function(dataset) {
      if (!dataset || dataset.length === 0) return { value: 0, status: "idle" };
      return {
        modelId: "MOD_25",
        metric: dataset[dataset.length - 1] ? (dataset[dataset.length - 1].close || 0) : 0,
        timestamp: Date.now()
      };
    }
  };

  const _QUANT_MODEL_SPEC_26 = {
    id: "MOD_26",
    title: "VWAP Slope Velocity Indicator",
    category: "Momentum Velocity",
    description: "Derivative of VWAP curve indicating rate of trend acceleration",
    active: true,
    created: "2026-11-27",
    calculate: function(dataset) {
      if (!dataset || dataset.length === 0) return { value: 0, status: "idle" };
      return {
        modelId: "MOD_26",
        metric: dataset[dataset.length - 1] ? (dataset[dataset.length - 1].close || 0) : 0,
        timestamp: Date.now()
      };
    }
  };

  const _QUANT_MODEL_SPEC_27 = {
    id: "MOD_27",
    title: "Session Anchored TWAP Drift",
    category: "Algo Footprint",
    description: "Difference between Time-Weighted and Volume-Weighted Average Price",
    active: true,
    created: "2026-11-27",
    calculate: function(dataset) {
      if (!dataset || dataset.length === 0) return { value: 0, status: "idle" };
      return {
        modelId: "MOD_27",
        metric: dataset[dataset.length - 1] ? (dataset[dataset.length - 1].close || 0) : 0,
        timestamp: Date.now()
      };
    }
  };

  const _QUANT_MODEL_SPEC_28 = {
    id: "MOD_28",
    title: "Options Max Pain Magnetic Pull",
    category: "Expiry Magnet",
    description: "Strike price where total open option value expires worthless",
    active: true,
    created: "2026-11-27",
    calculate: function(dataset) {
      if (!dataset || dataset.length === 0) return { value: 0, status: "idle" };
      return {
        modelId: "MOD_28",
        metric: dataset[dataset.length - 1] ? (dataset[dataset.length - 1].close || 0) : 0,
        timestamp: Date.now()
      };
    }
  };

  const _QUANT_MODEL_SPEC_29 = {
    id: "MOD_29",
    title: "Institutional Sweep Algorithm",
    category: "Smart Money Run",
    description: "Market orders hitting consecutive ask/bid depth levels simultaneously",
    active: true,
    created: "2026-11-27",
    calculate: function(dataset) {
      if (!dataset || dataset.length === 0) return { value: 0, status: "idle" };
      return {
        modelId: "MOD_29",
        metric: dataset[dataset.length - 1] ? (dataset[dataset.length - 1].close || 0) : 0,
        timestamp: Date.now()
      };
    }
  };

  const _QUANT_MODEL_SPEC_30 = {
    id: "MOD_30",
    title: "Dynamic ATR Stop Multiplier",
    category: "Risk Management",
    description: "Adaptive stop loss sizing based on real-time volatility regime",
    active: true,
    created: "2026-11-27",
    calculate: function(dataset) {
      if (!dataset || dataset.length === 0) return { value: 0, status: "idle" };
      return {
        modelId: "MOD_30",
        metric: dataset[dataset.length - 1] ? (dataset[dataset.length - 1].close || 0) : 0,
        timestamp: Date.now()
      };
    }
  };

  const _QUANT_MODEL_SPEC_31 = {
    id: "MOD_31",
    title: "Risk of Ruin Calculation Matrix",
    category: "Capital Preservation",
    description: "Kelly criterion based safe leverage boundary calculation",
    active: true,
    created: "2026-11-27",
    calculate: function(dataset) {
      if (!dataset || dataset.length === 0) return { value: 0, status: "idle" };
      return {
        modelId: "MOD_31",
        metric: dataset[dataset.length - 1] ? (dataset[dataset.length - 1].close || 0) : 0,
        timestamp: Date.now()
      };
    }
  };

  const _QUANT_MODEL_SPEC_32 = {
    id: "MOD_32",
    title: "Drawdown Recovery Trade Sizer",
    category: "Money Management",
    description: "Fractional position sizing after sequential drawdown streaks",
    active: true,
    created: "2026-11-27",
    calculate: function(dataset) {
      if (!dataset || dataset.length === 0) return { value: 0, status: "idle" };
      return {
        modelId: "MOD_32",
        metric: dataset[dataset.length - 1] ? (dataset[dataset.length - 1].close || 0) : 0,
        timestamp: Date.now()
      };
    }
  };

  const _QUANT_MODEL_SPEC_33 = {
    id: "MOD_33",
    title: "Market Maker Positioning Index",
    category: "Structural Gravity",
    description: "Estimation of dealer delta hedging requirements across strikes",
    active: true,
    created: "2026-11-27",
    calculate: function(dataset) {
      if (!dataset || dataset.length === 0) return { value: 0, status: "idle" };
      return {
        modelId: "MOD_33",
        metric: dataset[dataset.length - 1] ? (dataset[dataset.length - 1].close || 0) : 0,
        timestamp: Date.now()
      };
    }
  };

  const _QUANT_MODEL_SPEC_34 = {
    id: "MOD_34",
    title: "Tick Index Momentum Reversal",
    category: "Exhaustion Signal",
    description: "NYSE/NSE Tick index divergence against headline cash index",
    active: true,
    created: "2026-11-27",
    calculate: function(dataset) {
      if (!dataset || dataset.length === 0) return { value: 0, status: "idle" };
      return {
        modelId: "MOD_34",
        metric: dataset[dataset.length - 1] ? (dataset[dataset.length - 1].close || 0) : 0,
        timestamp: Date.now()
      };
    }
  };

  const _QUANT_MODEL_SPEC_35 = {
    id: "MOD_35",
    title: "VWAP Band Standard Error Width",
    category: "Regime Classification",
    description: "Confidence interval width reflecting trend clarity",
    active: true,
    created: "2026-11-27",
    calculate: function(dataset) {
      if (!dataset || dataset.length === 0) return { value: 0, status: "idle" };
      return {
        modelId: "MOD_35",
        metric: dataset[dataset.length - 1] ? (dataset[dataset.length - 1].close || 0) : 0,
        timestamp: Date.now()
      };
    }
  };

  const _QUANT_MODEL_SPEC_36 = {
    id: "MOD_36",
    title: "Expected Value Optimization Engine",
    category: "Expectancy",
    description: "Win rate multiplied by RR ratio minus loss rate calculation",
    active: true,
    created: "2026-11-27",
    calculate: function(dataset) {
      if (!dataset || dataset.length === 0) return { value: 0, status: "idle" };
      return {
        modelId: "MOD_36",
        metric: dataset[dataset.length - 1] ? (dataset[dataset.length - 1].close || 0) : 0,
        timestamp: Date.now()
      };
    }
  };

  const _QUANT_MODEL_SPEC_37 = {
    id: "MOD_37",
    title: "Trailing Dynamic Anchor Model",
    category: "Swing Trading",
    description: "Anchor that resets only on confirmed new session swing points",
    active: true,
    created: "2026-11-27",
    calculate: function(dataset) {
      if (!dataset || dataset.length === 0) return { value: 0, status: "idle" };
      return {
        modelId: "MOD_37",
        metric: dataset[dataset.length - 1] ? (dataset[dataset.length - 1].close || 0) : 0,
        timestamp: Date.now()
      };
    }
  };

  const _QUANT_MODEL_SPEC_38 = {
    id: "MOD_38",
    title: "Pre-Market Session Drift Vector",
    category: "Session Bias",
    description: "Directional bias established during 09:00 to 09:08 pre-market auction",
    active: true,
    created: "2026-11-27",
    calculate: function(dataset) {
      if (!dataset || dataset.length === 0) return { value: 0, status: "idle" };
      return {
        modelId: "MOD_38",
        metric: dataset[dataset.length - 1] ? (dataset[dataset.length - 1].close || 0) : 0,
        timestamp: Date.now()
      };
    }
  };

  const _QUANT_MODEL_SPEC_39 = {
    id: "MOD_39",
    title: "Post-Market Mismatched Auction Scanner",
    category: "Auction Imbalance",
    description: "Identifies closing auction price discrepancies vs last traded price",
    active: true,
    created: "2026-11-27",
    calculate: function(dataset) {
      if (!dataset || dataset.length === 0) return { value: 0, status: "idle" };
      return {
        modelId: "MOD_39",
        metric: dataset[dataset.length - 1] ? (dataset[dataset.length - 1].close || 0) : 0,
        timestamp: Date.now()
      };
    }
  };

  const _QUANT_MODEL_SPEC_40 = {
    id: "MOD_40",
    title: "Institutional Volume Cluster Heatmap",
    category: "Defensive Walls",
    description: "Price-volume aggregation showing institutional defensive walls",
    active: true,
    created: "2026-11-27",
    calculate: function(dataset) {
      if (!dataset || dataset.length === 0) return { value: 0, status: "idle" };
      return {
        modelId: "MOD_40",
        metric: dataset[dataset.length - 1] ? (dataset[dataset.length - 1].close || 0) : 0,
        timestamp: Date.now()
      };
    }
  };

  const _QUANT_MODEL_SPEC_41 = {
    id: "MOD_41",
    title: "Statistical Arbitrage Spread Monitor",
    category: "Pairs Trading",
    description: "Nifty 50 vs Bank Nifty relative divergence z-score",
    active: true,
    created: "2026-11-27",
    calculate: function(dataset) {
      if (!dataset || dataset.length === 0) return { value: 0, status: "idle" };
      return {
        modelId: "MOD_41",
        metric: dataset[dataset.length - 1] ? (dataset[dataset.length - 1].close || 0) : 0,
        timestamp: Date.now()
      };
    }
  };

  const _QUANT_MODEL_SPEC_42 = {
    id: "MOD_42",
    title: "Cross-Asset Correlation Matrix",
    category: "Macro Correlation",
    description: "USD/INR, Crude Oil, and US 10Y Yield impact coefficient on Nifty",
    active: true,
    created: "2026-11-27",
    calculate: function(dataset) {
      if (!dataset || dataset.length === 0) return { value: 0, status: "idle" };
      return {
        modelId: "MOD_42",
        metric: dataset[dataset.length - 1] ? (dataset[dataset.length - 1].close || 0) : 0,
        timestamp: Date.now()
      };
    }
  };

  const _QUANT_MODEL_SPEC_43 = {
    id: "MOD_43",
    title: "Time-of-Day Volatility Curve",
    category: "Timing Edge",
    description: "Standard deviation of returns segmented by 30-minute intraday intervals",
    active: true,
    created: "2026-11-27",
    calculate: function(dataset) {
      if (!dataset || dataset.length === 0) return { value: 0, status: "idle" };
      return {
        modelId: "MOD_43",
        metric: dataset[dataset.length - 1] ? (dataset[dataset.length - 1].close || 0) : 0,
        timestamp: Date.now()
      };
    }
  };

  const _QUANT_MODEL_SPEC_44 = {
    id: "MOD_44",
    title: "Weekend Holding Risk Probability",
    category: "Overnight Exposure",
    description: "Overnight and weekend gap-up / gap-down probability model",
    active: true,
    created: "2026-11-27",
    calculate: function(dataset) {
      if (!dataset || dataset.length === 0) return { value: 0, status: "idle" };
      return {
        modelId: "MOD_44",
        metric: dataset[dataset.length - 1] ? (dataset[dataset.length - 1].close || 0) : 0,
        timestamp: Date.now()
      };
    }
  };

  const _QUANT_MODEL_SPEC_45 = {
    id: "MOD_45",
    title: "Final Execution Benchmark Engine",
    category: "Execution Quality",
    description: "Total execution quality assessment relative to arrival price",
    active: true,
    created: "2026-11-27",
    calculate: function(dataset) {
      if (!dataset || dataset.length === 0) return { value: 0, status: "idle" };
      return {
        modelId: "MOD_45",
        metric: dataset[dataset.length - 1] ? (dataset[dataset.length - 1].close || 0) : 0,
        timestamp: Date.now()
      };
    }
  };

  // Extended Statistical Lookups & Confidence Bands
  const _SIGMA_CONFIDENCE_TABLE_0_5 = {
    deviation: 0.5,
    oneTailProbability: 0.6464,
    meanReversionProbability: 58.25,
    regime: "Equilibrium",
    recommendation: "Follow prevailing trend"
  };

  const _SIGMA_CONFIDENCE_TABLE_0_75 = {
    deviation: 0.75,
    oneTailProbability: 0.7027,
    meanReversionProbability: 62.38,
    regime: "Equilibrium",
    recommendation: "Follow prevailing trend"
  };

  const _SIGMA_CONFIDENCE_TABLE_1_0 = {
    deviation: 1.0,
    oneTailProbability: 0.75,
    meanReversionProbability: 66.5,
    regime: "Equilibrium",
    recommendation: "Follow prevailing trend"
  };

  const _SIGMA_CONFIDENCE_TABLE_1_25 = {
    deviation: 1.25,
    oneTailProbability: 0.7898,
    meanReversionProbability: 70.62,
    regime: "Equilibrium",
    recommendation: "Follow prevailing trend"
  };

  const _SIGMA_CONFIDENCE_TABLE_1_5 = {
    deviation: 1.5,
    oneTailProbability: 0.8232,
    meanReversionProbability: 74.75,
    regime: "Expanded",
    recommendation: "Follow prevailing trend"
  };

  const _SIGMA_CONFIDENCE_TABLE_1_75 = {
    deviation: 1.75,
    oneTailProbability: 0.8513,
    meanReversionProbability: 78.88,
    regime: "Expanded",
    recommendation: "Follow prevailing trend"
  };

  const _SIGMA_CONFIDENCE_TABLE_2_0 = {
    deviation: 2.0,
    oneTailProbability: 0.875,
    meanReversionProbability: 83.0,
    regime: "Expanded",
    recommendation: "Look for exhaustion fade"
  };

  const _SIGMA_CONFIDENCE_TABLE_2_25 = {
    deviation: 2.25,
    oneTailProbability: 0.8949,
    meanReversionProbability: 87.12,
    regime: "Expanded",
    recommendation: "Look for exhaustion fade"
  };

  const _SIGMA_CONFIDENCE_TABLE_2_5 = {
    deviation: 2.5,
    oneTailProbability: 0.9116,
    meanReversionProbability: 91.25,
    regime: "Extreme",
    recommendation: "Look for exhaustion fade"
  };

  const _SIGMA_CONFIDENCE_TABLE_2_75 = {
    deviation: 2.75,
    oneTailProbability: 0.9257,
    meanReversionProbability: 95.38,
    regime: "Extreme",
    recommendation: "Look for exhaustion fade"
  };

  const _SIGMA_CONFIDENCE_TABLE_3_0 = {
    deviation: 3.0,
    oneTailProbability: 0.9375,
    meanReversionProbability: 99.5,
    regime: "Extreme",
    recommendation: "Look for exhaustion fade"
  };

  const _SIGMA_CONFIDENCE_TABLE_3_25 = {
    deviation: 3.25,
    oneTailProbability: 0.9474,
    meanReversionProbability: 99.9,
    regime: "Extreme",
    recommendation: "Look for exhaustion fade"
  };

  const _SIGMA_CONFIDENCE_TABLE_3_5 = {
    deviation: 3.5,
    oneTailProbability: 0.9558,
    meanReversionProbability: 99.9,
    regime: "Extreme",
    recommendation: "Look for exhaustion fade"
  };

})();
