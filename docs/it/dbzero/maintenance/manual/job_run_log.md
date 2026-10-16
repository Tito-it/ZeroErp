## 📚 Documentazione Tabella: `maintenance.job_run_log`

> 👀 **Vedi anche:**
>
Approfondimento tabelle:
>
`maintenance.job_definitions` *(riferimento ipotetico: la tabella non esiste)*
>
Approfondimento funzioni/procedure:
>
[maintenance.fn_run_and_log](/dbzero/maintenance/funzioni/fn_run_and_log)
> [script.fn_job_run_start](/dbzero/script/funzioni/fn_job_run_start)
> [script.fn_job_run_end](/dbzero/script/funzioni/fn_job_run_end)
> [maintenance.proc_apply_storicizza_defaults_job](/dbzero/maintenance/funzioni/proc_apply_storicizza_defaults_job)

---
### 🎯 Scopo Principale
(latest review 18-06-2026)
La tabella `maintenance.job_run_log` memorizza i log di esecuzione dei job schedulati o lanciati manualmente all’interno del sistema Zero ERP.
Ogni riga rappresenta una singola esecuzione di un job, includendo informazioni di stato, tempi di inizio/fine, eventuali errori e dettagli di esecuzione.

È la tabella **generica** "un record per esecuzione di job" per **qualsiasi** processo
schedulato: job **pgAgent** (lato DB) *e* **job headless cron/command** (management
command Django via systemd, es. `run_fatturazione_batch`). La colonna **`origine`**
distingue la sorgente del lancio; la colonna **`meta`** porta un riepilogo *generico* del
run. Il dettaglio di dominio NON vive qui (es. la fatturazione lo tiene in `vendite.*`,
correlato via `run_uuid`).

---

### Vincoli e Relazioni

* **`job_run_log_pkey`**: Chiave primaria su `id`.
* **Relazioni logiche** (non vincolate da FK nel DDL):

  * Possibile collegamento con tabella di definizione job (`maintenance.job_definitions`).
  * Utilizzata da funzioni di logging automatico (`maintenance.fn_run_and_log`).

---

### Colonne discriminanti `origine` e `meta`

* **`origine`** (`varchar(16)` NOT NULL, default `'PGAGENT'`, CHECK
  `chk_job_run_log_origine`): come è stato lanciato il run.
  * `PGAGENT` — job DB pgAgent (default; backfill dei record storici, semantica identica a prima).
  * `CRON` — management command schedulato (systemd/cron), es. `run_fatturazione_batch`.
  * `COMMAND` — lancio manuale di un command.
* **`meta`** (`jsonb` NOT NULL, default `'{}'`): riepilogo **generico** del run (es. conteggi
  per esito). **Mai** dettaglio di dominio (resta nei domini, correlato via `run_uuid`).

### ⭐ Rev 2026-09-04 — chi è che sta girando

Il giornale registrava da sempre **che** qualcosa era girato. Non registrava
**chi**: un run era una riga senza autore, e in un sistema multi-azienda questa
è una domanda che prima o poi qualcuno fa.

| colonna | Che cosa dice |
| --- | --- |
| `processo_codice` | quale processo di [dbops.processi](/dbzero/dbops/manual/processi) sta girando (**hard FK**: un codice inventato viene respinto) |
| `auth_user_id` | l'utente tecnico con cui gira, quando ne ha uno |

⚠️ **`auth_user_id` non è l'operatore per-item della coda.** Quello sta già in
`coda_lavori.scope`, ed è un'altra cosa: qui c'è l'identità del **processo**,
là c'è la persona che ha chiesto un singolo lavoro.

⭐ **I dodici job notturni si sono dichiarati senza toccare lo scheduler.** Il
codice del processo non viene passato come parametro: si **deriva dal nome del
job**, perché per convenzione le due stringhe coincidono. Chi vuole essere
esplicito passa comunque il parametro, che vince.

⇒ Il presidio [dbops.vw_run_senza_attore](/dbzero/dbops/manual/vw_run_senza_attore)
conta chi non si è ancora dichiarato — guardando l'**ultima** corsa, non lo
storico: le righe vecchie hanno l'autore vuoto per sempre e non sono sanabili.

### ⭐ Rev 2026-10-10 — una corsa saltata non è una corsa riuscita

Quando il lock della corsia è occupato il lavoro non parte, ma il giornale ne
tiene traccia: la sveglia c'è stata. Fino al 2026-10-10 quella riga nasceva con
`ok = true`, e l'unica cosa che la distingueva da una corsa vera era il **testo**
del `message`. Ogni lettore la contava come riuscita.

| colonna | sulla riga saltata |
| --- | --- |
| `saltata` | `true` (`boolean NOT NULL DEFAULT false`) |
| `ok` | `NULL`: non ha fatto lavoro, quindi non ha esito |
| `ended_at` | valorizzato: nasce già chiusa |

Il CHECK `chk_job_run_log_saltata` tiene insieme le tre cose. La scrivono solo i
due rami del lock occupato, in `fn_job_run_start` e `fn_run_and_log`, e
`fn_job_run_end` rifiuta di chiuderla (`E_JOB_RUN_SALTATA_NON_CHIUDIBILE`).

⭐ **Che cosa ne fa chi legge** dipende dalla domanda:

