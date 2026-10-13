# Servizi ZeroERP — i comandi

Foglio pratico per il **server backend**: quali servizi systemd ha ZeroERP e con
quali comandi si accendono, si spengono e si guardano. Come si **installano** sta
nel [Playbook operativo](play-book-operativo-backend.md) §8 (Gunicorn) e §15-16
(timer e servizi).

> ⚠️ Gli unit si cambiano sui **template** in `backend/deploy/systemd/`, mai in
> `/etc/systemd/system`: `install-timers.sh` riscrive tutto a ogni giro.

## I servizi

Ci sono due tipi di unit, e si comandano in modo diverso:

* **sempre acceso** (`.service`): gira di continuo. Si fa `start`/`stop`/`restart`
  sul `.service`;
* **a sveglia** (`.timer` + `.service`): il **timer** sveglia il `.service`, che
  fa un giro e si chiude. Si accende o si spegne il **`.timer`**; il `.service`
  si lancia a mano solo per una corsa di prova.

| Unit | Tipo | Cosa fa | Se lo fermi |
| --- | --- | --- | --- |
| `zeroerp-gunicorn` | sempre acceso | il backend (API) | l'applicazione non risponde |
| `zeroerp-listen-permessi` | sempre acceso | tiene allineata la cache dei permessi (LISTEN/NOTIFY) | i permessi cambiati non arrivano finché non riparte; il presidio dei processi si accende con `SERVIZIO_GIU` |
| `zeroerp-coda-lavori` | sveglia, ogni minuto | esegue la coda dei lavori, compreso «Esegui ora» | «Esegui ora» e i lavori accodati restano fermi |
| `zeroerp-coda-stampa` | sveglia, ogni 2 minuti | produce i PDF in coda | le stampe restano in coda |
| `zeroerp-send-pending-emails` | sveglia, ogni 5 minuti | spedisce le email in coda | le email restano in coda |
| `zeroerp-digest-presidi-giornaliero` | sveglia, ogni giorno dalle 07:00 | la mail dei presidi | nessuna mail di allarme |
| `zeroerp-digest-presidi-settimanale` | sveglia, il lunedì dalle 07:30 | la mail settimanale (registri, battito) | nessuna mail settimanale |
| `zeroerp-fatturazione-immediata` | sveglia, **spenta di default** | giro di fatturazione immediata | — |
| `zeroerp-fatturazione-differita` | sveglia, **spenta di default** | giro di fatturazione differita | — |
| `zeroerp-smoke-notturno` | sveglia, **spenta di default**, si accende **solo su sviluppo** | il giro notturno di tutti gli smoke (alle 02:30); una regressione arriva nella mail delle 07:00 | gli smoke tornano a dipendere da chi si ricorda di lanciarli |

⛔ I due timer di **fatturazione emettono documenti**: si accendono solo su un
host dichiarato pronto, mai «per prova».

⚠️ Questa tabella **descrive** il deploy e non lo sostituisce: cadenze, comandi e
cosa è acceso stanno in [`backend/deploy/sveglie.json`](../../../../backend/deploy/sveglie.json)
(Gunicorn no: si installa a parte). Quello che c'è davvero sulla macchina si vede con:

```bash
systemctl list-units 'zeroerp-*' --all     # tutti gli unit, con lo stato
systemctl list-timers 'zeroerp-*'          # le sveglie: ultima e prossima corsa
```

## I comandi

Al posto di `<unit>` va il nome della tabella, per esempio `zeroerp-listen-permessi`.

| Voglio… | Comando |
| --- | --- |
| vedere se gira | `systemctl status <unit>` |
| accendere | `sudo systemctl start <unit>` |
| spegnere | `sudo systemctl stop <unit>` |
| riavviare | `sudo systemctl restart <unit>` |
| accenderlo anche al riavvio della macchina | `sudo systemctl enable --now <unit>` |
| spegnerlo e non farlo ripartire al riavvio | `sudo systemctl disable --now <unit>` |
| leggere il log (ultime 50 righe) | `journalctl -u <unit> -n 50 --no-pager` |
| seguire il log dal vivo | `journalctl -u <unit> -f` |
| log da un'ora precisa | `journalctl -u <unit> --since "2026-10-10 18:00"` |

Per le **sveglie** il nome cambia secondo cosa si vuole:

```bash
sudo systemctl stop    zeroerp-coda-lavori.timer      # niente più sveglie (finché non lo riaccendi)
sudo systemctl start   zeroerp-coda-lavori.timer      # le sveglie ripartono
sudo systemctl start   zeroerp-coda-lavori.service    # UNA corsa adesso, a mano
```

## Ricette

**Ho cambiato codice Python** → Gunicorn non si ricarica da solo. Senza `sudo`:

```bash
kill -HUP $(pgrep -f "gunicorn zeroerp" | head -1)
```

I worker ripartono col codice nuovo e il servizio non si interrompe
(dettagli: [Gunicorn dev autoreload](gunicorn-dev-autoreload.md)). `systemctl reload`
**non** funziona: l'unit non dichiara un comando di reload. In alternativa:
`sudo systemctl restart zeroerp-gunicorn`.
⚠️ Anche il listener e i timer usano il codice Python: dopo una modifica che li
riguarda, `sudo systemctl restart zeroerp-listen-permessi` (i timer leggono il
codice nuovo alla corsa successiva).

**Fermare e riaccendere un servizio per provare un presidio** (collaudo):

```bash
sudo systemctl stop  zeroerp-listen-permessi   # il presidio dei processi si accende
sudo systemctl start zeroerp-listen-permessi   # e si spegne
```

**Dopo un riavvio di PostgreSQL** → il listener si riconnette da solo
(`Restart=always`): controlla con `systemctl status zeroerp-listen-permessi`.

**Lanciare un comando Django come lo lancerebbe un timer**, senza systemd:

```bash
cd /home/tid/apps/ZeroErp/backend
set -a && . ./.env.systemd && set +a
.venv/bin/python manage.py digest_presidi --cadenza giornaliera --secco
```

`--secco` (solo per il digest) compone la mail e la stampa, senza inviarla e senza
registrare la corsa.

**Fermare tutto ZeroERP** (manutenzione):

```bash
sudo systemctl stop 'zeroerp-*.timer' zeroerp-listen-permessi zeroerp-gunicorn
# … e per ripartire:
sudo systemctl start zeroerp-gunicorn zeroerp-listen-permessi
sudo /home/tid/apps/ZeroErp/backend/bin/install-timers.sh   # riaccende i timer giusti
```

⚠️ Per ripartire si usa `install-timers.sh` e non `start 'zeroerp-*.timer'`: lo
script accende **solo** i timer dichiarati accesi in `sveglie.json`, e lascia
spenti quelli della fatturazione.

**Una corsa è andata bene?** Il giornale delle corse, sul DB:

```sql
SELECT jobname, origine, ok, message, started_at
  FROM maintenance.job_run_log ORDER BY id DESC LIMIT 10;
```

Oppure dall'applicazione: **Processi automatici**.
