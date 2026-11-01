# 🚀 NIFTY 50 Pro Terminal — Live Server Production Deployment Guide

This guide provides end-to-end instructions for deploying the **NIFTY 50 Pro Terminal & AI Strategy Copilot** onto a live 24/7 cloud server (Ubuntu 22.04 / 24.04 LTS VPS or Cloud Provider).

---

## 📋 1. Recommended Cloud Server Specifications

Because this application runs **continuous background threads** (5m candle aggregation, Angel One WebSocket tick streaming, 24/7 Telegram alerts, vector retrieval, and live option chain polling), it requires a persistent VPS rather than serverless functions.

| Resource | Minimum Specification | Recommended Specification |
| :--- | :--- | :--- |
| **OS** | Ubuntu 22.04 LTS / 24.04 LTS | Ubuntu 24.04 LTS |
| **vCPU** | 1 Core | 2 Cores |
| **RAM** | 2 GB | 4 GB (Recommended for ChromaDB + In-Memory Cache) |
| **Disk** | 20 GB SSD / NVMe | 40 GB NVMe |
| **Providers** | DigitalOcean ($6-$12/mo), Hetzner (€4.5-€7/mo), AWS EC2 (t3.small/medium), Hostinger VPS |

---

## 📦 2. Preparing and Uploading Code to Server

### Option A: Using Git (Recommended & Easiest)
1. Push your repository to GitHub / GitLab (keep it **Private**):
   ```bash
   git init
   git add .
   git commit -m "Initial commit for production"
   git remote add origin https://github.com/yourusername/nifty-terminal.git
   git branch -M main
   git push -u origin main
   ```
2. On your live server (SSH terminal):
   ```bash
   git clone https://github.com/yourusername/nifty-terminal.git /var/www/nifty_terminal
   cd /var/www/nifty_terminal
   ```

### Option B: Direct Upload via SCP / rsync / FileZilla (From Windows)
If you do not use Git, open PowerShell on your Windows PC:
```powershell
# Exclude temporary folders and upload directly to server
scp -r -P 22 . root@YOUR_SERVER_IP:/var/www/nifty_terminal
```
*(Or connect using **FileZilla** SFTP to your server IP on Port 22 and drag-and-drop the files into `/var/www/nifty_terminal`)*.

---

## ⚙️ 3. Configure Production Environment Variables (`.env`)

On the server, create your `.env` file from `.env.example`:

```bash
cd /var/www/nifty_terminal
cp .env.example .env
nano .env
```

Fill in your actual production credentials:
```env
# 1. Angel One SmartAPI Credentials
ANGEL_API_KEY="your_api_key"
ANGEL_CLIENT_ID="your_client_id"
ANGEL_PASSWORD="your_trading_pin"
ANGEL_TOTP_SECRET="your_totp_alphanumeric_secret"

# 2. Market Contract Configuration
DEFAULT_EXCHANGE=NSE
DEFAULT_SYMBOL="NIFTY 50"
DEFAULT_TOKEN="99926000"
MOCK_MODE=false

# 3. Telegram 24/7 Alerts
TELEGRAM_BOT_TOKEN="your_bot_token"
TELEGRAM_CHAT_ID="your_chat_id"
TELEGRAM_PHONE="your_phone"
TELEGRAM_ENABLED=true

# 4. Google Gemini API Key (Copilot & RAG)
GEMINI_API_KEY="your_gemini_api_key"

# 5. Network Binding
HOST=0.0.0.0
PORT=8000
```
*Save and exit in nano: press `Ctrl + O`, `Enter`, then `Ctrl + X`.*

---

## 🛠️ 4. Method 1: Automated VPS Deployment (Recommended)

We have provided a turnkey automated bash script that installs Python, virtual environment, system dependencies, Nginx, Certbot SSL, and systemd service:

```bash
cd /var/www/nifty_terminal
sudo bash scripts/deploy_vps.sh
```

---

## 🔧 5. Manual Step-by-Step Deployment (If doing manually)

If you prefer executing each step manually on Ubuntu:

### Step 5.1: Install System Packages
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv git curl nginx certbot python3-certbot-nginx build-essential libffi-dev sqlite3
```

### Step 5.2: Create Python Virtual Environment & Install Dependencies
```bash
cd /var/www/nifty_terminal
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

### Step 5.3: Set Up 24/7 Background Systemd Service
Copy the service file to systemd:
```bash
sudo cp scripts/nifty_terminal.service /etc/systemd/system/nifty_terminal.service
sudo systemctl daemon-reload
sudo systemctl enable nifty_terminal
sudo systemctl start nifty_terminal
```

Check that the server is active:
```bash
sudo systemctl status nifty_terminal
```

### Step 5.4: Configure Nginx (Reverse Proxy & WebSockets)
```bash
sudo cp scripts/nginx_nifty.conf /etc/nginx/sites-available/nifty_terminal
# Edit server_name with your actual domain or IP:
sudo nano /etc/nginx/sites-available/nifty_terminal

# Enable site and test configuration:
sudo ln -sf /etc/nginx/sites-available/nifty_terminal /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
```

### Step 5.5: Enable Free HTTPS SSL (Let's Encrypt)
If you have pointed a domain (e.g., `trade.yourdomain.com`) to your server IP:
```bash
sudo certbot --nginx -d trade.yourdomain.com
```

---

## 🐳 6. Method 2: Docker Container Deployment

If you prefer running via Docker and Docker Compose:

### Step 6.1: Install Docker on Server
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo apt install -y docker-compose-plugin
```

### Step 6.2: Launch Application
```bash
cd /var/www/nifty_terminal
# Build and run in detached mode
sudo docker compose up -d --build
```

### Step 6.3: View Logs / Stop
```bash
# View live container logs
sudo docker compose logs -f

# Restart container
sudo docker compose restart

# Stop container
sudo docker compose down
```

---

## 🛡️ 7. Firewall & Server Security Setup

Ensure your VPS firewall allows SSH, Web, and HTTPS traffic:
```bash
sudo ufw allow 22/tcp     # SSH access
sudo ufw allow 80/tcp     # HTTP (Nginx)
sudo ufw allow 443/tcp    # HTTPS (SSL)
sudo ufw enable
```

---

## 🔍 8. Management, Monitoring & Log Inspection

| Task | Command |
| :--- | :--- |
| **Check server status** | `sudo systemctl status nifty_terminal` |
| **Stream live application logs** | `journalctl -u nifty_terminal -f` |
| **Restart the terminal server** | `sudo systemctl restart nifty_terminal` |
| **Stop the terminal server** | `sudo systemctl stop nifty_terminal` |
| **Check Health Endpoint** | `curl http://localhost:8000/health` |
| **Check Nginx Access Logs** | `tail -f /var/log/nginx/access.log` |
| **Check Nginx Error Logs** | `tail -f /var/log/nginx/error.log` |

---

## 🚨 9. Important Market Hours & 24/7 Execution Notes

1. **Broker Token Renewal (9:00 AM IST)**:
   - Angel One SmartAPI JWT tokens expire daily. The application contains an automated TOTP background relogin loop. Ensure `ANGEL_TOTP_SECRET` in `.env` is accurate so it re-authenticates automatically every morning without requiring human intervention.
2. **SQLite Database Persistence**:
   - User profiles, trade predictions, and drawing tools are stored in `users.db`. Always maintain periodic backups of `users.db`.
3. **NSE Live Option Chain Scraper**:
   - The engine uses `curl_cffi` to query NSE India. Ensure the server has outgoing internet connectivity to `nseindia.com`.
