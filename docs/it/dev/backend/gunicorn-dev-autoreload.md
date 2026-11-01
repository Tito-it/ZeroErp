# Gunicorn in sviluppo — ricarica del codice

> **Ultimo aggiornamento**: 1 novembre 2026
>
> **Destinatari**: chi sviluppa sul backend nella macchina `backend-dev`.
>
> **Vedi anche**:
>
> * [Configurazione Django su backend-dev](configurazione-django.md) — servizio systemd, file d'ambiente, Nginx

---

## Il punto di partenza

Il backend di sviluppo gira come servizio systemd `zeroerp-gunicorn`,
**direttamente sul working tree** (`/home/tid/apps/ZeroErp/backend`), lanciato
da `bin/start-gunicorn.sh`: 3 worker, bind `127.0.0.1:8000`, **senza** ricarica
automatica.

⚠️ Una modifica Python **non è attiva** finché i worker non vengono ricaricati:
il frontend continua a parlare con il codice di prima, senza nessun errore. I
test e gli smoke lanciati con `.venv/bin/python` non se ne accorgono, perché non
passano dal server.

Ci sono due modi per ricaricare. Quello di tutti i giorni è il primo.

## 1. Ricarica a mano, dopo una modifica (consigliato)

Il master di Gunicorn appartiene all'utente `tid`: un `HUP` fa ripartire i
worker con il codice nuovo, senza `sudo` e senza interrompere il servizio.

```bash
kill -HUP $(pgrep -f "gunicorn zeroerp" | head -1)
ps -o pid,lstart,cmd -C gunicorn      # i worker devono avere l'ora di adesso
```

## 2. Ricarica automatica (`--reload`)

`bin/start-gunicorn.sh` legge quattro variabili, tutte con un default:

| Variabile | Default | Effetto |
| --- | --- | --- |
| `ZEROERP_GUNICORN_BIND` | `127.0.0.1:8000` | indirizzo di ascolto. ⛔ Resta **loopback**: vedi la regola 1 di [Configurazione Django](configurazione-django.md) |
| `ZEROERP_GUNICORN_WORKERS` | `3` | numero di worker |
| `ZEROERP_GUNICORN_TIMEOUT` | `60` | timeout di un worker, in secondi |
| `ZEROERP_GUNICORN_RELOAD` | `0` | `1` = `--reload`: i worker ripartono a ogni file Python salvato |

Si accende e si spegne con le funzioni di `backend/bin/dev-guni-aliases.sh`:

```bash
source /home/tid/apps/ZeroErp/backend/bin/dev-guni-aliases.sh
dev-guni-on       # reload + 1 worker, poi restart del servizio
dev-guni-off      # torna al default, poi restart
dev-guni-status
dev-guni-logs     # ultime 80 righe del journal (o: dev-guni-logs 200)
```

Per averle in ogni shell:

```bash
echo "source /home/tid/apps/ZeroErp/backend/bin/dev-guni-aliases.sh" >> ~/.bashrc
```

`dev-guni-on` scrive un drop-in **suo**,
`/etc/systemd/system/zeroerp-gunicorn.service.d/10-dev-reload.conf`, e
`dev-guni-off` cancella solo quello. Richiedono `sudo`.

⛔ **Non usare `systemctl edit` / `systemctl revert`** per questa cosa. Nella
stessa cartella c'è `override.conf`, che porta
`EnvironmentFile=…/backend/.env.systemd`: è da lì che il servizio prende parte
delle variabili. `systemctl revert` cancella **tutti** i drop-in, quindi anche
quello.

⚠️ `--reload` è solo per lo sviluppo: in produzione non si usa.

## Prova rapida

Passando da Nginx, cioè dall'unico ingresso:

```bash
curl -ksi https://192.168.X.8/health
curl -ksi https://192.168.X.8/api/v1/core/diagnostics/error-envelope/   # 401 senza token: il server risponde
```
