/**
 * YourTradeBot — Terminal 1 Institutional Candlestick & AI Background
 * 
 * Features:
 * - Hypnotic, ultra-smooth drifting financial candlestick streams (Bullish Emerald / Bearish Crimson)
 * - Institutional Quant Overlays: Anchored VWAP curve, ±2σ bands, and subtle liquidity grid
 * - Volumetric Ambient Blurred Aurora (Emerald & Cyan/Indigo AI pulses)
 * - Periodic AI Neural Scan Waves: Identifies institutional traps and reveals quant edge over manual noise
 * - 60 FPS GPU-accelerated Canvas with low CPU overhead & battery saver (auto-pauses on hidden tab)
 */

(function () {
  'use strict';

  function initCandlestickAIBackground() {
    const canvas = document.getElementById('candlestick-ai-canvas');
    if (!canvas) return;

    const ctx = canvas.getContext('2d', { alpha: false });
    if (!ctx) return;

    let width = 0;
    let height = 0;
    let dpr = 1;

    // Track state
    let animationFrameId = null;
    let isTabVisible = true;
    let lastTime = performance.now();

    // Data structures for candles
    const candleWidth = 9;
    const candleSpacing = 14;
    let candles = [];
    let basePrice = 25350;
    let currentTrend = 1;
    let trendCountdown = 30;

    // AI Neural Scan state
    let scanActive = false;
    let scanProgress = 0; // 0 to 1
    let nextScanTime = performance.now() + 3500; // First scan in 3.5s
    const scanCooldown = 9000; // Scan every 9 seconds
    let activePivots = [];

    // Volumetric glow orb state
    let orbTheta1 = 0;
    let orbTheta2 = Math.PI;

    // Generate initial continuous candle data
    function generateCandle(prevClose, index) {
      if (--trendCountdown <= 0) {
        currentTrend = Math.random() > 0.48 ? 1 : -1;
        trendCountdown = Math.floor(15 + Math.random() * 25);
      }

      // Volatility with mean reversion
      const drift = currentTrend * (Math.random() * 8 + 2);
      const meanReversion = (basePrice - prevClose) * 0.015;
      const change = drift + meanReversion + (Math.random() - 0.5) * 14;

      const open = prevClose;
      const close = open + change;
      const high = Math.max(open, close) + Math.random() * 9 + 1;
      const low = Math.min(open, close) - (Math.random() * 9 + 1);

      return {
        open,
        close,
        high,
        low,
        isBullish: close >= open,
        x: index * (candleWidth + candleSpacing),
        signal: null // Assigned dynamically during AI scans
      };
    }

    function initCandleData() {
      candles = [];
      const count = Math.ceil(width / (candleWidth + candleSpacing)) + 25;
      let lastClose = basePrice;

      for (let i = 0; i < count; i++) {
        const c = generateCandle(lastClose, i);
        lastClose = c.close;
        candles.push(c);
      }
    }

    function handleResize() {
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      width = window.innerWidth;
      height = window.innerHeight;

      canvas.width = Math.floor(width * dpr);
      canvas.height = Math.floor(height * dpr);
      ctx.scale(dpr, dpr);

      initCandleData();
    }

    window.addEventListener('resize', handleResize, { passive: true });
    handleResize();

    // Map price value to screen Y
    function priceToY(price, minP, maxP) {
      const range = maxP - minP || 1;
      // Keep inside 20% to 80% vertical canvas area
      const norm = (price - minP) / range;
      const chartTop = height * 0.22;
      const chartHeight = height * 0.56;
      return chartTop + (1 - norm) * chartHeight;
    }

    // Main animation frame
    function render(now) {
      if (!isTabVisible) return;

      const dt = Math.min((now - lastTime) / 1000, 0.1);
      lastTime = now;

      // 1. Shift candles left (Drift speed: ~22px/sec)
      const shiftSpeed = 20 * dt;
      for (let i = 0; i < candles.length; i++) {
        candles[i].x -= shiftSpeed;
      }

      // If the first candle has drifted completely off screen left
      while (candles.length > 0 && candles[0].x < -(candleWidth + 10)) {
        candles.shift();
      }

      // Add new candles to the right edge
      const lastCandle = candles[candles.length - 1];
      if (lastCandle && lastCandle.x < width + 100) {
        const nextX = lastCandle.x + candleWidth + candleSpacing;
        const newC = generateCandle(lastCandle.close, 0);
        newC.x = nextX;
        candles.push(newC);
      }

      // Pulse the latest candle slightly to simulate live ticks
      if (candles.length > 0) {
        const live = candles[candles.length - 1];
        const tick = Math.sin(now * 0.006) * 1.5;
        live.close = live.open + (live.isBullish ? 4 + tick : -4 - tick);
        live.high = Math.max(live.high, live.close + 2);
        live.low = Math.min(live.low, live.close - 2);
      }

      // 2. Clear background to dark obsidian
      ctx.fillStyle = '#030712';
      ctx.fillRect(0, 0, width, height);

      // 3. Render Volumetric Ambient AI Aurora Mesh (Slow hypnotic breathing)
      orbTheta1 += 0.005;
      orbTheta2 += 0.0035;

      const orb1X = width * 0.35 + Math.cos(orbTheta1) * (width * 0.2);
      const orb1Y = height * 0.45 + Math.sin(orbTheta1 * 0.8) * (height * 0.18);
      const orb1Rad = Math.min(width, height) * 0.55;

      const grad1 = ctx.createRadialGradient(orb1X, orb1Y, 10, orb1X, orb1Y, orb1Rad);
      // AI Neural Cyan / Indigo
      grad1.addColorStop(0, 'rgba(56, 189, 248, 0.11)');
      grad1.addColorStop(0.5, 'rgba(37, 99, 235, 0.06)');
      grad1.addColorStop(1, 'rgba(3, 7, 18, 0)');
      ctx.fillStyle = grad1;
      ctx.fillRect(0, 0, width, height);

      const orb2X = width * 0.72 + Math.sin(orbTheta2) * (width * 0.2);
      const orb2Y = height * 0.55 + Math.cos(orbTheta2 * 0.7) * (height * 0.16);
      const orb2Rad = Math.min(width, height) * 0.5;

      const grad2 = ctx.createRadialGradient(orb2X, orb2Y, 10, orb2X, orb2Y, orb2Rad);
      // Quantitative Emerald Edge
      grad2.addColorStop(0, 'rgba(16, 185, 129, 0.10)');
      grad2.addColorStop(0.5, 'rgba(5, 150, 105, 0.04)');
      grad2.addColorStop(1, 'rgba(3, 7, 18, 0)');
      ctx.fillStyle = grad2;
      ctx.fillRect(0, 0, width, height);

      // 4. Calculate Price Bounds for scaling
      let minP = Infinity;
      let maxP = -Infinity;
      for (let i = 0; i < candles.length; i++) {
        if (candles[i].low < minP) minP = candles[i].low;
        if (candles[i].high > maxP) maxP = candles[i].high;
      }
      minP -= 15;
      maxP += 15;

      // 5. Draw Subtle Institutional Quant Grid Lines
      const gridLevels = 5;
      ctx.lineWidth = 1;
      ctx.setLineDash([4, 6]);
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.035)';
      ctx.fillStyle = 'rgba(148, 163, 184, 0.25)';
      ctx.font = '10px monospace';

      for (let g = 0; g <= gridLevels; g++) {
        const p = minP + (maxP - minP) * (g / gridLevels);
        const y = priceToY(p, minP, maxP);
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
        ctx.stroke();

        if (g === 1 || g === 3 || g === 4) {
          ctx.fillText(`₹${p.toFixed(0)}`, width - 58, y - 4);
        }
      }
      ctx.setLineDash([]);

      // 6. Draw Anchored VWAP ±2σ Bands & Central Equidistant Spline
      if (candles.length > 4) {
        ctx.lineWidth = 1.8;
        ctx.strokeStyle = 'rgba(56, 189, 248, 0.28)';
        ctx.beginPath();
        for (let i = 0; i < candles.length; i++) {
          const c = candles[i];
          const typical = (c.high + c.low + c.close) / 3;
          const y = priceToY(typical, minP, maxP);
          if (i === 0) ctx.moveTo(c.x + candleWidth / 2, y);
          else ctx.lineTo(c.x + candleWidth / 2, y);
        }
        ctx.stroke();

        // Upper Exhaustion Band (+2σ)
        ctx.lineWidth = 1;
        ctx.setLineDash([3, 4]);
        ctx.strokeStyle = 'rgba(239, 68, 68, 0.22)';
        ctx.beginPath();
        for (let i = 0; i < candles.length; i++) {
          const c = candles[i];
          const upper = (c.high + c.low + c.close) / 3 + 22;
          const y = priceToY(upper, minP, maxP);
          if (i === 0) ctx.moveTo(c.x + candleWidth / 2, y);
          else ctx.lineTo(c.x + candleWidth / 2, y);
        }
        ctx.stroke();

        // Lower Exhaustion Band (-2σ)
        ctx.strokeStyle = 'rgba(16, 185, 129, 0.22)';
        ctx.beginPath();
        for (let i = 0; i < candles.length; i++) {
          const c = candles[i];
          const lower = (c.high + c.low + c.close) / 3 - 22;
          const y = priceToY(lower, minP, maxP);
          if (i === 0) ctx.moveTo(c.x + candleWidth / 2, y);
          else ctx.lineTo(c.x + candleWidth / 2, y);
        }
        ctx.stroke();
        ctx.setLineDash([]);
      }

      // 7. Check & Update AI Neural Scan Wave
      if (!scanActive && now > nextScanTime) {
        scanActive = true;
        scanProgress = 0;
        // Pick 2-3 prominent candles in view for AI signal callouts
        activePivots = [];
        const inView = candles.filter(c => c.x > width * 0.15 && c.x < width * 0.85);
        if (inView.length > 0) {
          const p1 = inView[Math.floor(inView.length * 0.3)];
          const p2 = inView[Math.floor(inView.length * 0.7)];
          if (p1) activePivots.push({ candle: p1, label: '🟢 VWAP +2σ REVERSAL (98.4%)' });
          if (p2) activePivots.push({ candle: p2, label: '⚡ SMART MONEY TRAP MITIGATED' });
        }
      }

      let scanX = -100;
      if (scanActive) {
        scanProgress += dt * 0.28; // Takes ~3.5 seconds to sweep across screen
        scanX = scanProgress * (width + 200) - 100;

        if (scanProgress >= 1) {
          scanActive = false;
          nextScanTime = now + scanCooldown;
          activePivots = [];
        }
      }

      // 8. Draw Candlesticks (Moving Red & Green Bars with High/Low Wicks)
      for (let i = 0; i < candles.length; i++) {
        const c = candles[i];
        if (c.x < -20 || c.x > width + 20) continue;

        const openY = priceToY(c.open, minP, maxP);
        const closeY = priceToY(c.close, minP, maxP);
        const highY = priceToY(c.high, minP, maxP);
        const lowY = priceToY(c.low, minP, maxP);

        const bodyTop = Math.min(openY, closeY);
        const bodyHeight = Math.max(Math.abs(closeY - openY), 2.5);
        const centerX = c.x + candleWidth / 2;

        // Proximity to AI Scan Beam (Illuminates when scanned)
        const distToScan = Math.abs(c.x - scanX);
        const isIlluminated = scanActive && distToScan < 90;
        const scanGlow = isIlluminated ? (1 - distToScan / 90) : 0;

        if (c.isBullish) {
          // Bullish Emerald
          const alphaFill = 0.22 + scanGlow * 0.45;
          const alphaStroke = 0.55 + scanGlow * 0.45;

          ctx.strokeStyle = `rgba(16, 185, 129, ${alphaStroke})`;
          ctx.fillStyle = `rgba(16, 185, 129, ${alphaFill})`;

          // Wick
          ctx.lineWidth = 1.2;
          ctx.beginPath();
          ctx.moveTo(centerX, highY);
          ctx.lineTo(centerX, lowY);
          ctx.stroke();

          // Body
          ctx.fillRect(c.x, bodyTop, candleWidth, bodyHeight);
          ctx.strokeRect(c.x, bodyTop, candleWidth, bodyHeight);
        } else {
          // Bearish Crimson
          const alphaFill = 0.20 + scanGlow * 0.45;
          const alphaStroke = 0.50 + scanGlow * 0.45;

          ctx.strokeStyle = `rgba(239, 68, 68, ${alphaStroke})`;
          ctx.fillStyle = `rgba(239, 68, 68, ${alphaFill})`;

          // Wick
          ctx.lineWidth = 1.2;
          ctx.beginPath();
          ctx.moveTo(centerX, highY);
          ctx.lineTo(centerX, lowY);
          ctx.stroke();

          // Body
          ctx.fillRect(c.x, bodyTop, candleWidth, bodyHeight);
          ctx.strokeRect(c.x, bodyTop, candleWidth, bodyHeight);
        }
      }

      // 9. Draw AI Scan Beam & Visual Clarity Over Market Noise
      if (scanActive) {
        // Vertical sweeping laser gradient
        const beamGrad = ctx.createLinearGradient(scanX - 55, 0, scanX + 55, 0);
        beamGrad.addColorStop(0, 'rgba(56, 189, 248, 0)');
        beamGrad.addColorStop(0.5, 'rgba(56, 189, 248, 0.22)');
        beamGrad.addColorStop(1, 'rgba(16, 185, 129, 0)');
        ctx.fillStyle = beamGrad;
        ctx.fillRect(scanX - 60, 0, 120, height);

        // Core thin laser line
        ctx.lineWidth = 1.5;
        ctx.strokeStyle = 'rgba(56, 189, 248, 0.65)';
        ctx.beginPath();
        ctx.moveTo(scanX, 0);
        ctx.lineTo(scanX, height);
        ctx.stroke();

        // Draw Callout Badges on Identified Pivots
        for (let p = 0; p < activePivots.length; p++) {
          const item = activePivots[p];
          if (scanX > item.candle.x - 20) {
            const px = item.candle.x;
            const py = priceToY(item.candle.high, minP, maxP) - 16;

            ctx.save();
            ctx.font = '600 10.5px Inter, sans-serif';
            const textWidth = ctx.measureText(item.label).width;

            // Badge Background
            ctx.fillStyle = 'rgba(15, 23, 42, 0.9)';
            ctx.strokeStyle = 'rgba(56, 189, 248, 0.7)';
            ctx.lineWidth = 1;
            ctx.beginPath();
            if (ctx.roundRect) {
              ctx.roundRect(px - textWidth / 2 - 6, py - 12, textWidth + 12, 18, 4);
            } else {
              ctx.rect(px - textWidth / 2 - 6, py - 12, textWidth + 12, 18);
            }
            ctx.fill();
            ctx.stroke();

            // Badge Text
            ctx.fillStyle = '#38bdf8';
            ctx.fillText(item.label, px - textWidth / 2, py + 1);

            // Connector line to candle
            ctx.strokeStyle = 'rgba(56, 189, 248, 0.5)';
            ctx.beginPath();
            ctx.moveTo(px, py + 7);
            ctx.lineTo(px, priceToY(item.candle.high, minP, maxP));
            ctx.stroke();
            ctx.restore();
          }
        }
      }

      // Request next frame
      animationFrameId = requestAnimationFrame(render);
    }

    // Auto-pause when tab is hidden to save CPU/battery
    document.addEventListener('visibilitychange', () => {
      if (document.hidden) {
        isTabVisible = false;
        if (animationFrameId) cancelAnimationFrame(animationFrameId);
      } else {
        isTabVisible = true;
        lastTime = performance.now();
        animationFrameId = requestAnimationFrame(render);
      }
    });

    // Start rendering loop
    animationFrameId = requestAnimationFrame(render);
  }

  // Initialize on DOM load
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initCandlestickAIBackground);
  } else {
    initCandlestickAIBackground();
  }
})();
