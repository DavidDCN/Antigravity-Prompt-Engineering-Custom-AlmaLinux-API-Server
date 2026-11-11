#!/usr/bin/env bash
# One-shot provisioning for the ATTRial image server on AlmaLinux 9/10.
# Usage (on the VM, from the folder that contains server/ and deploy/):
#     sudo bash deploy/setup.sh
# Safe to re-run: it updates code and dependencies, and keeps data and the API key.
set -euo pipefail

SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BASE=/srv/imgserver
ENV_FILE=/etc/imgserver/imgserver.env
MIRROR_DIR="/home/daviddcn/Downloads/background images"

if [[ $EUID -ne 0 ]]; then echo "Run with sudo." >&2; exit 1; fi

echo "==> Installing packages"
dnf -y install nginx policycoreutils-python-utils rsync curl acl
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

echo "==> Syncing with AlmaLinux desktop folder: $MIRROR_DIR"
if [[ -d /home/daviddcn ]]; then
    mkdir -p "$MIRROR_DIR"
    chown -R daviddcn:daviddcn "/home/daviddcn/Downloads" || true
    chmod o+x /home/daviddcn "/home/daviddcn/Downloads" || true
    chmod 777 "$MIRROR_DIR" || true
    setfacl -m u:imgserver:rx /home/daviddcn "/home/daviddcn/Downloads" || true
    setfacl -R -m u:imgserver:rwx "$MIRROR_DIR" || true
    setfacl -R -d -m u:imgserver:rwx "$MIRROR_DIR" || true
    setfacl -R -d -m u:daviddcn:rwx "$MIRROR_DIR" || true
    # Copy any existing images from the desktop folder into backgrounds/ so none are missed
    shopt -s nullglob nocaseglob
    for f in "$MIRROR_DIR"/*.{jpg,jpeg,png,webp,avif,gif,bmp}; do
        [[ -f "$f" ]] && cp -n "$f" "$BASE/data/backgrounds/" || true
    done
    shopt -u nullglob nocaseglob
fi

chown -R imgserver:imgserver "$BASE"
chmod 755 /srv "$BASE" "$BASE/data" "$BASE/data/backgrounds" "$BASE/data/uploads"
chmod -R 644 "$BASE/data/backgrounds/"* 2>/dev/null || true
chmod -R 644 "$BASE/data/uploads/"* 2>/dev/null || true
chmod -R 755 "$BASE/app" "$BASE/venv/bin"

echo "==> SELinux: allow nginx to proxy to the API and systemd to execute venv binaries & sync mirror folder"
if command -v getenforce &>/dev/null && [[ "$(getenforce)" != "Disabled" ]]; then
    setsebool -P httpd_can_network_connect 1
    restorecon -Rv "$BASE" || true
    chcon -R -t bin_t "$BASE/venv/bin/" || true
    [[ -d "$MIRROR_DIR" ]] && chcon -R -t var_t "$MIRROR_DIR" || true
fi

echo "==> systemd service"
install -m 644 "$SRC_DIR/deploy/imgserver.service" /etc/systemd/system/imgserver.service
systemctl daemon-reload
systemctl enable imgserver
systemctl restart imgserver

echo "==> nginx reverse proxy"
install -m 644 "$SRC_DIR/deploy/nginx-imgserver.conf" /etc/nginx/conf.d/imgserver.conf
sed -i 's/ default_server//g' /etc/nginx/nginx.conf
nginx -t
systemctl enable nginx
systemctl restart nginx

echo "==> Firewall: open HTTP"
if systemctl is-active --quiet firewalld; then
    firewall-cmd --permanent --add-service=http
    firewall-cmd --reload
fi

echo "==> Health check & Two-Way Folder Sync"
sleep 2
if curl -fsS http://127.0.0.1/api/database >/dev/null; then
    [[ -d "$MIRROR_DIR" ]] && chown -R daviddcn:daviddcn "$MIRROR_DIR" 2>/dev/null || true
    IP="$(hostname -I | awk '{print $1}')"
    echo
    echo "Done! Web GUI (Open Frame + All Database Images): http://${IP}/"
    echo "AlmaLinux synced folder: $MIRROR_DIR"
else
    echo "Health check failed. Inspect: journalctl -u imgserver -n 50 --no-pager" >&2
    exit 1
fi
