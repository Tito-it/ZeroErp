# Brief — Riproducibilità deploy worker (unit systemd versionati + validazione CI)

> **Tipo**: brief infra/BE (piano eseguibile, NON azione DB) · **Target**:
> `dev/backend-tid` · **Data**: 2026-07-21 · **Owner**: BE · **Priorità**: media (toglie le
> «istruzioni a mano» dal deploy dei worker; non blocca funzionalità).
> **Stato**: 🟢 **REALIZZATO (2026-07-21, working tree, non committato)** — Parte 1
> (4 template versionati in `backend/deploy/systemd/` + `install-timers.sh` renderizza,
> zero heredoc duplicati) e Parte 2 (job CI `validate-deploy` in `ci-validate.yaml`:
> `bash -n`+`shellcheck` su `backend/bin/*.sh` + `systemd-analyze verify` sugli unit
> renderizzati). Tutto **simulato verde in locale** (shellcheck severità piena, verify
> exit 0, render == heredoc precedente). Playbook §16 riscritto sui template. Aperti:
> commit + prima run CI reale su push; `sudo install-timers.sh` su host pulito = azione
> runtime di Tid.
>
> Contesto: worker DRAINER della Fase C (`draina_coda_lavori`, `draina_coda_stampa`)
> deployati via systemd timer (playbook §16). Vedi anche `play-book-operativo-backend.md`
> §16 e il wrapper `backend/bin/run-command.sh` + installer `backend/bin/install-timers.sh`.

## 1. Problema

Gli **unit systemd** dei worker vivono in `/etc/systemd/system/*` (config per-host,
**fuori dal repo**). Un nuovo host — o un rebuild — non li ha: il deploy dipende da
istruzioni scritte a mano. È **l'unico** pezzo della catena non versionato.

Cosa è **già** riproducibile (per chiarezza, non va toccato):

| Pezzo | Dove | Riproducibile |
| --- | --- | --- |
| GRANT ruolo batch (incl. coda stampa + render) | `scripts/sql/provision_db_role_batch_fatturazione.sql` (CI lo esegue) | ✅ |
| Schema coda + tipi + `fn_accoda_lavoro` | migration Liquibase `20260720-07..10` | ✅ |
| Codice worker (command + core coda) | repo `apps/core/services/coda_lavori/`, command | ✅ |
| Wrapper `run-command.sh` + installer `install-timers.sh` | `backend/bin/` | ✅ (committabili) |
| **Unit systemd installati** | `/etc/systemd/system/` | ❌ **buco** |

> Nota: la CI **non è un host di runtime** — non esegue i timer. «Coprirli con la CI»
> significa **validarne la correttezza**, non eseguirli (vedi §3).

## 2. Parte 1 — Unit come template versionati (unica fonte di verità)

1. Committare i 4 unit come **template** nel repo:
   `backend/deploy/systemd/zeroerp-coda-lavori.service` · `.timer` ·
   `zeroerp-coda-stampa.service` · `.timer`. File reali, reviewabili in PR, con
   **placeholder** per i valori per-host (`__APP_DIR__`, `__APP_USER__`, `__ONCALENDAR__`).
2. Rifattorizzare `backend/bin/install-timers.sh` perché **renderizzi i template**
   (sostituzione placeholder → copia in `/etc/systemd/system`) invece di generarli con
   heredoc inline. Così la definizione degli unit vive **in un solo posto** (i template),
   non duplicata tra script e playbook.
3. Il playbook §16 resta la doc, ma i blocchi heredoc diventano un **riferimento** che
   punta ai template versionati (o si rimuovono, lasciando solo «esegui `install-timers.sh`»).

Effetto: provisioning worker = **un comando versionato** (`sudo backend/bin/install-timers.sh`),
zero istruzioni a mano; le modifiche agli unit passano da PR come qualsiasi codice.

## 3. Parte 2 — Step CI di validazione (`ci-validate.yaml`)

Aggiungere un job/step leggero che **valida gli artefatti di deploy** (non li esegue):

* `bash -n` + **`shellcheck`** su `backend/bin/*.sh` (wrapper, installer) → sintassi/lint
  degli script;
* **`systemd-analyze verify`** sui template `backend/deploy/systemd/*.service|*.timer`
  (con placeholder sostituiti da valori fittizi) → un unit malformato **fallisce in CI**
  prima di raggiungere un host.

È il senso utile di «coperti dalla CI»: garanzia di validità, non esecuzione.

## 4. Fuori perimetro (decisione futura)

* **Docker/produzione**: i timer systemd non vivono nei container. Se un giorno il deploy
  passa all'immagine Docker (oggi il `Dockerfile` è **web-only**, `CMD gunicorn`), i worker
  diventano un **container-sidecar** con loop (`while true; do manage.py draina_coda_lavori;
  sleep 60; done`), un **k8s CronJob**, o un cron di compose (es. ofelia). In quel caso
  valutare anche una modalità `--loop` del command. Decisione separata, legata a come sarà
  la produzione — non necessaria per l'assetto systemd attuale.

## 5. Accettazione (DoD)

* [x] 4 template unit in `backend/deploy/systemd/`, con placeholder per-host
      (`__APP_DIR__`/`__APP_USER__`/`__ONCALENDAR__`).
* [x] `install-timers.sh` renderizza i template (heredoc inline rimossi; nessuna
      definizione unit duplicata) + modalità `--render-only <DIR>` per la CI.
* [~] `sudo backend/bin/install-timers.sh` su host pulito installa+abilita `coda-lavori`
      (e scrive `coda-stampa` disabilitato): **render byte-equivalente all'heredoc
      precedente verificato** (comportamento invariato) → il `sudo` reale su host è
      azione runtime di Tid, non eseguibile in CI/agent.
* [x] Step CI in `ci-validate.yaml` (job `validate-deploy`): `bash -n`/`shellcheck` +
      `systemd-analyze verify` — **simulati verdi in locale**; prima run reale al push.
* [x] Playbook §16 aggiornato: i template sono la fonte, gli heredoc §16.1/16.2 sostituiti
      da un riferimento ai template + note CI.
