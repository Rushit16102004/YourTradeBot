@echo off
title VWAP Trading Platform Launcher
cd /d "%~dp0"
echo ========================================================
echo  Starting VWAP Server (Port 8000) + Cloudflare & Telegram
echo ========================================================

:: 1. Launch FastAPI / Uvicorn Server on Port 8000
start "VWAP Server" cmd /k "python server.py"

:: 2. Wait 3 seconds for server initialization
timeout /t 3 /nobreak >nul

:: 3. Launch Cloudflare Tunnel with Automatic Telegram Broadcast
start "Cloudflare Tunnel" cmd /k "python start_tunnel_with_telegram.py"

echo.
echo Both VWAP Server and Cloudflare Tunnel have been launched!
echo The new live link will be automatically sent to your Telegram.
echo ========================================================
timeout /t 5