| domanda | la riga saltata | dove |
| --- | --- | --- |
| «il lavoro è riuscito?» | si scarta da sola (`ok IS TRUE`) | ogni lettore |
| «qual è l'ultima corsa **vera**?» | esclusa | [vw_job_run_da_guardare](/dbzero/maintenance/manual/vw_job_run_da_guardare), `ultimo_esito` di [vw_processi_programmazione](/dbzero/dbops/manual/vw_processi_programmazione) |
| «la sveglia è viva?» | **contata**: prova che il timer si è svegliato | `giornale_ultima_corsa` e `giornale_ultima_corsa_pgagent` di vw_processi_programmazione |

⛔ Il testo `'skip: another run in progress'` resta nel `message` per chi legge il
giornale, ma non è il marcatore: un filtro sul testo sarebbe una seconda sede
della stessa regola.

⚠️ Le skip scritte prima del 2026-10-10 hanno `saltata = false` e `ok = true`:
non sono state bonificate (decisione di Tid).

Brief: `brief-db-corsa-saltata-non-e-una-corsa`.

---

### Percorsi di scrittura

* **pgAgent** → [`maintenance.fn_run_and_log`](/dbzero/maintenance/funzioni/fn_run_and_log)
  (avvolge un blocco SQL). Invariata.
* **Job headless (cron/command)** → [`script.fn_job_run_start`](/dbzero/script/funzioni/fn_job_run_start)
  + [`script.fn_job_run_end`](/dbzero/script/funzioni/fn_job_run_end): spezzano start/end
  attorno a un corpo job **Python**. `SECURITY DEFINER` (i ruoli batch headless non hanno
  DML diretto sulla tabella, solo `EXECUTE`). Advisory lock di sessione opzionale per
  anti-overlap fra run dello stesso job (per `lock_key`).
* **Canale fuori transazione** (il run che fallisce) → `zeroerp_log`, che ha il
  solo `INSERT` (`90_end/20260905-38`).

### ⭐ Rev 2026-10-16 — il codice dell'errore e lo SQLSTATE, separati

* **`sqlstate`** — il codice del database per l'errore che ha fermato la corsa
  (cinque caratteri), quando l'errore è passato dal database. Vuoto per una corsa
  riuscita e per un errore che il database non ha visto. Le prime due cifre dicono se
  il guasto è dell'ambiente: è ciò che legge
  [`vw_job_run_da_guardare`](/dbzero/maintenance/manual/vw_job_run_da_guardare) per la
  causa.
* **`error_code`** — resta «il codice più preciso che chi scrive ha»: il codice di
  dominio (`E_…`) o del backend, e in mancanza lo SQLSTATE o il nome dell'eccezione.

Lo scrivono le tre porte: `fn_run_and_log` (che da oggi mette in `error_code` il codice
di dominio invece di `P0001`), il verbale fuori transazione `fn_job_run_log_failure` e
`script.fn_job_run_end` (parametro `p_sqlstate`, che il backend deve passare). Le righe
di prima sono state convertite dalla forma di `error_code`; il codice di dominio delle
vecchie righe `P0001` non si recupera.

### Chi legge, chi scrive — la postura di `zeroerp_app` *(rev 2026-09-19)*

Il ruolo applicativo **legge** questo giornale e **non lo scrive**:

| Privilegio | `zeroerp_app` | Perché |
| --- | --- | --- |
| `USAGE` sullo schema | sì | risolvere i nomi (e il presidio dei riferimenti morti) |
| `SELECT` sulla tabella e su `vw_job_run_da_guardare` | sì | lista dei processi automatici e corse di un processo, riepilogo giri e liveness, esiti delle corsie di fatturazione, `job_liveness` nel digest — cinque lettori nel backend |
| `INSERT`, `UPDATE`, `DELETE` | **no** | la porta di scrittura sono le due funzioni `SECURITY DEFINER` qui sopra; un giornale non si cancella |

Sede: `scripts/sql/provision_zeroerp.sql`, fase `post` (blocco `maintenance`, in fondo) e il
changeSet gemello `90_end/20260919-08` per i database già provisionati.
`maintenance` **non** entra nella whitelist del provisioning, che darebbe SIUD
pieno. Presidio: `db/pgtap/maintenance/test-app-postura-job-run-log-v1.sql`.

⚠️ Fino al 2026-09-19 il `SELECT` esisteva **solo sul database di sviluppo**,
dato a mano, e il provisioning diceva «l'app non ne legge né scrive le
tabelle». È emerso quando i test Django in CI sono passati a connettersi come
`zeroerp_app`: sedici rossi su `list_processi`/`list_job_runs`. Regola:
[linee-guida-sql §11.9](/linee-guida-sql) — un privilegio che esiste su una
sola macchina è un ricordo, non una configurazione.

### Considerazioni di Progettazione

* Permette la **tracciabilità completa** delle esecuzioni, con dettagli utili per debug e audit.
* Il campo `run_uuid` consente di correlare log multipli appartenenti alla stessa sessione o esecuzione — e di **agganciare i record di dominio** del run (es. `vendite.*` per la fatturazione).
* La colonna `agent_host` è utile per identificare l’host sorgente in scenari multi-server o distribuiti.

---

### 🚨 Gestione Errori e Audit

* Gli errori vengono registrati nei campi `error_code` ed `error_detail`, mantenendo in `message` un testo più leggibile per l’operatore.
* Integrazione con funzioni di logging standard (`fn_run_and_log`) per assicurare uniformità nella raccolta dei dati.

---

> **“Questa tabella rappresenta il cuore del sistema di tracciamento dei job, fornendo una base solida per l’analisi delle esecuzioni e la diagnosi dei problemi.”**

---

{% include-markdown "signature-core.md" %}
