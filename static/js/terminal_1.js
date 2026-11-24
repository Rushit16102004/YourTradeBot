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
      img: '/static/images/screenshots/shot6_signals.png',
      badge: 'Algorithmic Alpha',
      title: 'Quantitative Buy & Sell Signal Engine',
      desc: 'Transparent real-time trade execution signals with clean entry markers on chart. Powered by multi-factor confluence, session VWAP boundaries, and institutional volume absorption.',
      tag: 'Signals'
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

  // --- 6. Auth Modal Logic (Matching Live Terminal Guest Mode) ---
  let usernameCheckTimer = null;
  let isUsernameAvailable = false;
  let phoneCheckTimer = null;
  let isPhoneAvailable = null;
  let selectedCountryCode = '+91';
  let selectedCountryFlag = '🇮🇳';

  const countryCodeData = [
    { code: '+91', flag: '🇮🇳', name: 'India' },
    { code: '+1', flag: '🇺🇸', name: 'United States' },
    { code: '+1', flag: '🇨🇦', name: 'Canada' },
    { code: '+44', flag: '🇬🇧', name: 'United Kingdom' },
    { code: '+971', flag: '🇦🇪', name: 'United Arab Emirates' },
    { code: '+966', flag: '🇸🇦', name: 'Saudi Arabia' },
    { code: '+65', flag: '🇸🇬', name: 'Singapore' },
    { code: '+61', flag: '🇦🇺', name: 'Australia' },
    { code: '+49', flag: '🇩🇪', name: 'Germany' },
    { code: '+33', flag: '🇫🇷', name: 'France' },
    { code: '+81', flag: '🇯🇵', name: 'Japan' },
    { code: '+7', flag: '🇷🇺', name: 'Russia' },
    { code: '+86', flag: '🇨🇳', name: 'China' },
    { code: '+55', flag: '🇧🇷', name: 'Brazil' },
    { code: '+27', flag: '🇿🇦', name: 'South Africa' },
    { code: '+62', flag: '🇮🇩', name: 'Indonesia' },
    { code: '+60', flag: '🇲🇾', name: 'Malaysia' },
    { code: '+92', flag: '🇵🇰', name: 'Pakistan' },
    { code: '+880', flag: '🇧🇩', name: 'Bangladesh' },
    { code: '+977', flag: '🇳🇵', name: 'Nepal' },
    { code: '+94', flag: '🇱🇰', name: 'Sri Lanka' },
    { code: '+974', flag: '🇶🇦', name: 'Qatar' },
    { code: '+965', flag: '🇰🇼', name: 'Kuwait' },
    { code: '+968', flag: '🇴🇲', name: 'Oman' },
    { code: '+973', flag: '🇧🇭', name: 'Bahrain' },
    { code: '+234', flag: '🇳🇬', name: 'Nigeria' },
    { code: '+90', flag: '🇹🇷', name: 'Turkey' },
    { code: '+39', flag: '🇮🇹', name: 'Italy' },
    { code: '+34', flag: '🇪🇸', name: 'Spain' },
    { code: '+31', flag: '🇳🇱', name: 'Netherlands' },
    { code: '+41', flag: '🇨🇭', name: 'Switzerland' },
    { code: '+46', flag: '🇸🇪', name: 'Sweden' },
    { code: '+47', flag: '🇳🇴', name: 'Norway' },
    { code: '+64', flag: '🇳🇿', name: 'New Zealand' },
    { code: '+63', flag: '🇵🇭', name: 'Philippines' },
    { code: '+66', flag: '🇹🇭', name: 'Thailand' },
    { code: '+84', flag: '🇻🇳', name: 'Vietnam' },
    { code: '+52', flag: '🇲🇽', name: 'Mexico' },
    { code: '+54', flag: '🇦🇷', name: 'Argentina' },
    { code: '+20', flag: '🇪🇬', name: 'Egypt' },
    { code: '+254', flag: '🇰🇪', name: 'Kenya' },
    { code: '+82', flag: '🇰🇷', name: 'South Korea' },
    { code: '+353', flag: '🇮🇪', name: 'Ireland' },
    { code: '+972', flag: '🇮🇱', name: 'Israel' },
    { code: '+48', flag: '🇵🇱', name: 'Poland' },
    { code: '+351', flag: '🇵🇹', name: 'Portugal' },
    { code: '+32', flag: '🇧🇪', name: 'Belgium' },
    { code: '+43', flag: '🇦🇹', name: 'Austria' },
    { code: '+852', flag: '🇭🇰', name: 'Hong Kong' },
    { code: '+886', flag: '🇹🇼', name: 'Taiwan' }
  ];

  window.openAuthModal = function (tab) {
    const overlay = document.getElementById('auth-modal-overlay') || document.getElementById('auth-modal');
    if (overlay) {
      overlay.style.display = 'flex';
      overlay.scrollTop = 0;
    }
    switchAuthTab(tab || 'login');
    const modalBody = document.getElementById('auth-modal-body');
    if (modalBody) modalBody.scrollTop = 0;
    const errBox = document.getElementById('auth-error-box');
    if (errBox) errBox.style.display = 'none';
    const passInput = document.getElementById('login-password');
    if (passInput) {
      passInput.value = '';
    }
    trackFunnelAction('funnel_direct_login_click', 'Opened Auth Modal (' + (tab || 'login') + ')');
  };

  window.closeAuthModal = function () {
    const overlay = document.getElementById('auth-modal-overlay') || document.getElementById('auth-modal');
    if (overlay) overlay.style.display = 'none';
  };

  window.handleAuthOverlayClick = function (event) {
    if (event.target.id === 'auth-modal-overlay' || event.target.id === 'auth-modal') {
      closeAuthModal();
    }
  };

  window.switchAuthTab = function (tab) {
    const tabLogin = document.getElementById('auth-tab-login') || document.getElementById('tab-btn-login');
    const tabReg = document.getElementById('auth-tab-register') || document.getElementById('tab-btn-register');
    const formLogin = document.getElementById('form-auth-login') || document.getElementById('form-login');
    const formReg = document.getElementById('form-auth-register') || document.getElementById('form-register');
    const formForgot = document.getElementById('form-auth-forgot');
    const privBox = document.getElementById('auth-privileges-box');
    const errBox = document.getElementById('auth-error-box') || document.getElementById('auth-msg');
    const modalBody = document.getElementById('auth-modal-body');
    const overlay = document.getElementById('auth-modal-overlay') || document.getElementById('auth-modal');

    if (errBox) errBox.style.display = 'none';
    if (formForgot) formForgot.style.display = 'none';
    if (modalBody) modalBody.scrollTop = 0;
    if (overlay) overlay.scrollTop = 0;

    if (tab === 'register') {
      if (tabReg) {
        tabReg.classList.add('active');
        tabReg.style.color = '#10b981';
        tabReg.style.borderBottomColor = '#10b981';
      }
      if (tabLogin) {
        tabLogin.classList.remove('active');
        tabLogin.style.color = '#64748b';
        tabLogin.style.borderBottomColor = 'transparent';
      }
      if (formLogin) formLogin.style.display = 'none';
      if (formReg) formReg.style.display = 'block';
      if (privBox) privBox.style.display = 'block';
    } else {
      if (tabLogin) {
        tabLogin.classList.add('active');
        tabLogin.style.color = '#38bdf8';
        tabLogin.style.borderBottomColor = '#38bdf8';
      }
      if (tabReg) {
        tabReg.classList.remove('active');
        tabReg.style.color = '#64748b';
        tabReg.style.borderBottomColor = 'transparent';
      }
      if (formLogin) formLogin.style.display = 'block';
      if (formReg) formReg.style.display = 'none';
      if (privBox) privBox.style.display = 'none';
    }
  };

  window.openForgotPasswordView = function () {
    const formLogin = document.getElementById('form-auth-login') || document.getElementById('form-login');
    const formReg = document.getElementById('form-auth-register') || document.getElementById('form-register');
    const formForgot = document.getElementById('form-auth-forgot');
    const tabLogin = document.getElementById('auth-tab-login') || document.getElementById('tab-btn-login');
    const tabReg = document.getElementById('auth-tab-register') || document.getElementById('tab-btn-register');
    const privBox = document.getElementById('auth-privileges-box');
    const errBox = document.getElementById('auth-error-box') || document.getElementById('auth-msg');
    const modalBody = document.getElementById('auth-modal-body');
    const overlay = document.getElementById('auth-modal-overlay') || document.getElementById('auth-modal');

    if (errBox) errBox.style.display = 'none';
    if (privBox) privBox.style.display = 'none';
    if (formLogin) formLogin.style.display = 'none';
    if (formReg) formReg.style.display = 'none';
    if (formForgot) formForgot.style.display = 'block';

    if (tabLogin) { tabLogin.style.color = '#64748b'; tabLogin.style.borderBottomColor = 'transparent'; }
    if (tabReg) { tabReg.style.color = '#64748b'; tabReg.style.borderBottomColor = 'transparent'; }

    if (modalBody) modalBody.scrollTop = 0;
    if (overlay) overlay.scrollTop = 0;
  };

  window.fillAdminLogin = function () {
    const identInput = document.getElementById('login-identifier') || document.getElementById('login-ident');
    const passInput = document.getElementById('login-password') || document.getElementById('login-pwd');
    if (identInput) {
      identInput.value = 'admin';
      identInput.dispatchEvent(new Event('input', { bubbles: true }));
    }
    if (passInput) {
      passInput.value = '';
      passInput.focus();
    }
  };

  window.handleLoginSubmit = async function (e) {
    if (e) e.preventDefault();
    const identInput = document.getElementById('login-identifier') || document.getElementById('login-ident');
    const passInput = document.getElementById('login-password') || document.getElementById('login-pwd');
    const errBox = document.getElementById('auth-error-box') || document.getElementById('auth-msg');
    const btn = document.getElementById('btn-submit-login');

    const ident = identInput ? identInput.value.trim() : '';
    const pwd = passInput ? passInput.value : '';

    if (!ident || !pwd) {
      showAuthError('Please enter both username/email and password.');
      return;
    }

    if (btn) {
      btn.disabled = true;
      btn.innerText = 'Verifying...';
    }

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
        showAuthSuccess('Login successful! Redirecting to Live Terminal...');
        setTimeout(() => {
          window.location.href = '/terminal';
        }, 600);
      } else {
        showAuthError(data.message || data.error || 'Login failed. Please check credentials.');
        if (btn) {
          btn.disabled = false;
          btn.innerText = 'Log In to Terminal';
        }
      }
    } catch (err) {
      showAuthError('Network error occurred. Please try again.');
      if (btn) {
        btn.disabled = false;
        btn.innerText = 'Log In to Terminal';
      }
    }
  };
  window.submitLogin = window.handleLoginSubmit;

  window.handleForgotPasswordSubmit = async function (e) {
    if (e) e.preventDefault();
    const identifier = document.getElementById('reset-identifier').value.trim();
    const phone = document.getElementById('reset-phone').value.trim();
    const newPass = document.getElementById('reset-new-password').value;
    const confPass = document.getElementById('reset-confirm-password').value;
    const btn = document.getElementById('btn-submit-reset');

    if (!identifier || !phone || !newPass) return;
    if (newPass.length < 6) {
      showAuthError('New password must be at least 6 characters.');
      return;
    }
    if (newPass !== confPass) {
      showAuthError('Passwords do not match.');
      return;
    }

    if (btn) {
      btn.disabled = true;
      btn.innerText = 'Verifying & Resetting...';
    }

    try {
      const res = await fetch('/api/auth/reset-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ identifier: identifier, phone: phone, new_password: newPass })
      });
      const data = await res.json();
      if (res.ok && data.token) {
        localStorage.setItem('auth_token', data.token);
        trackFunnelAction('funnel_direct_reset_success', 'Password reset directly from Terminal 1');
        showAuthSuccess('Password successfully reset! Launching Live Terminal...');
        setTimeout(() => {
          window.location.href = '/terminal';
        }, 700);
      } else {
        showAuthError(data.message || 'Could not reset password. Please check your username and registered phone.');
      }
    } catch (e) {
      showAuthError('Network error during password reset. Please try again.');
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.innerText = '🚀 Reset Password & Log In';
      }
    }
  };

  // Country Code Selection
  function renderCountryCodeList(filterText = '') {
    const listEl = document.getElementById('reg-country-list');
    if (!listEl) return;
    const q = (filterText || '').toLowerCase().trim();
    const filtered = countryCodeData.filter(c =>
      c.name.toLowerCase().includes(q) ||
      c.code.includes(q) ||
      c.code.replace('+', '').includes(q)
    );
    if (filtered.length === 0) {
      listEl.innerHTML = '<div style="padding: 8px; color: #94a3b8; font-size: 11px; text-align: center;">No country found</div>';
      return;
    }
    listEl.innerHTML = filtered.map(c => {
      const isSel = selectedCountryCode === c.code;
      const safeName = c.name.replace(/'/g, "\\'");
      return `<div onclick="selectCountryCode('${c.code}', '${c.flag}', '${safeName}')" style="display: flex; align-items: center; justify-content: space-between; padding: 6px 8px; border-radius: 5px; cursor: pointer; font-size: 12px; color: ${isSel ? '#38bdf8' : '#e2e8f0'}; background: ${isSel ? 'rgba(56, 189, 248, 0.15)' : 'transparent'}; transition: background 0.15s ease;">` +
        `<span style="display: flex; align-items: center; gap: 7px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">` +
          `<span style="font-size: 14px;">${c.flag}</span>` +
          `<span>${c.name}</span>` +
        `</span>` +
        `<span style="font-weight: 700; color: #94a3b8; font-size: 11px; margin-left: 8px;">${c.code}</span>` +
      `</div>`;
    }).join('');
  }

  window.toggleCountryCodeDropdown = function (e) {
    if (e) {
      e.preventDefault();
      e.stopPropagation();
    }
    const drop = document.getElementById('reg-country-dropdown');
    if (!drop) return;
    const isShown = drop.style.display === 'block';
    drop.style.display = isShown ? 'none' : 'block';
    if (!isShown) {
      renderCountryCodeList();
      const searchInput = document.getElementById('reg-country-search');
      if (searchInput) {
        searchInput.value = '';
        setTimeout(() => searchInput.focus(), 60);
      }
    }
  };

  window.filterCountryList = function (val) {
    renderCountryCodeList(val);
  };

  window.selectCountryCode = function (code, flag, name) {
    selectedCountryCode = code;
    selectedCountryFlag = flag;
    const codeEl = document.getElementById('reg-country-code');
    const flagEl = document.getElementById('reg-country-flag');
    const phoneInput = document.getElementById('reg-phone');
    if (codeEl) codeEl.textContent = code;
    if (flagEl) flagEl.textContent = flag;
    const drop = document.getElementById('reg-country-dropdown');
    if (drop) drop.style.display = 'none';

    if (phoneInput) {
      if (code === '+91') {
        phoneInput.maxLength = 10;
        phoneInput.placeholder = '10-digit mobile number';
      } else {
        phoneInput.maxLength = 14;
        phoneInput.placeholder = 'Mobile number (' + code + ')';
      }
      phoneInput.focus();
    }
    handleRegPhoneInput();
  };

  window.handleRegPhoneInput = function () {
    const input = document.getElementById('reg-phone');
    if (!input) return;
    const maxLen = (selectedCountryCode === '+91') ? 10 : 14;
    input.value = input.value.replace(/\D/g, '').substring(0, maxLen);
    if (phoneCheckTimer) clearTimeout(phoneCheckTimer);
    phoneCheckTimer = setTimeout(checkPhoneAvailability, 300);
  };

  window.checkPhoneAvailability = async function () {
    const phoneInput = document.getElementById('reg-phone');
    const hint = document.getElementById('reg-phone-hint');
    const statusEl = document.getElementById('reg-phone-status');
    if (!phoneInput) return;
    const clean = phoneInput.value.replace(/\D/g, '');
    if (!clean) {
      if (statusEl) statusEl.innerHTML = '';
      if (hint) hint.innerHTML = '';
      phoneInput.style.borderColor = '#334155';
      isPhoneAvailable = null;
      return;
    }

    if (selectedCountryCode === '+91') {
      if (clean.length < 10 || !['6', '7', '8', '9'].includes(clean[0])) {
        if (statusEl) statusEl.innerHTML = '<span style="color: #f87171;">Must be 10 digits (6-9)</span>';
        phoneInput.style.borderColor = '#f59e0b';
        isPhoneAvailable = false;
        return;
      }
    } else {
      if (clean.length < 6 || clean.length > 14) {
        if (statusEl) statusEl.innerHTML = '<span style="color: #f87171;">6-14 digits required</span>';
        phoneInput.style.borderColor = '#f59e0b';
        isPhoneAvailable = false;
        return;
      }
    }

    try {
      const res = await fetch(`/api/auth/check-phone?phone=${encodeURIComponent(clean)}&country_code=${encodeURIComponent(selectedCountryCode)}`);
      const data = await res.json();
      if (data.available) {
        if (statusEl) statusEl.innerHTML = '<span style="color: #34d399; font-weight: 600;">✅ Available</span>';
        if (hint) hint.innerHTML = `<span style="color: #34d399;">✅ Valid number (${selectedCountryCode} ${clean})</span>`;
        phoneInput.style.borderColor = '#10b981';
        isPhoneAvailable = true;
      } else {
        if (statusEl) statusEl.innerHTML = '<span style="color: #f87171; font-weight: 600;">❌ Already registered</span>';
        if (hint) hint.innerHTML = `<span style="color: #f87171; font-weight: 700;">❌ ${data.message} <a href="javascript:void(0)" onclick="switchAuthTab('login')" style="color: #38bdf8; text-decoration: underline;">Go to Log In 🔑</a></span>`;
        phoneInput.style.borderColor = '#ef4444';
        isPhoneAvailable = false;
      }
    } catch (e) {}
  };

  window.debounceCheckUsername = function () {
    if (usernameCheckTimer) clearTimeout(usernameCheckTimer);
    usernameCheckTimer = setTimeout(checkUsernameAvailability, 350);
  };

  window.checkUsernameAvailability = async function () {
    const usernameInput = document.getElementById('reg-username');
    const statusEl = document.getElementById('reg-username-status');
    if (!usernameInput || !statusEl) return;
    const val = usernameInput.value.trim().toLowerCase();
    if (!val) {
      statusEl.innerHTML = '';
      isUsernameAvailable = false;
      usernameInput.style.borderColor = '#334155';
      return;
    }
    if (val.length < 3) {
      statusEl.innerHTML = '<span style="color: #94a3b8;">Min 3 characters</span>';
      isUsernameAvailable = false;
      usernameInput.style.borderColor = '#f59e0b';
      return;
    }
    if (!/^[a-zA-Z0-9_.-]+$/.test(val)) {
      statusEl.innerHTML = '<span style="color: #f87171;">Only letters, numbers, _, -</span>';
      isUsernameAvailable = false;
      usernameInput.style.borderColor = '#ef4444';
      return;
    }

    try {
      const res = await fetch(`/api/auth/check-username?username=${encodeURIComponent(val)}`);
      const data = await res.json();
      if (data.available) {
        statusEl.innerHTML = '<span style="color: #34d399; font-weight: 600;">✅ Available</span>';
        isUsernameAvailable = true;
        usernameInput.style.borderColor = '#10b981';
      } else {
        statusEl.innerHTML = `<span style="color: #f87171; font-weight: 600;">❌ ${data.message || 'Already taken'}</span>`;
        isUsernameAvailable = false;
        usernameInput.style.borderColor = '#ef4444';
      }
    } catch (e) {}
  };

  window.checkPasswordMatch = function () {
    const pw = document.getElementById('reg-password');
    const cpw = document.getElementById('reg-confirm-password');
    const statusEl = document.getElementById('reg-password-match-status');
    if (!pw || !cpw || !statusEl) return;
    const pVal = pw.value;
    const cpVal = cpw.value;
    if (!cpVal) {
      statusEl.innerHTML = '';
      cpw.style.borderColor = '#334155';
      return;
    }
    if (pVal === cpVal) {
      statusEl.innerHTML = '<span style="color: #34d399; font-weight: 600;">✅ Passwords match</span>';
      cpw.style.borderColor = '#10b981';
    } else {
      statusEl.innerHTML = '<span style="color: #f87171; font-weight: 600;">❌ Passwords do not match</span>';
      cpw.style.borderColor = '#ef4444';
    }
  };

  window.handleRegisterSubmit = async function (e) {
    if (e) e.preventDefault();
    const usernameInput = document.getElementById('reg-username') || document.getElementById('reg-uname');
    const emailInput = document.getElementById('reg-email');
    const passwordInput = document.getElementById('reg-password') || document.getElementById('reg-pwd');
    const confirmInput = document.getElementById('reg-confirm-password');
    const phoneInput = document.getElementById('reg-phone');
    const styleInput = document.getElementById('reg-trading-style') || document.getElementById('reg-style');
    const policyChk = document.getElementById('reg-accept-policy') || document.getElementById('reg-policy');
    const termsContainer = document.getElementById('reg-terms-container');
    const btn = document.getElementById('btn-submit-register');

    const username = usernameInput ? usernameInput.value.trim().toLowerCase() : '';
    const email = emailInput ? emailInput.value.trim() : '';
    const password = passwordInput ? passwordInput.value : '';
    const confirmPassword = confirmInput ? confirmInput.value : password;
    const phone = phoneInput ? phoneInput.value.replace(/\D/g, '') : '';
    const style = styleInput ? styleInput.value : 'intraday_scalper';

    // 1. Username checks
    if (!username || username.length < 3) {
      showAuthError('Please choose a username of at least 3 characters.');
      usernameInput && usernameInput.focus();
      return;
    }

    // 2. Email checks
    if (!email || !email.includes('@') || !email.includes('.')) {
      showAuthError('Please enter a valid email address.');
      emailInput && emailInput.focus();
      return;
    }

    // 3. Password checks
    if (!password || password.length < 4) {
      showAuthError('Password must be at least 4 characters long.');
      passwordInput && passwordInput.focus();
      return;
    }

    // 4. Confirm Password checks
    if (confirmInput && password !== confirmPassword) {
      showAuthError('Passwords do not match. Please ensure both password fields match.');
      confirmInput && confirmInput.focus();
      return;
    }

    // 5. Mobile Number checks (optional)
    if (phone) {
      if (selectedCountryCode === '+91') {
        if (phone.length !== 10 || !['6', '7', '8', '9'].includes(phone[0])) {
          showAuthError('Please enter a valid 10-digit Indian mobile number starting with 6, 7, 8, or 9 (or leave blank).');
          phoneInput && phoneInput.focus();
          return;
        }
      } else {
        if (phone.length < 6 || phone.length > 14) {
          showAuthError(`Please enter a valid mobile number (6 to 14 digits) for country code ${selectedCountryCode}.`);
          phoneInput && phoneInput.focus();
          return;
        }
      }
      if (isPhoneAvailable === false) {
        showAuthError('This mobile number is already registered to another account. Please Log In.');
        phoneInput && phoneInput.focus();
        return;
      }
    }

    // 6. Policy Check
    if (!policyChk || !policyChk.checked) {
      showAuthError('Please click and accept the Terms of Service & Privacy Policy checkbox to complete registration.');
      if (termsContainer) {
        termsContainer.style.borderColor = '#ef4444';
        termsContainer.style.boxShadow = '0 0 14px rgba(239, 68, 68, 0.45)';
        setTimeout(() => {
          termsContainer.style.borderColor = '#1e293b';
          termsContainer.style.boxShadow = 'none';
        }, 4000);
      }
      policyChk && policyChk.focus();
      return;
    }

    if (btn) {
      btn.disabled = true;
      btn.innerText = 'Creating Account... ⏳';
    }

    try {
      const res = await fetch('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: username,
          email: email,
          password: password,
          confirm_password: confirmPassword,
          country_code: selectedCountryCode,
          phone: phone,
          trading_style: style,
          accepted_policy: true
        })
      });
      const data = await res.json();
      if (res.ok && data.token) {
        localStorage.setItem('auth_token', data.token);
        trackFunnelAction('funnel_direct_register_success', 'Created account directly from Terminal 1');
        showAuthSuccess('Account created successfully! Launching Live Terminal...');
        setTimeout(() => {
          window.location.href = '/terminal';
        }, 800);
      } else {
        showAuthError(data.message || data.error || 'Registration failed. Username or email may already be in use.');
        if (btn) {
          btn.disabled = false;
          btn.innerText = 'Register & Create Account 🚀';
        }
      }
    } catch (err) {
      showAuthError('Network error occurred. Please try again.');
      if (btn) {
        btn.disabled = false;
        btn.innerText = 'Register & Create Account 🚀';
      }
    }
  };
  window.submitRegister = window.handleRegisterSubmit;

  function showAuthError(msg) {
    const box = document.getElementById('auth-error-box') || document.getElementById('auth-msg');
    if (!box) return;
    box.innerHTML = msg;
    box.className = 'auth-msg error';
    box.style.display = 'block';
    box.style.background = 'rgba(239, 68, 68, 0.12)';
    box.style.border = '1px solid rgba(239, 68, 68, 0.4)';
    box.style.color = '#f87171';
  }

  function showAuthSuccess(msg) {
    const box = document.getElementById('auth-error-box') || document.getElementById('auth-msg');
    if (!box) return;
    box.innerHTML = msg;
    box.className = 'auth-msg success';
    box.style.display = 'block';
    box.style.background = 'rgba(16, 185, 129, 0.15)';
    box.style.border = '1px solid rgba(16, 185, 129, 0.4)';
    box.style.color = '#34d399';
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

  // Close modals and dropdowns when clicking outside
  document.addEventListener('click', (e) => {
    const authModal = document.getElementById('auth-modal-overlay') || document.getElementById('auth-modal');
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
