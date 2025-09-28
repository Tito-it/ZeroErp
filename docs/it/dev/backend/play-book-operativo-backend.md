# Playbook operativo (SOLO COMANDI)

> Copia‑incolla sequenziale per creare un CT `backend-*` come `backend-dev` (Django + Gunicorn + Nginx, Redis, PostgreSQL esterno, Tailscale, UFW). Sostituisci i **⚠️ segnaposto**.

## Variabili (adatta e poi esegui)

```bash
export CTID=⚠️102
export HOSTNAME=backend-dev
export TAIL_NAME=backend-dev.tailXXXX.ts.net
export APP_USER=tid
export DB_NAME=⚠️yourdb
export DB_USER=zeroerp_app
export DB_PASS=⚠️StrongPassword
export DB_HOST=⚠️dbdev.tailXXXX.ts.net
export DB_PORT=5432
```

## 0) Host Proxmox – abilita TUN e riavvia CT

```bash
echo "lxc.cgroup2.devices.allow: c 10:200 rwm" >> /etc/pve/lxc/$CTID.conf
echo "lxc.mount.entry: /dev/net/tun dev/net/tun none bind,create=file" >> /etc/pve/lxc/$CTID.conf
pct restart $CTID
```

## 1) Base nel CT (Debian 12)

```bash
apt update && apt -y upgrade
apt install -y locales openssh-server sudo curl gnupg ufw
sed -i '/it_IT.UTF-8 UTF-8/s/^# *//' /etc/locale.gen
sed -i '/en_US.UTF-8 UTF-8/s/^# *//' /etc/locale.gen
locale-gen && update-locale LANG=it_IT.UTF-8
adduser $APP_USER && usermod -aG sudo $APP_USER
printf '
PermitRootLogin no
' >> /etc/ssh/sshd_config && systemctl restart ssh
```

## 2) Tailscale + UFW

```bash
curl -fsSL https://tailscale.com/install.sh | sh
systemctl enable --now tailscaled
# login manuale o con auth-key
# tailscale up --auth-key=tskey-XXXX --hostname=$HOSTNAME
ufw allow 22/tcp
ufw default deny incoming && ufw default allow outgoing
ufw allow 80/tcp && ufw allow 443/tcp
ufw enable
```

*(opzionale) Limita SSH solo su Tailscale*

```bash
ufw delete allow 22/tcp || true
ufw allow in on tailscale0 to any port 22 proto tcp
ufw status verbose
```

## 3) Stack applicativo

```bash
apt install -y \
  python3-venv python3-pip python3-dev build-essential libpq-dev pkg-config \
  postgresql-client nginx redis-server git ca-certificates unzip
systemctl enable --now nginx redis-server
```

## 4) App Django

```bash
sudo -u $APP_USER bash -lc '
  mkdir -p ~/apps/zeroerp && cd ~/apps/zeroerp && \
  python3 -m venv .venv && source .venv/bin/activate && \
  pip install --upgrade pip && \
  pip install django gunicorn "psycopg[binary]" django-redis djangorestframework && \
  django-admin startproject zeroerp_backend .
'
```

## 5) Static/Media

```bash
mkdir -p /var/www/zeroerp/static /var/www/zeroerp/media
chown -R $APP_USER:$APP_USER /var/www/zeroerp
sudo -u $APP_USER bash -lc 'cd ~/apps/zeroerp && source .venv/bin/activate && python manage.py collectstatic --noinput'
```

## 6) Env sicuro (no password nel codice)

```bash
install -d -m 0750 /etc/zeroerp
cat > /etc/zeroerp/zeroerp.env <<EOF
DJANGO_SECRET_KEY=$(openssl rand -base64 48)
DJANGO_DEBUG=1
DJANGO_ALLOWED_HOSTS=${HOSTNAME},${TAIL_NAME},localhost,127.0.0.1
DB_NAME=${DB_NAME}
DB_USER=${DB_USER}
DB_PASSWORD='${DB_PASS}'
DB_HOST=${DB_HOST}
DB_PORT=${DB_PORT}
EOF
chown root:$APP_USER /etc/zeroerp/zeroerp.env && chmod 640 /etc/zeroerp/zeroerp.env
```

