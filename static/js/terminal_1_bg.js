/**
 * YourTradeBot — Terminal 1 Institutional Candlestick & AI Background
 * 
 * Multi-Depth Dynamic Financial Matrix:
 * - 3 Concurrent Candlestick Streams with Parallax Depth (Upper Scalp, Center Institutional VWAP, Lower Macro Liquidity)
 * - Volumetric Volume Bars rising along the lower liquidity zone
 * - Multi-band Anchored VWAP with ±2σ exhaustion cloud
 * - Periodic AI Neural Scan Waves with dynamic confluence callout badges
 * - Hypnotic 3-point Volumetric Aurora Breathing (Azure, Emerald, Violet)
 * - 60 FPS GPU-accelerated Canvas with auto-pause on hidden tab
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

    // AI Neural Scanner State
    let scanActive = false;
    let scanProgress = 0;
    let nextScanTime = performance.now() + 3000;
    const scanCooldown = 8500;
    let activeCallouts = [];

    // Aurora glow oscillation angles
    let auroraTheta1 = 0;
    let auroraTheta2 = Math.PI * 0.6;
    let auroraTheta3 = Math.PI * 1.3;

    /**
     * Candlestick Stream definition
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
        this.volatility = config.volatility || 10;
        this.hasVWAP = !!config.hasVWAP;
        this.hasVolume = !!config.hasVolume;
        this.alphaMod = config.alphaMod || 1.0;

        this.candles = [];
        this.currentTrend = 1;
        this.trendCountdown = 20;
      }

      generateCandle(prevClose, index) {
        if (--this.trendCountdown <= 0) {
          this.currentTrend = Math.random() > 0.48 ? 1 : -1;
          this.trendCountdown = Math.floor(12 + Math.random() * 26);
        }

        const drift = this.currentTrend * (Math.random() * (this.volatility * 0.6) + 1.5);
        const meanReversion = (this.basePrice - prevClose) * 0.018;
        const change = drift + meanReversion + (Math.random() - 0.5) * this.volatility;

        const open = prevClose;
        const close = open + change;
        const wickSpread = Math.random() * (this.volatility * 0.7) + 1.2;
        const high = Math.max(open, close) + wickSpread;
        const low = Math.min(open, close) - wickSpread;
        const volume = Math.floor(20 + Math.random() * 80 + (Math.abs(change) / this.volatility) * 50);

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
        const count = Math.ceil(canvasWidth / step) + 20;
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

        // Shift left
        for (let i = 0; i < this.candles.length; i++) {
          this.candles[i].x -= shift;
        }

        // Evict off-screen candles
        while (this.candles.length > 0 && this.candles[0].x < -(this.candleWidth + 15)) {
          this.candles.shift();
        }

        // Spawn new candles on right
        const last = this.candles[this.candles.length - 1];
        if (last && last.x < canvasWidth + 120) {
          const newC = this.generateCandle(last.close, 0);
          newC.x = last.x + step;
          this.candles.push(newC);
        }

        // Dynamic tick pulse on the active live candle
        if (this.candles.length > 0) {
          const live = this.candles[this.candles.length - 1];
          const tick = Math.sin(now * 0.007 + (this.hasVWAP ? 1 : 2)) * (this.volatility * 0.15);
          live.close = live.open + (live.isBullish ? 3 + tick : -3 - tick);
          live.high = Math.max(live.high, live.close + 1.5);
          live.low = Math.min(live.low, live.close - 1.5);
        }
      }

      priceToY(price, minP, maxP, canvasHeight) {
        const range = maxP - minP || 1;
        const norm = (price - minP) / range;
        const topY = canvasHeight * this.yMinPct;
        const zoneHeight = canvasHeight * (this.yMaxPct - this.yMinPct);
        return topY + (1 - norm) * zoneHeight;
      }

      draw(ctx, canvasWidth, canvasHeight, scanX, scanActive) {
        if (this.candles.length === 0) return;

        // Calculate price extremes for this stream
        let minP = Infinity;
        let maxP = -Infinity;
        for (let i = 0; i < this.candles.length; i++) {
          const c = this.candles[i];
          if (c.low < minP) minP = c.low;
          if (c.high > maxP) maxP = c.high;
        }
        minP -= this.volatility * 0.5;
        maxP += this.volatility * 0.5;

        // 1. Anchored VWAP Ribbon & Exhaustion Bands (Center Stream)
        if (this.hasVWAP && this.candles.length > 4) {
          // Central VWAP line
          ctx.lineWidth = 1.6;
          ctx.strokeStyle = 'rgba(56, 189, 248, 0.40)';
          ctx.beginPath();
          for (let i = 0; i < this.candles.length; i++) {
            const c = this.candles[i];
            const typical = (c.high + c.low + c.close) / 3;
            const y = this.priceToY(typical, minP, maxP, canvasHeight);
            if (i === 0) ctx.moveTo(c.x + this.candleWidth / 2, y);
            else ctx.lineTo(c.x + this.candleWidth / 2, y);
          }
          ctx.stroke();

          // Upper +2σ Band
          ctx.lineWidth = 1;
          ctx.setLineDash([3, 4]);
          ctx.strokeStyle = 'rgba(239, 68, 68, 0.30)';
          ctx.beginPath();
          for (let i = 0; i < this.candles.length; i++) {
            const c = this.candles[i];
            const upper = (c.high + c.low + c.close) / 3 + this.volatility * 1.6;
            const y = this.priceToY(upper, minP, maxP, canvasHeight);
            if (i === 0) ctx.moveTo(c.x + this.candleWidth / 2, y);
            else ctx.lineTo(c.x + this.candleWidth / 2, y);
          }
          ctx.stroke();

          // Lower -2σ Band
          ctx.strokeStyle = 'rgba(16, 185, 129, 0.30)';
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

        // 2. Volume Pillars (Lower Stream)
        if (this.hasVolume) {
          const maxVolHeight = canvasHeight * 0.08;
          const baseY = canvasHeight * this.yMaxPct;
          for (let i = 0; i < this.candles.length; i++) {
            const c = this.candles[i];
            if (c.x < -20 || c.x > canvasWidth + 20) continue;
            const barH = (c.volume / 150) * maxVolHeight;
            const vY = baseY - barH;
            ctx.fillStyle = c.isBullish ? 'rgba(16, 185, 129, 0.16)' : 'rgba(239, 68, 68, 0.16)';
            ctx.fillRect(c.x, vY, this.candleWidth, barH);
          }
        }

        // 3. Render Candlesticks
        for (let i = 0; i < this.candles.length; i++) {
          const c = this.candles[i];
          if (c.x < -20 || c.x > canvasWidth + 20) continue;

          const openY = this.priceToY(c.open, minP, maxP, canvasHeight);
          const closeY = this.priceToY(c.close, minP, maxP, canvasHeight);
          const highY = this.priceToY(c.high, minP, maxP, canvasHeight);
          const lowY = this.priceToY(c.low, minP, maxP, canvasHeight);

          const bodyTop = Math.min(openY, closeY);
          const bodyHeight = Math.max(Math.abs(closeY - openY), 2.2);
          const centerX = c.x + this.candleWidth / 2;

          // Illumination when hit by AI laser beam
          const distToScan = Math.abs(c.x - scanX);
          const isScanned = scanActive && distToScan < 80;
          const scanGlow = isScanned ? (1 - distToScan / 80) : 0;

          if (c.isBullish) {
            const alphaFill = (0.20 + scanGlow * 0.50) * this.alphaMod;
            const alphaStroke = (0.50 + scanGlow * 0.50) * this.alphaMod;

            ctx.strokeStyle = `rgba(16, 185, 129, ${alphaStroke})`;
            ctx.fillStyle = `rgba(16, 185, 129, ${alphaFill})`;

            ctx.lineWidth = 1.1;
            ctx.beginPath();
            ctx.moveTo(centerX, highY);
            ctx.lineTo(centerX, lowY);
            ctx.stroke();

            ctx.fillRect(c.x, bodyTop, this.candleWidth, bodyHeight);
            ctx.strokeRect(c.x, bodyTop, this.candleWidth, bodyHeight);
          } else {
            const alphaFill = (0.18 + scanGlow * 0.50) * this.alphaMod;
            const alphaStroke = (0.45 + scanGlow * 0.50) * this.alphaMod;

            ctx.strokeStyle = `rgba(239, 68, 68, ${alphaStroke})`;
            ctx.fillStyle = `rgba(239, 68, 68, ${alphaFill})`;

            ctx.lineWidth = 1.1;
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

    // Configure 3 complementary institutional tracks
    const streams = [
      // Track 1: Upper High-Speed Scalp Stream (kinetic, smaller, fast)
      new CandleStream({
        name: 'scalp',
        yMinPct: 0.05,
        yMaxPct: 0.32,
        candleWidth: 6,
        candleSpacing: 9,
        speed: 32,
        basePrice: 25420,
        volatility: 9,
        alphaMod: 0.85
      }),
      // Track 2: Center Institutional Anchor Engine (VWAP ±2σ Bands, mid-speed)
      new CandleStream({
        name: 'institutional',
        yMinPct: 0.28,
        yMaxPct: 0.70,
        candleWidth: 10,
        candleSpacing: 15,
        speed: 20,
        basePrice: 25360,
        volatility: 14,
        hasVWAP: true,
        alphaMod: 1.1
      }),
      // Track 3: Lower Macro Liquidity & Depth Stream (volume pillars, macro width, slow parallax)
      new CandleStream({
        name: 'macro',
        yMinPct: 0.65,
        yMaxPct: 0.94,
        candleWidth: 13,
        candleSpacing: 18,
        speed: 13,
        basePrice: 25300,
        volatility: 18,
        hasVolume: true,
        alphaMod: 0.75
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
      '🤖 QUANT MOMENTUM ACCELERATION'
    ];

    /**
     * Master Render Loop
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
      auroraTheta1 += 0.005;
      auroraTheta2 += 0.0038;
      auroraTheta3 += 0.0028;

      // Aurora 1: Azure / Electric Cyan
      const a1X = width * 0.28 + Math.cos(auroraTheta1) * (width * 0.18);
      const a1Y = height * 0.38 + Math.sin(auroraTheta1 * 0.8) * (height * 0.16);
      const a1Rad = Math.min(width, height) * 0.52;
      const grad1 = ctx.createRadialGradient(a1X, a1Y, 15, a1X, a1Y, a1Rad);
      grad1.addColorStop(0, 'rgba(56, 189, 248, 0.10)');
      grad1.addColorStop(0.5, 'rgba(37, 99, 235, 0.04)');
      grad1.addColorStop(1, 'rgba(3, 7, 18, 0)');
      ctx.fillStyle = grad1;
      ctx.fillRect(0, 0, width, height);

      // Aurora 2: Institutional Emerald Edge
      const a2X = width * 0.72 + Math.sin(auroraTheta2) * (width * 0.20);
      const a2Y = height * 0.52 + Math.cos(auroraTheta2 * 0.7) * (height * 0.18);
      const a2Rad = Math.min(width, height) * 0.50;
      const grad2 = ctx.createRadialGradient(a2X, a2Y, 15, a2X, a2Y, a2Rad);
      grad2.addColorStop(0, 'rgba(16, 185, 129, 0.09)');
      grad2.addColorStop(0.5, 'rgba(5, 150, 105, 0.03)');
      grad2.addColorStop(1, 'rgba(3, 7, 18, 0)');
      ctx.fillStyle = grad2;
      ctx.fillRect(0, 0, width, height);

      // Aurora 3: Deep Quant Violet
      const a3X = width * 0.50 + Math.cos(auroraTheta3 * 0.9) * (width * 0.22);
      const a3Y = height * 0.78 + Math.sin(auroraTheta3) * (height * 0.14);
      const a3Rad = Math.min(width, height) * 0.44;
      const grad3 = ctx.createRadialGradient(a3X, a3Y, 15, a3X, a3Y, a3Rad);
      grad3.addColorStop(0, 'rgba(139, 92, 246, 0.07)');
      grad3.addColorStop(1, 'rgba(3, 7, 18, 0)');
      ctx.fillStyle = grad3;
      ctx.fillRect(0, 0, width, height);

      // 4. Subtle Cross-Hatch Grid Matrix & Price Guides
      ctx.lineWidth = 1;
      ctx.setLineDash([3, 6]);
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.025)';
      const hLines = [0.15, 0.35, 0.55, 0.75, 0.90];
      for (let i = 0; i < hLines.length; i++) {
        const y = height * hLines[i];
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
        ctx.stroke();
      }
      ctx.setLineDash([]);

      // 5. Update AI Neural Scanner
      if (!scanActive && now > nextScanTime) {
        scanActive = true;
        scanProgress = 0;
        activeCallouts = [];

        // Sample 2 prominent candles from the center institutional stream
        const centerStream = streams[1];
        const inView = centerStream.candles.filter(c => c.x > width * 0.20 && c.x < width * 0.80);
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

      let scanX = -120;
      if (scanActive) {
        scanProgress += dt * 0.26; // Smooth ~3.8s sweep
        scanX = scanProgress * (width + 240) - 120;

        if (scanProgress >= 1) {
          scanActive = false;
          nextScanTime = now + scanCooldown;
          activeCallouts = [];
        }
      }

      // 6. Draw all 3 streams (Back to Front: Macro -> Scalp -> Institutional)
      streams[2].draw(ctx, width, height, scanX, scanActive); // Macro Liquidity
      streams[0].draw(ctx, width, height, scanX, scanActive); // Upper Scalp
      streams[1].draw(ctx, width, height, scanX, scanActive); // Center Institutional

      // 7. Render AI Photon Beam & High-Tech HUD Badges
      if (scanActive) {
        // Dual-pass laser aura
        const beamGrad = ctx.createLinearGradient(scanX - 65, 0, scanX + 65, 0);
        beamGrad.addColorStop(0, 'rgba(56, 189, 248, 0)');
        beamGrad.addColorStop(0.48, 'rgba(56, 189, 248, 0.24)');
        beamGrad.addColorStop(0.52, 'rgba(16, 185, 129, 0.24)');
        beamGrad.addColorStop(1, 'rgba(16, 185, 129, 0)');
        ctx.fillStyle = beamGrad;
        ctx.fillRect(scanX - 70, 0, 140, height);

        // Core sharp laser line
        ctx.lineWidth = 1.6;
        ctx.strokeStyle = 'rgba(56, 189, 248, 0.75)';
        ctx.beginPath();
        ctx.moveTo(scanX, 0);
        ctx.lineTo(scanX, height);
        ctx.stroke();

        // Laser scan head node at top & bottom
        ctx.fillStyle = '#38bdf8';
        ctx.shadowColor = '#38bdf8';
        ctx.shadowBlur = 10;
        ctx.beginPath();
        ctx.arc(scanX, 20, 3, 0, Math.PI * 2);
        ctx.arc(scanX, height - 20, 3, 0, Math.PI * 2);
        ctx.fill();
        ctx.shadowBlur = 0;

        // Render Callout Badges that have been revealed by the beam
        for (let p = 0; p < activeCallouts.length; p++) {
          const item = activeCallouts[p];
          if (scanX > item.candle.x - 25) {
            const px = item.candle.x + item.stream.candleWidth / 2;
            const py = height * 0.30 + p * 32;

            ctx.save();
            ctx.font = '600 11px Inter, -apple-system, BlinkMacSystemFont, sans-serif';
            const textWidth = ctx.measureText(item.label).width;

            // Translucent glowing badge pill
            ctx.fillStyle = 'rgba(10, 15, 30, 0.92)';
            ctx.strokeStyle = 'rgba(56, 189, 248, 0.65)';
            ctx.lineWidth = 1;
            ctx.beginPath();
            if (ctx.roundRect) {
              ctx.roundRect(px - textWidth / 2 - 8, py - 13, textWidth + 16, 22, 5);
            } else {
              ctx.rect(px - textWidth / 2 - 8, py - 13, textWidth + 16, 22);
            }
            ctx.fill();
            ctx.stroke();

            // Label text with slight cyan luminescence
            ctx.fillStyle = '#7dd3fc';
            ctx.fillText(item.label, px - textWidth / 2, py + 2);

            // Subtle tether line to candle
            ctx.strokeStyle = 'rgba(56, 189, 248, 0.45)';
            ctx.setLineDash([2, 3]);
            ctx.beginPath();
            ctx.moveTo(px, py + 9);
            ctx.lineTo(px, height * 0.48);
            ctx.stroke();
            ctx.setLineDash([]);
            ctx.restore();
          }
        }
      }

      animationFrameId = requestAnimationFrame(render);
    }

    // Tab visibility handling
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
