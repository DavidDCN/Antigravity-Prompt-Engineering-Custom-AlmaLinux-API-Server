#!/usr/bin/env bash
# One-shot provisioning for the ATTRial image server on AlmaLinux 9.
# Usage (on the VM, from the folder that contains server/ and deploy/):
#     sudo bash deploy/setup.sh
# Safe to re-run: it updates code and dependencies, and keeps data and the API key.
set -euo pipefail

SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BASE=/srv/imgserver
ENV_FILE=/etc/imgserver/imgserver.env

if [[ $EUID -ne 0 ]]; then echo "Run with sudo." >&2; exit 1; fi

echo "==> Installing packages"
dnf -y install nginx policycoreutils-python-utils rsync curl
# Needs Python >= 3.10. AlmaLinux 9 ships python3.11/3.12 as add-ons; AlmaLinux 10 defaults to 3.12.
PY=""
for v in 3.12 3.11; do
    if command -v "python$v" &>/dev/null || dnf -y install "python$v" "python$v-pip" &>/dev/null; then
        PY="python$v"; break
    fi
done
if [[ -z "$PY" ]]; then
    dnf -y install python3 python3-pip
    PY=python3
fi
"$PY" -c 'import sys; assert sys.version_info >= (3, 10), sys.version' \
    || { echo "Python 3.10+ is required." >&2; exit 1; }
echo "    Using $($PY --version)"

echo "==> Creating service user and folders"
id imgserver &>/dev/null || useradd --system --home-dir "$BASE" --shell /sbin/nologin imgserver
mkdir -p "$BASE/app" "$BASE/data/backgrounds" "$BASE/data/uploads" /etc/imgserver

echo "==> Copying application code"
rsync -a --delete --exclude '__pycache__' --exclude 'data/' --exclude 'tests/' \
    "$SRC_DIR/server/" "$BASE/app/"

echo "==> Python virtualenv + dependencies"
[[ -x "$BASE/venv/bin/python" ]] || "$PY" -m venv "$BASE/venv"
"$BASE/venv/bin/pip" install --upgrade pip
"$BASE/venv/bin/pip" install -r "$BASE/app/requirements.txt"

echo "==> Configuration"
if [[ ! -f "$ENV_FILE" ]]; then
    install -m 640 -o root -g imgserver "$SRC_DIR/deploy/imgserver.env.example" "$ENV_FILE"
    KEY="$(head -c 32 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' | head -c 40)"
    sed -i "s/^IMGSERVER_API_KEY=.*/IMGSERVER_API_KEY=${KEY}/" "$ENV_FILE"
    echo "    Generated admin API key (also stored in $ENV_FILE): ${KEY}"
fi

chown -R imgserver:imgserver "$BASE"
chmod 755 /srv "$BASE"
chmod -R 755 "$BASE/app" "$BASE/venv/bin"

echo "==> SELinux: allow nginx to proxy to the API and systemd to execute venv binaries"
if command -v getenforce &>/dev/null && [[ "$(getenforce)" != "Disabled" ]]; then
    setsebool -P httpd_can_network_connect 1
    restorecon -Rv "$BASE" || true
    chcon -R -t bin_t "$BASE/venv/bin/" || true
fi

echo "==> systemd service"
install -m 644 "$SRC_DIR/deploy/imgserver.service" /etc/systemd/system/imgserver.service
systemctl daemon-reload
systemctl enable imgserver
systemctl restart imgserver

echo "==> nginx reverse proxy"
install -m 644 "$SRC_DIR/deploy/nginx-imgserver.conf" /etc/nginx/conf.d/imgserver.conf
# Drop the stock default_server so ours takes port 80.
sed -i 's/ default_server//g' /etc/nginx/nginx.conf
nginx -t
systemctl enable nginx
systemctl restart nginx

echo "==> SELinux: allow nginx to proxy to the API"
if command -v getenforce &>/dev/null && [[ "$(getenforce)" != "Disabled" ]]; then
    setsebool -P httpd_can_network_connect 1
fi

echo "==> Firewall: open HTTP"
if systemctl is-active --quiet firewalld; then
    firewall-cmd --permanent --add-service=http
    firewall-cmd --reload
fi

echo "==> Health check"
sleep 2
if curl -fsS http://127.0.0.1/api/health; then
    echo
    IP="$(hostname -I | awk '{print $1}')"
    echo "Done. From your Windows PC, open Web GUI: http://${IP}/"
    echo "Swagger API docs:                         http://${IP}/docs"
    echo "Desktop app server address:               http://${IP}"
else
    echo "Health check failed. Inspect: journalctl -u imgserver -n 50 --no-pager" >&2
    exit 1
fi