## 7) PostgreSQL (su VM `dbdev`) – una tantum

```sql
CREATE ROLE ${DB_USER} LOGIN PASSWORD '${DB_PASS}' NOCREATEDB NOCREATEROLE;
CREATE SCHEMA IF NOT EXISTS django AUTHORIZATION ${DB_USER};
ALTER ROLE ${DB_USER} IN DATABASE ${DB_NAME}
  SET search_path = django, public, config, anagrafiche, vendite, acquisti, dbops;
REVOKE CREATE ON SCHEMA public FROM ${DB_USER};
-- In pg_hba.conf (IP Tailscale del CT):
-- host  ${DB_NAME}  ${DB_USER}  100.x.y.z/32  scram-sha-256
```

## 8) Gunicorn (systemd)

```bash
cat > /etc/systemd/system/zeroerp-gunicorn.service <<EOF
[Unit]
Description=ZeroERP Django (Gunicorn)
After=network.target

[Service]
User=${APP_USER}
Group=${APP_USER}
WorkingDirectory=/home/${APP_USER}/apps/zeroerp
Environment="PATH=/home/${APP_USER}/apps/zeroerp/.venv/bin"
EnvironmentFile=/etc/zeroerp/zeroerp.env
ExecStart=/home/${APP_USER}/apps/zeroerp/.venv/bin/gunicorn zeroerp_backend.wsgi:application --bind 127.0.0.1:8000 --workers 3 --timeout 60
Restart=always

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload && systemctl enable --now zeroerp-gunicorn
```

## 9) Nginx (HTTPS self‑signed + redirect)

```bash
openssl req -x509 -nodes -newkey rsa:2048 -days 365 \
  -keyout /etc/ssl/private/backend-dev.key \
  -out /etc/ssl/certs/backend-dev.crt \
  -subj "/CN=${TAIL_NAME}"
cat > /etc/nginx/sites-available/zeroerp <<'EOF'
server {
  listen 443 ssl http2;
  server_name ${TAIL_NAME} ${HOSTNAME};
  ssl_certificate     /etc/ssl/certs/backend-dev.crt;
  ssl_certificate_key /etc/ssl/private/backend-dev.key;
  location /static/ { alias /var/www/zeroerp/static/; expires 7d; }
  location /media/  { alias /var/www/zeroerp/media/;  expires off; }
  location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
  }
}
server { listen 80; server_name ${TAIL_NAME} ${HOSTNAME}; return 308 https://$host$request_uri; }
EOF
ln -s /etc/nginx/sites-available/zeroerp /etc/nginx/sites-enabled/zeroerp || true
nginx -t && systemctl reload nginx
```

## 10) Sicurezza Django dietro proxy (append alla fine di settings.py)

```bash
cat >> /home/${APP_USER}/apps/zeroerp/zeroerp_backend/settings.py <<'EOF'
# --- Proxy HTTPS/Nginx + cookie sicuri ---
CSRF_TRUSTED_ORIGINS = [f"https://${TAIL_NAME}"]
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
# Static/Media best practice
STATIC_URL = "/static/"; MEDIA_URL = "/media/"
STATIC_ROOT = "/var/www/zeroerp/static"; MEDIA_ROOT  = "/var/www/zeroerp/media"
EOF
```

## 11) Migrazioni + superuser

```bash
set -a; source <(sudo cat /etc/zeroerp/zeroerp.env); set +a
sudo -u $APP_USER bash -lc 'cd ~/apps/zeroerp && source .venv/bin/activate && python manage.py migrate && python manage.py createsuperuser'
systemctl restart zeroerp-gunicorn
```

## 12) UFW finale (solo Tailscale per SSH)

```bash
ufw delete allow 22/tcp || true
ufw allow in on tailscale0 to any port 22 proto tcp
ufw status verbose
```

## 13) Check rapido

```bash
curl -kI https://${TAIL_NAME}/static/admin/css/base.css   # 200 OK
curl -kI https://${TAIL_NAME}/                          # 200/302
systemctl status zeroerp-gunicorn | sed -n '1,5p'
nginx -t
```

## 14) Snapshot Proxmox

```bash
pct snapshot $CTID baseline-$(date +%F) --description "Django ok, HTTPS, UFW, Tailscale"
```
