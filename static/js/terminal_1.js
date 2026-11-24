/**
 * YourTradeBot — Terminal 1 Master Interactive Script
 * Handles Interactive Gallery, Auth Modal, Visitor Funnel Analytics, and Contact Form
 */

(function () {
  'use strict';

  // --- 1. Visitor ID & Funnel Tracking Helper ---
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

  // --- 2. Check for Returning Authenticated User ---
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
            navLoginBtn.textContent = '👑 My Terminal';
            navLoginBtn.onclick = () => { window.location.href = '/terminal'; };
          }
        }
      }
    } catch (e) {}
  }

  // --- 3. Interactive Screenshot Showcase Data & Engine ---
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
      imgEl.style.opacity = '0.5';
      setTimeout(() => {
        imgEl.src = s.img;
        imgEl.style.opacity = '1';
      }, 150);
    }
    if (badgeEl) badgeEl.textContent = s.badge;
    if (titleEl) titleEl.textContent = s.title;
    if (descEl) descEl.textContent = s.desc;

    // Update active tab buttons
    const tabs = document.querySelectorAll('.gallery-tab');
    tabs.forEach((tab, idx) => {
      if (idx === index) {
        tab.classList.add('active');
      } else {
        tab.classList.remove('active');
      }
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

  // --- 4. Lightbox Zoom ---
  window.openLightbox = function () {
    const s = screenshots[currentSlideIndex];
    const modal = document.getElementById('lightbox-modal');
    const img = document.getElementById('lightbox-img');
    if (modal && img) {
      img.src = s.img;
      modal.style.display = 'flex';
    }
  };

  window.closeLightbox = function () {
    const modal = document.getElementById('lightbox-modal');
    if (modal) modal.style.display = 'none';
  };

  // --- 5. Navigation Actions ---
  window.launchGuestMode = function () {
    trackFunnelAction('funnel_try_guest_click', 'Clicked Try for Free Without Registration');
    window.location.href = '/terminal?mode=guest';
  };

  window.selectScreenshot = function (index) {
    stopSlideAutoTimer();
    loadSlide(index);
    startSlideAutoTimer();
  };

  // --- 6. Auth Modal Logic ---
  window.openAuthModal = function (tab) {
    const overlay = document.getElementById('auth-modal');
    if (overlay) {
      overlay.style.display = 'flex';
      switchAuthTab(tab || 'login');
    }
    trackFunnelAction('funnel_direct_login_click', 'Opened Auth Modal (' + tab + ')');
  };

  window.closeAuthModal = function () {
    const overlay = document.getElementById('auth-modal');
    if (overlay) overlay.style.display = 'none';
  };

  window.switchAuthTab = function (tab) {
    const tabLogin = document.getElementById('tab-btn-login');
    const tabRegister = document.getElementById('tab-btn-register');
    const formLogin = document.getElementById('form-login');
    const formRegister = document.getElementById('form-register');
    const msgBox = document.getElementById('auth-msg');

    if (msgBox) {
      msgBox.className = 'auth-msg';
      msgBox.style.display = 'none';
    }

    if (tab === 'register') {
      tabRegister.classList.add('active');
      tabLogin.classList.remove('active');
      formRegister.style.display = 'flex';
      formLogin.style.display = 'none';
    } else {
      tabLogin.classList.add('active');
      tabRegister.classList.remove('active');
      formLogin.style.display = 'flex';
      formRegister.style.display = 'none';
    }
  };

  // Login Submit Handler
  window.submitLogin = async function (e) {
    e.preventDefault();
    const ident = document.getElementById('login-ident').value.trim();
    const pwd = document.getElementById('login-pwd').value.trim();
    const msgBox = document.getElementById('auth-msg');
    const btn = document.getElementById('btn-submit-login');

    if (!ident || !pwd) {
      showAuthMsg('Please enter both username/email and password.', 'error');
      return;
    }

    btn.disabled = true;
    btn.textContent = 'Verifying...';

    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ identifier: ident, username: ident, password: pwd })
      });
      const data = await res.json();
      if (res.ok && data.token) {
        localStorage.setItem('auth_token', data.token);
        trackFunnelAction('funnel_direct_login_success', 'Logged in directly from Terminal 1');
        showAuthMsg('Login successful! Redirecting to Live Terminal...', 'success');
        setTimeout(() => {
          window.location.href = '/terminal';
        }, 800);
      } else {
        showAuthMsg(data.message || data.error || 'Login failed. Please check credentials.', 'error');
        btn.disabled = false;
        btn.textContent = 'Sign In to Terminal';
      }
    } catch (err) {
      showAuthMsg('Network error occurred. Please try again.', 'error');
      btn.disabled = false;
      btn.textContent = 'Sign In to Terminal';
    }
  };

  // Register Submit Handler
  window.submitRegister = async function (e) {
    e.preventDefault();
    const uname = document.getElementById('reg-uname').value.trim();
    const email = document.getElementById('reg-email').value.trim();
    const phone = document.getElementById('reg-phone').value.trim();
    const pwd = document.getElementById('reg-pwd').value.trim();
    const style = document.getElementById('reg-style').value;
    const btn = document.getElementById('btn-submit-register');

    if (!uname || !email || !pwd) {
      showAuthMsg('Please complete all required fields.', 'error');
      return;
    }

    const policyEl = document.getElementById('reg-policy');
    if (policyEl && !policyEl.checked) {
      showAuthMsg('Please accept the Terms of Service & Privacy Policy to register.', 'error');
      return;
    }

    btn.disabled = true;
    btn.textContent = 'Creating Account...';

    try {
      const res = await fetch('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: uname,
          email: email,
          phone: phone || '',
          password: pwd,
          trading_style: style || 'intraday_scalper',
          accepted_policy: true
        })
      });
      const data = await res.json();
      if (res.ok && data.token) {
        localStorage.setItem('auth_token', data.token);
        trackFunnelAction('funnel_direct_register_success', 'Created account directly from Terminal 1');
        showAuthMsg('Account created successfully! Launching Live Terminal...', 'success');
        setTimeout(() => {
          window.location.href = '/terminal';
        }, 900);
      } else {
        showAuthMsg(data.message || data.error || 'Registration failed. Username or email may already be in use.', 'error');
        btn.disabled = false;
        btn.textContent = 'Create 100% Free Account';
      }
    } catch (err) {
      showAuthMsg('Network error occurred. Please try again.', 'error');
      btn.disabled = false;
      btn.textContent = 'Create 100% Free Account';
    }
  };

  function showAuthMsg(msg, type) {
    const box = document.getElementById('auth-msg');
    if (!box) return;
    box.textContent = msg;
    box.className = 'auth-msg ' + (type === 'success' ? 'success' : 'error');
    box.style.display = 'block';
  }

  // --- 7. Feedback / Contact Form ---
  window.submitContactForm = async function (e) {
    e.preventDefault();
    const name = document.getElementById('contact-name').value.trim();
    const email = document.getElementById('contact-email').value.trim();
    const msg = document.getElementById('contact-msg').value.trim();
    const btn = document.getElementById('btn-contact-submit');

    if (!msg) return;

    btn.disabled = true;
    btn.textContent = 'Sending...';

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
        btn.textContent = '✓ Message Sent!';
        btn.style.background = '#10b981';
        document.getElementById('contact-form').reset();
        setTimeout(() => {
          btn.disabled = false;
          btn.textContent = 'Send Message to Developer';
          btn.style.background = '';
        }, 4000);
      } else {
        btn.disabled = false;
        btn.textContent = 'Send Failed. Try Again';
      }
    } catch (err) {
      btn.disabled = false;
      btn.textContent = 'Send Failed. Try Again';
    }
  };

  // Close modals when clicking outside
  document.addEventListener('click', (e) => {
    const authModal = document.getElementById('auth-modal');
    if (authModal && e.target === authModal) {
      closeAuthModal();
    }
    const lbModal = document.getElementById('lightbox-modal');
    if (lbModal && e.target === lbModal) {
      closeLightbox();
    }
  });

  // --- Initialize on DOM Load ---
  document.addEventListener('DOMContentLoaded', () => {
    recordInitialVisit();
    checkReturningUser();
    loadSlide(0);
    startSlideAutoTimer();

    // Pause slideshow on hover
    const frame = document.querySelector('.window-frame');
    if (frame) {
      frame.addEventListener('mouseenter', stopSlideAutoTimer);
      frame.addEventListener('mouseleave', startSlideAutoTimer);
    }
  });

})();
