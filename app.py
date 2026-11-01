"""
NIFTY 50 Live Trading Terminal — 100% Pure HTML Local Web Server.
Zero Streamlit. Runs high-performance Trading Terminal on http://localhost:8000.
Features:
- Instant sub-second page loading
- 2 months of candles stored in 1st Priority In-Memory RAM Cache
- Real-time tick updates directly into memory
- Locked user viewport (never auto-adjusts or jumps on updates)
- Full tactile control over X-axis and Y-axis scale and zoom
- Native on-chart drawing tools (trendlines, zone rectangles, eraser)
- Background 24/7 strategy evaluation & Telegram alerts
"""
import os
import sys

from server import app, main

if __name__ == "__main__":
    main()
    
# http://localhost:8000//
# http://<YOUR_LAPTOP_LOCAL_IP>:8000