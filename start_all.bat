@echo off
title NIFTY 50 Pro Terminal Launcher
cd /d "%~dp0"
echo ========================================================
echo  Starting NIFTY 50 Pro Terminal (FastAPI / Port 8000)
echo ========================================================

:: Launch FastAPI / Uvicorn Server on Port 8000
python server.py

pause
