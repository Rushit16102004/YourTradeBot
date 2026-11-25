/**
 * YourTradeBot — Terminal 1 Masterpiece Trading & AI Background
 * 
 * Proprietary Quantum Matrix Architecture:
 * - 3 Concurrent Parallax Candlestick Streams (Macro Depth, Core Institutional VWAP ±2σ, Kinetic Scalp)
 * - AI Neural Synapse Constellation connecting swing pivots with traveling algorithmic energy pulses
 * - Interactive Pointer & Touch Quantum Well: Touch/mouse moves cause luminous ripple & particle spark emission
 * - Sweeping AI Dual-Photon Laser Scanner with HUD Holographic Confluence Badges
 * - Rising Translucent Volume Columns along the lower macro depth plane
 * - 3-Point Hypnotic Volumetric Aurora Nebulae (Azure, Emerald, Violet)
 * - 60 FPS GPU-accelerated Canvas with auto-pause on hidden tab for zero CPU overhead
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

    let animationFrameId = null;
    let isTabVisible = true;
    let lastTime = performance.now();

    // --- Interactive Pointer & Touch State ---
    let pointerX = -9999;
    let pointerY = -9999;
    let pointerActive = false;
    let pointerRadius = 140;
    let pointerParticles = [];

    // --- AI Neural Scanner State ---
    let scanActive = false;
    let scanProgress = 0;
    let nextScanTime = performance.now() + 2500;
    const scanCooldown = 8000;
    let activeCallouts = [];
    let scanSparkles = [];

    // --- Aurora Breathing Angles ---
    let auroraTheta1 = 0;
    let auroraTheta2 = Math.PI * 0.6;
    let auroraTheta3 = Math.PI * 1.3;

    // --- Neural Synapse Pulses ---
    let synapsePulses = [];

    /**
     * Candlestick Stream Definition with Parallax Depth
     */
    class CandleStream {
      constructor(config) {
        this.name = config.name;
        this.yMinPct = config.yMinPct;
        this.yMaxPct = config.yMaxPct;
        this.candleWidth = config.candleWidth;
        this.candleSpacing = config.candleSpacing;
        this.speed = config.speed;
        this.basePrice = config.basePrice;
        this.volatility = config.volatility || 12;
        this.hasVWAP = !!config.hasVWAP;
        this.hasVolume = !!config.hasVolume;
        this.hasNeuralNodes = !!config.hasNeuralNodes;
        this.alphaMod = config.alphaMod || 1.0;

        this.candles = [];
        this.currentTrend = 1;
        this.trendCountdown = 20;
      }

      generateCandle(prevClose, index) {
        if (--this.trendCountdown <= 0) {
          this.currentTrend = Math.random() > 0.48 ? 1 : -1;
          this.trendCountdown = Math.floor(12 + Math.random() * 24);
        }

        const drift = this.currentTrend * (Math.random() * (this.volatility * 0.65) + 1.8);
        const meanReversion = (this.basePrice - prevClose) * 0.016;
        const change = drift + meanReversion + (Math.random() - 0.5) * this.volatility;

        const open = prevClose;
        const close = open + change;
        const wickSpread = Math.random() * (this.volatility * 0.85) + 3.0;
        const high = Math.max(open, close) + wickSpread;
        const low = Math.min(open, close) - wickSpread;
        const volume = Math.floor(30 + Math.random() * 90 + (Math.abs(change) / this.volatility) * 70);

        return {
          open,
          close,
          high,
          low,
          volume,
          isBullish: close >= open,
          x: index * (this.candleWidth + this.candleSpacing)
        };
      }

      init(canvasWidth) {
        this.candles = [];
        const step = this.candleWidth + this.candleSpacing;
        const count = Math.ceil(canvasWidth / step) + 24;
        let lastClose = this.basePrice;

        for (let i = 0; i < count; i++) {
          const c = this.generateCandle(lastClose, i);
          lastClose = c.close;
          this.candles.push(c);
        }
      }

      update(dt, canvasWidth, now) {
        const step = this.candleWidth + this.candleSpacing;
        const shift = this.speed * dt;

        // Drift left
        for (let i = 0; i < this.candles.length; i++) {
          this.candles[i].x -= shift;
        }

        // Evict off-screen candles
        while (this.candles.length > 0 && this.candles[0].x < -(this.candleWidth + 20)) {
          this.candles.shift();
        }

        // Spawn new candles on right
        const last = this.candles[this.candles.length - 1];
        if (last && last.x < canvasWidth + 140) {
          const newC = this.generateCandle(last.close, 0);
          newC.x = last.x + step;
          this.candles.push(newC);
        }

        // Dynamic tick pulse on the rightmost active candle
        if (this.candles.length > 0) {
          const live = this.candles[this.candles.length - 1];
          const tick = Math.sin(now * 0.008 + (this.hasVWAP ? 1 : 2.5)) * (this.volatility * 0.18);
          live.close = live.open + (live.isBullish ? 3.5 + tick : -3.5 - tick);
          live.high = Math.max(live.high, live.close + 2);
          live.low = Math.min(live.low, live.close - 2);
        }
      }

      priceToY(price, minP, maxP, canvasHeight) {
        const range = maxP - minP || 1;
        const norm = (price - minP) / range;
        const topY = canvasHeight * this.yMinPct;
        const zoneHeight = canvasHeight * (this.yMaxPct - this.yMinPct);
        return topY + (1 - norm) * zoneHeight;
      }

      draw(ctx, canvasWidth, canvasHeight, scanX, scanActive, pX, pY, pActive) {
        if (this.candles.length === 0) return;

        let minP = Infinity;
        let maxP = -Infinity;
        for (let i = 0; i < this.candles.length; i++) {
          const c = this.candles[i];
          if (c.low < minP) minP = c.low;
          if (c.high > maxP) maxP = c.high;
        }
        minP -= this.volatility * 0.6;
        maxP += this.volatility * 0.6;

        // 1. Anchored VWAP Ribbon with Dynamic ±2σ Exhaustion Cloud
        if (this.hasVWAP && this.candles.length > 4) {
          // Soft glowing cloud fill between +2σ and -2σ
          ctx.beginPath();
          for (let i = 0; i < this.candles.length; i++) {
            const c = this.candles[i];
            const upper = (c.high + c.low + c.close) / 3 + this.volatility * 1.6;
            const y = this.priceToY(upper, minP, maxP, canvasHeight);
            if (i === 0) ctx.moveTo(c.x + this.candleWidth / 2, y);
            else ctx.lineTo(c.x + this.candleWidth / 2, y);
          }
          for (let i = this.candles.length - 1; i >= 0; i--) {
            const c = this.candles[i];
            const lower = (c.high + c.low + c.close) / 3 - this.volatility * 1.6;
            const y = this.priceToY(lower, minP, maxP, canvasHeight);
            ctx.lineTo(c.x + this.candleWidth / 2, y);
          }
          ctx.closePath();
          ctx.fillStyle = 'rgba(56, 189, 248, 0.025)';
          ctx.fill();

          // Central Anchored VWAP Spline (Glowing Cyan)
          ctx.lineWidth = 1.8;
          ctx.strokeStyle = 'rgba(56, 189, 248, 0.45)';
          ctx.beginPath();
          for (let i = 0; i < this.candles.length; i++) {
            const c = this.candles[i];
            const typical = (c.high + c.low + c.close) / 3;
            const y = this.priceToY(typical, minP, maxP, canvasHeight);
            if (i === 0) ctx.moveTo(c.x + this.candleWidth / 2, y);
            else ctx.lineTo(c.x + this.candleWidth / 2, y);
          }
          ctx.stroke();

          // Upper +2σ Exhaustion Band (Crimson Resistance)
          ctx.lineWidth = 1.1;
          ctx.setLineDash([3, 4]);
          ctx.strokeStyle = 'rgba(239, 68, 68, 0.35)';
          ctx.beginPath();
          for (let i = 0; i < this.candles.length; i++) {
            const c = this.candles[i];
            const upper = (c.high + c.low + c.close) / 3 + this.volatility * 1.6;
            const y = this.priceToY(upper, minP, maxP, canvasHeight);
            if (i === 0) ctx.moveTo(c.x + this.candleWidth / 2, y);
            else ctx.lineTo(c.x + this.candleWidth / 2, y);
          }
          ctx.stroke();

          // Lower -2σ Exhaustion Band (Emerald Demand)
          ctx.strokeStyle = 'rgba(16, 185, 129, 0.35)';
          ctx.beginPath();
          for (let i = 0; i < this.candles.length; i++) {
            const c = this.candles[i];
            const lower = (c.high + c.low + c.close) / 3 - this.volatility * 1.6;
            const y = this.priceToY(lower, minP, maxP, canvasHeight);
            if (i === 0) ctx.moveTo(c.x + this.candleWidth / 2, y);
            else ctx.lineTo(c.x + this.candleWidth / 2, y);
          }
          ctx.stroke();
          ctx.setLineDash([]);
        }

        // 2. Rising Translucent Volume Columns (Macro Lower Stream)
        if (this.hasVolume) {
          const maxVolHeight = canvasHeight * 0.09;
          const baseY = canvasHeight * this.yMaxPct;
          for (let i = 0; i < this.candles.length; i++) {
            const c = this.candles[i];
            if (c.x < -20 || c.x > canvasWidth + 20) continue;
            const barH = (c.volume / 160) * maxVolHeight;
            const vY = baseY - barH;
            ctx.fillStyle = c.isBullish ? 'rgba(16, 185, 129, 0.18)' : 'rgba(239, 68, 68, 0.18)';
            ctx.fillRect(c.x, vY, this.candleWidth, barH);
          }
        }

        // 3. AI Neural Synapse Constellation (Draws connecting lines between pivot highs/lows)
        if (this.hasNeuralNodes && this.candles.length > 8) {
          const pivots = [];
          for (let i = 2; i < this.candles.length - 2; i += 3) {
            const c = this.candles[i];
            if (c.x > 0 && c.x < canvasWidth) {
              const py = this.priceToY(c.isBullish ? c.high : c.low, minP, maxP, canvasHeight);
              pivots.push({ x: c.x + this.candleWidth / 2, y: py, isBullish: c.isBullish });
            }
          }

          if (pivots.length > 2) {
            ctx.lineWidth = 1;
            ctx.strokeStyle = 'rgba(139, 92, 246, 0.20)';
            ctx.setLineDash([2, 4]);
            ctx.beginPath();
            ctx.moveTo(pivots[0].x, pivots[0].y);
            for (let p = 1; p < pivots.length; p++) {
              ctx.lineTo(pivots[p].x, pivots[p].y);
            }
            ctx.stroke();
            ctx.setLineDash([]);

            // Pulse glowing neural nodes at pivot junctions
            for (let p = 0; p < pivots.length; p++) {
              const pt = pivots[p];
              ctx.fillStyle = pt.isBullish ? 'rgba(56, 189, 248, 0.65)' : 'rgba(244, 63, 94, 0.65)';
              ctx.beginPath();
              ctx.arc(pt.x, pt.y, 2.2, 0, Math.PI * 2);
              ctx.fill();
            }
          }
        }

        // 4. Draw Candlesticks (Moving Red & Green Bars with High/Low Wicks)
        for (let i = 0; i < this.candles.length; i++) {
          const c = this.candles[i];
          if (c.x < -20 || c.x > canvasWidth + 20) continue;

          const openY = this.priceToY(c.open, minP, maxP, canvasHeight);
          const closeY = this.priceToY(c.close, minP, maxP, canvasHeight);
          const highY = this.priceToY(c.high, minP, maxP, canvasHeight);
          const lowY = this.priceToY(c.low, minP, maxP, canvasHeight);

          const bodyTop = Math.min(openY, closeY);
          const bodyHeight = Math.max(Math.abs(closeY - openY), 4.0);
          const centerX = c.x + this.candleWidth / 2;

          // Illumination when hit by AI laser beam
          const distToScan = Math.abs(c.x - scanX);
          const isScanned = scanActive && distToScan < 95;
          const scanGlow = isScanned ? (1 - distToScan / 95) : 0;

          // Interactive touch/pointer proximity glow
          let pointerGlow = 0;
          if (pActive) {
            const distToPointer = Math.hypot(centerX - pX, (bodyTop + bodyHeight / 2) - pY);
            if (distToPointer < pointerRadius) {
              pointerGlow = (1 - distToPointer / pointerRadius) * 0.45;
            }
          }

          const totalGlow = Math.min(scanGlow + pointerGlow, 1.0);

          if (c.isBullish) {
            // Emerald Bullish
            const alphaFill = (0.24 + totalGlow * 0.55) * this.alphaMod;
            const alphaStroke = (0.60 + totalGlow * 0.40) * this.alphaMod;

            ctx.strokeStyle = `rgba(16, 185, 129, ${alphaStroke})`;
            ctx.fillStyle = `rgba(16, 185, 129, ${alphaFill})`;

            ctx.lineWidth = 2.0;
            ctx.beginPath();
            ctx.moveTo(centerX, highY);
            ctx.lineTo(centerX, lowY);
            ctx.stroke();

            ctx.fillRect(c.x, bodyTop, this.candleWidth, bodyHeight);
            ctx.strokeRect(c.x, bodyTop, this.candleWidth, bodyHeight);
          } else {
            // Crimson Bearish
            const alphaFill = (0.22 + totalGlow * 0.55) * this.alphaMod;
            const alphaStroke = (0.55 + totalGlow * 0.40) * this.alphaMod;

            ctx.strokeStyle = `rgba(239, 68, 68, ${alphaStroke})`;
            ctx.fillStyle = `rgba(239, 68, 68, ${alphaFill})`;

            ctx.lineWidth = 2.0;
            ctx.beginPath();
            ctx.moveTo(centerX, highY);
            ctx.lineTo(centerX, lowY);
            ctx.stroke();

            ctx.fillRect(c.x, bodyTop, this.candleWidth, bodyHeight);
            ctx.strokeRect(c.x, bodyTop, this.candleWidth, bodyHeight);
          }
        }
      }
    }

    // Configure 3 complementary institutional tracks with enlarged, prominent candles
    const streams = [
      // Track 1: Upper High-Speed Scalp Stream (kinetic, enlarged 12px)
      new CandleStream({
        name: 'scalp',
        yMinPct: 0.05,
        yMaxPct: 0.32,
        candleWidth: 12,
        candleSpacing: 16,
        speed: 28,
        basePrice: 25440,
        volatility: 16,
        alphaMod: 0.90
      }),
      // Track 2: Center Institutional Anchor Engine (VWAP ±2σ Bands + AI Neural Constellation, enlarged 18px)
      new CandleStream({
        name: 'institutional',
        yMinPct: 0.28,
        yMaxPct: 0.72,
        candleWidth: 18,
        candleSpacing: 25,
        speed: 18,
        basePrice: 25370,
        volatility: 24,
        hasVWAP: true,
        hasNeuralNodes: true,
        alphaMod: 1.20
      }),
      // Track 3: Lower Macro Liquidity & Depth Stream (volume pillars, macro width 26px)
      new CandleStream({
        name: 'macro',
        yMinPct: 0.64,
        yMaxPct: 0.94,
        candleWidth: 26,
        candleSpacing: 36,
        speed: 11,
        basePrice: 25310,
        volatility: 32,
        hasVolume: true,
        alphaMod: 0.80
      })
    ];

    function handleResize() {
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      width = window.innerWidth;
      height = window.innerHeight;

      canvas.width = Math.floor(width * dpr);
      canvas.height = Math.floor(height * dpr);
      ctx.scale(dpr, dpr);

      streams.forEach(s => s.init(width));
    }

    window.addEventListener('resize', handleResize, { passive: true });
    handleResize();

    // Available AI Confluence Badges
    const badgeBank = [
      '🟢 VWAP ±2σ REVERSAL (98.4%)',
      '⚡ INSTITUTIONAL TRAP MITIGATED',
      '🎯 HIGH-PROBABILITY ORDER BLOCK',
      '🛡️ RETAIL EXHAUSTION SWEPT',
      '🤖 AI STRATEGY CONFLUENCE',
      '⚡ SMART MONEY ACCUMULATION'
    ];

    // Pointer Interaction Listeners (Desktop & Mobile Touch)
    function onPointerMove(e) {
      pointerActive = true;
      if (e.touches && e.touches.length > 0) {
        pointerX = e.touches[0].clientX;
        pointerY = e.touches[0].clientY;
      } else {
        pointerX = e.clientX;
        pointerY = e.clientY;
      }

      // Spawn subtle quantum sparkles
      if (Math.random() > 0.4 && pointerParticles.length < 35) {
        pointerParticles.push({
          x: pointerX + (Math.random() - 0.5) * 20,
          y: pointerY + (Math.random() - 0.5) * 20,
          vx: (Math.random() - 0.5) * 1.5,
          vy: (Math.random() - 0.5) * 1.5 - 0.5,
          life: 1.0,
          color: Math.random() > 0.5 ? '#38bdf8' : '#a855f7'
        });
      }
    }

    function onPointerLeave() {
      pointerActive = false;
      pointerX = -9999;
      pointerY = -9999;
    }

    window.addEventListener('mousemove', onPointerMove, { passive: true });
    window.addEventListener('touchmove', onPointerMove, { passive: true });
    window.addEventListener('mouseleave', onPointerLeave, { passive: true });
    window.addEventListener('touchend', onPointerLeave, { passive: true });

    /**
     * Master Render Loop (60 FPS)
     */
    function render(now) {
      if (!isTabVisible) return;

      const dt = Math.min((now - lastTime) / 1000, 0.1);
      lastTime = now;

      // 1. Update all streams
      streams.forEach(s => s.update(dt, width, now));

      // 2. Clear canvas with Deep Obsidian base
      ctx.fillStyle = '#030712';
      ctx.fillRect(0, 0, width, height);

      // 3. Volumetric 3-Point Hypnotic Aurora Nebulae
      auroraTheta1 += 0.0048;
      auroraTheta2 += 0.0036;
      auroraTheta3 += 0.0026;

      // Aurora 1: Azure / Electric Cyan
      const a1X = width * 0.28 + Math.cos(auroraTheta1) * (width * 0.18);
      const a1Y = height * 0.38 + Math.sin(auroraTheta1 * 0.8) * (height * 0.16);
      const a1Rad = Math.min(width, height) * 0.52;
      const grad1 = ctx.createRadialGradient(a1X, a1Y, 15, a1X, a1Y, a1Rad);
      grad1.addColorStop(0, 'rgba(56, 189, 248, 0.11)');
      grad1.addColorStop(0.5, 'rgba(37, 99, 235, 0.04)');
      grad1.addColorStop(1, 'rgba(3, 7, 18, 0)');
      ctx.fillStyle = grad1;
      ctx.fillRect(0, 0, width, height);

      // Aurora 2: Institutional Emerald Edge
      const a2X = width * 0.72 + Math.sin(auroraTheta2) * (width * 0.20);
      const a2Y = height * 0.52 + Math.cos(auroraTheta2 * 0.7) * (height * 0.18);
      const a2Rad = Math.min(width, height) * 0.50;
      const grad2 = ctx.createRadialGradient(a2X, a2Y, 15, a2X, a2Y, a2Rad);
      grad2.addColorStop(0, 'rgba(16, 185, 129, 0.10)');
      grad2.addColorStop(0.5, 'rgba(5, 150, 105, 0.03)');
      grad2.addColorStop(1, 'rgba(3, 7, 18, 0)');
      ctx.fillStyle = grad2;
      ctx.fillRect(0, 0, width, height);

      // Aurora 3: Deep Quant Violet
      const a3X = width * 0.50 + Math.cos(auroraTheta3 * 0.9) * (width * 0.22);
      const a3Y = height * 0.78 + Math.sin(auroraTheta3) * (height * 0.14);
      const a3Rad = Math.min(width, height) * 0.44;
      const grad3 = ctx.createRadialGradient(a3X, a3Y, 15, a3X, a3Y, a3Rad);
      grad3.addColorStop(0, 'rgba(139, 92, 246, 0.08)');
      grad3.addColorStop(1, 'rgba(3, 7, 18, 0)');
      ctx.fillStyle = grad3;
      ctx.fillRect(0, 0, width, height);

      // 4. Interactive Pointer / Touch Quantum Gravity Well
      if (pointerActive && pointerX > 0 && pointerY > 0) {
        const pGrad = ctx.createRadialGradient(pointerX, pointerY, 5, pointerX, pointerY, pointerRadius);
        pGrad.addColorStop(0, 'rgba(56, 189, 248, 0.16)');
        pGrad.addColorStop(0.6, 'rgba(139, 92, 246, 0.06)');
        pGrad.addColorStop(1, 'rgba(3, 7, 18, 0)');
        ctx.fillStyle = pGrad;
        ctx.beginPath();
        ctx.arc(pointerX, pointerY, pointerRadius, 0, Math.PI * 2);
        ctx.fill();
      }

      // 5. Subtle Cybernetic Cross-Hatch Grid Matrix & Price Guides
      ctx.lineWidth = 1;
      ctx.setLineDash([3, 6]);
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.025)';
      ctx.fillStyle = 'rgba(148, 163, 184, 0.22)';
      ctx.font = '10px monospace';
      const hLines = [0.15, 0.35, 0.55, 0.75, 0.90];
      const priceLabels = ['₹25,480', '₹25,420', '₹25,370 (VWAP)', '₹25,320', '₹25,260'];
      for (let i = 0; i < hLines.length; i++) {
        const y = height * hLines[i];
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
        ctx.stroke();

        if (width > 600) {
          ctx.fillText(priceLabels[i] || '', width - 95, y - 4);
        }
      }
      ctx.setLineDash([]);

      // 6. Update AI Neural Scanner
      if (!scanActive && now > nextScanTime) {
        scanActive = true;
        scanProgress = 0;
        activeCallouts = [];

        // Sample 2 prominent candles from the center institutional stream
        const centerStream = streams[1];
        const inView = centerStream.candles.filter(c => c.x > width * 0.18 && c.x < width * 0.82);
        if (inView.length >= 2) {
          const idx1 = Math.floor(inView.length * 0.28);
          const idx2 = Math.floor(inView.length * 0.72);
          const c1 = inView[idx1];
          const c2 = inView[idx2];
          const b1 = badgeBank[Math.floor(Math.random() * badgeBank.length)];
          let b2 = badgeBank[Math.floor(Math.random() * badgeBank.length)];
          while (b2 === b1) b2 = badgeBank[Math.floor(Math.random() * badgeBank.length)];

          if (c1) activeCallouts.push({ candle: c1, stream: centerStream, label: b1 });
          if (c2) activeCallouts.push({ candle: c2, stream: centerStream, label: b2 });
        }
      }

      let scanX = -130;
      if (scanActive) {
        scanProgress += dt * 0.25; // Smooth ~4s sweep
        scanX = scanProgress * (width + 260) - 130;

        // Emit scanner trail sparkles
        if (Math.random() > 0.35 && scanSparkles.length < 40) {
          scanSparkles.push({
            x: scanX + (Math.random() - 0.5) * 40,
            y: Math.random() * height,
            life: 1.0,
            size: Math.random() * 2 + 1,
            color: Math.random() > 0.5 ? '#38bdf8' : '#10b981'
          });
        }

        if (scanProgress >= 1) {
          scanActive = false;
          nextScanTime = now + scanCooldown;
          activeCallouts = [];
        }
      }

      // 7. Draw all 3 streams (Back to Front: Macro -> Scalp -> Institutional)
      streams[2].draw(ctx, width, height, scanX, scanActive, pointerX, pointerY, pointerActive); // Macro Liquidity
      streams[0].draw(ctx, width, height, scanX, scanActive, pointerX, pointerY, pointerActive); // Upper Scalp
      streams[1].draw(ctx, width, height, scanX, scanActive, pointerX, pointerY, pointerActive); // Center Institutional

      // 8. Render AI Dual-Photon Beam & High-Tech HUD Badges
      if (scanActive) {
        // Dual-pass photon laser aura
        const beamGrad = ctx.createLinearGradient(scanX - 70, 0, scanX + 70, 0);
        beamGrad.addColorStop(0, 'rgba(56, 189, 248, 0)');
        beamGrad.addColorStop(0.48, 'rgba(56, 189, 248, 0.26)');
        beamGrad.addColorStop(0.52, 'rgba(16, 185, 129, 0.26)');
        beamGrad.addColorStop(1, 'rgba(16, 185, 129, 0)');
        ctx.fillStyle = beamGrad;
        ctx.fillRect(scanX - 75, 0, 150, height);

        // Core sharp laser line
        ctx.lineWidth = 1.8;
        ctx.strokeStyle = 'rgba(56, 189, 248, 0.85)';
        ctx.beginPath();
        ctx.moveTo(scanX, 0);
        ctx.lineTo(scanX, height);
        ctx.stroke();

        // Top & bottom laser emitters
        ctx.fillStyle = '#38bdf8';
        ctx.shadowColor = '#38bdf8';
        ctx.shadowBlur = 12;
        ctx.beginPath();
        ctx.arc(scanX, 18, 3.5, 0, Math.PI * 2);
        ctx.arc(scanX, height - 18, 3.5, 0, Math.PI * 2);
        ctx.fill();
        ctx.shadowBlur = 0;

        // Render Callout Badges
        for (let p = 0; p < activeCallouts.length; p++) {
          const item = activeCallouts[p];
          if (scanX > item.candle.x - 25) {
            const px = item.candle.x + item.stream.candleWidth / 2;
            const py = height * 0.32 + p * 34;

            ctx.save();
            ctx.font = '600 11px Inter, -apple-system, BlinkMacSystemFont, sans-serif';
            const textWidth = ctx.measureText(item.label).width;

            // Translucent glowing badge pill with glass border
            ctx.fillStyle = 'rgba(10, 15, 30, 0.94)';
            ctx.strokeStyle = 'rgba(56, 189, 248, 0.70)';
            ctx.lineWidth = 1;
            ctx.beginPath();
            if (ctx.roundRect) {
              ctx.roundRect(px - textWidth / 2 - 8, py - 13, textWidth + 16, 23, 6);
            } else {
              ctx.rect(px - textWidth / 2 - 8, py - 13, textWidth + 16, 23);
            }
            ctx.fill();
            ctx.stroke();

            // Label text with slight cyan luminescence
            ctx.fillStyle = '#7dd3fc';
            ctx.fillText(item.label, px - textWidth / 2, py + 2.5);

            // Subtle tether line to candle
            ctx.strokeStyle = 'rgba(56, 189, 248, 0.50)';
            ctx.setLineDash([2, 3]);
            ctx.beginPath();
            ctx.moveTo(px, py + 10);
            ctx.lineTo(px, height * 0.50);
            ctx.stroke();
            ctx.setLineDash([]);
            ctx.restore();
          }
        }
      }

      // 9. Update & Draw Scanner Sparkles
      for (let i = scanSparkles.length - 1; i >= 0; i--) {
        const sp = scanSparkles[i];
        sp.life -= dt * 0.8;
        if (sp.life <= 0) {
          scanSparkles.splice(i, 1);
          continue;
        }
        ctx.fillStyle = sp.color;
        ctx.globalAlpha = sp.life * 0.7;
        ctx.beginPath();
        ctx.arc(sp.x, sp.y, sp.size, 0, Math.PI * 2);
        ctx.fill();
        ctx.globalAlpha = 1.0;
      }

      // 10. Update & Draw Pointer Interactive Sparkles
      for (let i = pointerParticles.length - 1; i >= 0; i--) {
        const pp = pointerParticles[i];
        pp.x += pp.vx;
        pp.y += pp.vy;
        pp.life -= dt * 1.2;
        if (pp.life <= 0) {
          pointerParticles.splice(i, 1);
          continue;
        }
        ctx.fillStyle = pp.color;
        ctx.globalAlpha = pp.life * 0.8;
        ctx.beginPath();
        ctx.arc(pp.x, pp.y, 2.5 * pp.life, 0, Math.PI * 2);
        ctx.fill();
        ctx.globalAlpha = 1.0;
      }

      animationFrameId = requestAnimationFrame(render);
    }

    // Auto-pause when tab is hidden to save GPU/CPU & battery
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

    animationFrameId = requestAnimationFrame(render);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initCandlestickAIBackground);
  } else {
    initCandlestickAIBackground();
  }
})();
