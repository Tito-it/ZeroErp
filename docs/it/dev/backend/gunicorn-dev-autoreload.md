# Gunicorn dev autoreload (backend-dev)

Note rapide per usare `zeroerp-gunicorn` in sviluppo con reload automatico.

## Quando usarlo
- Ambiente sviluppo su `backend-dev`
- Accesso da browser via `https://192.168.X.8/` (nginx davanti)

## Come attivarlo
```bash
sudo systemctl edit zeroerp-gunicorn.service
```

Inserire:
```ini
[Service]
Environment=ZEROERP_GUNICORN_RELOAD=1
Environment=ZEROERP_GUNICORN_BIND=127.0.0.1:8000
Environment=ZEROERP_GUNICORN_WORKERS=1
```

Poi:
```bash
sudo systemctl daemon-reload
sudo systemctl restart zeroerp-gunicorn.service
sudo systemctl status zeroerp-gunicorn.service --no-pager
```

## Test rapido
```bash
curl -ki "https://192.168.X.8/api/core/diagnostics/error-envelope/"
```

## Come disattivarlo
```bash
sudo systemctl revert zeroerp-gunicorn.service
sudo systemctl daemon-reload
sudo systemctl restart zeroerp-gunicorn.service
```

## Alias pronti (consigliato)
Script helper disponibile in:
- `backend/bin/dev-guni-aliases.sh`

Carica funzioni shell:
```bash
source /home/tid/apps/ZeroErp/backend/bin/dev-guni-aliases.sh
```

Comandi:
```bash
dev-guni-on
dev-guni-off
dev-guni-status
dev-guni-logs
```

Persistenza in `~/.bashrc`:
```bash
echo "source /home/tid/apps/ZeroErp/backend/bin/dev-guni-aliases.sh" >> ~/.bashrc
```

## Note
- Lo script `backend/bin/start-gunicorn.sh` supporta variabili:
  - `ZEROERP_GUNICORN_RELOAD`
  - `ZEROERP_GUNICORN_BIND`
  - `ZEROERP_GUNICORN_WORKERS`
  - `ZEROERP_GUNICORN_TIMEOUT`
- In produzione evitare `--reload`.
