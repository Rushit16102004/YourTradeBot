@echo off
title Cloudflare Tunnel - VWAP Platform
cd /d "%~dp0"
echo ========================================================
echo  Starting Cloudflare Secure Tunnel + Telegram Broadcast
echo  (100%% Free - Zero Interstitial Warning Screens)
echo ========================================================
echo.
python start_tunnel_with_telegram.py
pause
