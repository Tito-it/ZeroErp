# 🧩 Zero ERP — Backend-dev (LXC) — Post-Upgrade Checklist

> 📄 **Scopo principale**
> Documento operativo per la verifica e manutenzione del container **`backend-dev`** (LXC Debian 13) dopo l'upgrade del sistema e l'allineamento dell'ambiente Django + Gunicorn + Nginx.

---

## ✅ Stato generale

| Componente     | Versione / Stato                            | Esito |
| -------------- | ------------------------------------------- | ----- |
| **Debian**     | 12 → 13 (Trixie)                            | ✔️    |
| **Python**     | pyenv 3.13.1 + venv dedicata                | ✔️    |
| **Django**     | 5.2.7                                       | ✔️    |
| **Gunicorn**   | systemd attivo (`zeroerp-gunicorn.service`) | ✔️    |
| **Nginx**      | HTTPS + reverse proxy                       | ✔️    |
| **PostgreSQL** | remoto su `dbdev` (v17, client 18)          | ✔️    |
| **Tailscale**  | connesso (`backend-dev.tailXXXX.ts.net`)    | ✔️    |

---

## 🧱 Percorsi e configurazioni principali

| Ambito          | Path / File                                                          | Note                                     |
| --------------- | -------------------------------------------------------------------- | ---------------------------------------- |
| App Django      | `/home/tid/apps/ZeroErp/backend`                                     | Contiene `manage.py`, `zeroerp_backend/` |
| Virtualenv      | `/home/tid/apps/ZeroErp/backend/.venv`                               | Python 3.13 con Django e Gunicorn        |
| Env file        | `/etc/zeroerp/zeroerp.env`                                           | Proprietario `root:tid`, permessi `640`  |
| Static/Media    | `/var/www/ZeroErp/static`, `/var/www/ZeroErp/media`                  | Proprietario `tid:tid`, permessi `755`   |
| Systemd         | `/etc/systemd/system/zeroerp-gunicorn.service`                       | Puntamento corretto `.venv/bin/gunicorn` |
| Nginx           | `/etc/nginx/sites-available/zeroerp`                                 | Alias aggiornati a `/var/www/ZeroErp`    |
| Certificato SSL | `/etc/ssl/certs/backend-dev.crt`, `/etc/ssl/private/backend-dev.key` | Self-signed per sviluppo                 |

---

## 🔄 Verifiche rapide

```bash
# Gunicorn + Django
sudo systemctl status zeroerp-gunicorn

# Nginx + HTTPS
curl -kI https://localhost/static/admin/css/base.css

# DB connectivity
sudo -u postgres psql -h 100.114.x.x -U zeroerp_app -d <dbname> -c "SELECT 'ok';"

# Redis (cache/sessioni)
sudo systemctl status redis-server
```

---

## 💾 Backup e snapshot

### 🧠 Snapshot Proxmox

```bash
pct snapshot 102 "post-upgrade-django-ok"
```

### 🗄️ Backup giornaliero

Verifica che lo storage `nas-backup` includa anche CT `102 (backend-dev)` nel file `/etc/pve/storage.cfg`.

### 🧩 Backup configurazioni interne

```bash
tar -czf /root/backend-configs-$(date +%F).tar.gz \
    /etc/zeroerp /etc/nginx/sites-available/zeroerp \
    /etc/systemd/system/zeroerp-gunicorn.service \
    /home/tid/apps/ZeroErp/backend/zeroerp_backend/settings.py
```

---

## 🧹 Pulizia post-upgrade

```bash
sudo apt autoremove --purge
sudo apt clean
sudo journalctl --vacuum-time=10d
```

---

## ⚙️ Manutenzione consigliata

* Aggiorna pacchetti Python nel venv:

  ```bash
  source ~/apps/ZeroErp/backend/.venv/bin/activate
  pip install -U pip django gunicorn psycopg[binary] redis djangorestframework
  deactivate
  ```

* Se rinomini directory (es. `ZeroErp` → `zeroerp`):

  * aggiorna `WorkingDirectory` e `ExecStart` in systemd;
  * aggiorna gli alias static in Nginx;
  * verifica i percorsi nei comandi di deploy e backup.

* Controlli periodici:

  ```bash
  tailscale status
  sudo systemctl list-units --failed
  ```

---

## 🔍 Test end-to-end

1. Accesso via HTTPS Tailscale → `https://backend-dev.tailXXXX.ts.net/admin`
2. Login Django Admin → verifica CSS statici
3. Query PostgreSQL → verifica connessione remota
4. Test Redis cache/sessioni (`python manage.py shell` → test cache)

---

## 🧭 Vedi anche

* 🧩 [Play-book Operativo Backend](/dev/backend/play-book-operativo-backend)
* 🗃️ [Configurazione PostgreSQL VM dbdev](/dev/db/dbdev.md)
* 🔐 [Sicurezza Django e Proxy HTTPS](../sicurezza-django-proxy.md)

---

> 📌 **Nota**: eseguire un nuovo snapshot dopo ogni aggiornamento Django o modifica alla configurazione di Gunicorn/Nginx per garantire rollback rapido in caso di errore.
