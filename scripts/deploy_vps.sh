#!/usr/bin/env bash
# ==============================================================================
# NIFTY 50 Pro Terminal — Ubuntu 22.04 / 24.04 VPS Automated Deployment Script
# Run as root: sudo bash scripts/deploy_vps.sh
# ==============================================================================

set -e

echo "=== [1/6] Updating System & Installing Prerequisites ==="
apt-get update && apt-get upgrade -y
apt-get install -y python3 python3-pip python3-venv git curl nginx certbot python3-certbot-nginx build-essential libffi-dev sqlite3

APP_DIR="/var/www/nifty_terminal"

echo "=== [2/6] Setting Up Project Directory at $APP_DIR ==="
mkdir -p $APP_DIR
mkdir -p $APP_DIR/logs
mkdir -p $APP_DIR/temp_storage
mkdir -p $APP_DIR/data_cache

# Copy project files if running outside the application directory
if [ -f "server.py" ] && [ "$(pwd)" != "$APP_DIR" ]; then
    cp -r * $APP_DIR/
fi

cd $APP_DIR

echo "=== [3/6] Setting Up Python Virtual Environment ==="
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

echo "=== [4/6] Checking .env Configuration ==="
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "⚠️ Created .env from .env.example. PLEASE EDIT .env WITH YOUR CREDENTIALS!"
    fi
fi

echo "=== [5/6] Configuring systemd Service ==="
cp scripts/nifty_terminal.service /etc/systemd/system/nifty_terminal.service
systemctl daemon-reload
systemctl enable nifty_terminal
systemctl restart nifty_terminal

echo "=== [6/6] Configuring Nginx Reverse Proxy ==="
cp scripts/nginx_nifty.conf /etc/nginx/sites-available/nifty_terminal
ln -sf /etc/nginx/sites-available/nifty_terminal /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl restart nginx

echo ""
echo "=========================================================================="
echo "✅ DEPLOYMENT COMPLETE!"
echo "Server Status: $(systemctl is-active nifty_terminal)"
echo "Nginx Status:  $(systemctl is-active nginx)"
echo ""
echo "Access your terminal at: http://$(curl -s ifconfig.me)"
echo "To view live logs: journalctl -u nifty_terminal -f"
echo "To enable free HTTPS SSL: certbot --nginx -d yourdomain.com"
echo "=========================================================================="
