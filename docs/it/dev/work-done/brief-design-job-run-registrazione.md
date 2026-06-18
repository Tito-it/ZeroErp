# Design — Registrazione run dei job headless (cron/command) in `job_run_log`

> **Tipo**: documento di design autorevole (lato nostro: modello + piano BE).
> Il cambio schema/funzioni è delegato al team DB →
> [brief-db-job-run-registrazione.md](brief-db-job-run-registrazione.md).
>
> **Data**: 2026-06-17 · **Stato**: 🟢 **COMPLETATO (DB + BE)**. DB: colonne + funzioni
> `script.fn_job_run_*`, pgTAP verdi (vedi [brief DB](brief-db-job-run-registrazione.md)).
> **BE (2026-06-18)**: `apps.core.services.job_run.registered_job` + wiring
> `run_fatturazione_batch` + test (suite core+vendite verde, 1065) — §6.
>
> **Decisioni (2026-06-17)**: **(a)** le funzioni `fn_job_run_start/end` vivono in
> **`script`** (non `maintenance`) — i ruoli batch/app hanno già `USAGE`+`EXECUTE` su
> `script`, niente apertura di `maintenance`; **(b)** `fn_run_and_log` **lasciata
> invariata** (no refactor DRY). Dettagli/razionale: [brief DB §2-§5](brief-db-job-run-registrazione.md).
>
> **Origine**: residuo F5 di [analisi-commesse-stato-e-sviluppi.md](analisi-commesse-stato-e-sviluppi.md)
> §10.4 ("l'esito del *run* del batch è solo su stdout/stderr, non persistito").
> **Vedi anche**: [Guida Tracciamento Processi e Job](/guide/analisi-tracciamento-processi-e-job),
> [brief-db-contesto-sistema-batch-fatturazione-rls.md](brief-db-contesto-sistema-batch-fatturazione-rls.md)
> (il batch gira come ruolo `zeroerp_batch_fatturazione` — §4 qui sotto).

---

## 1. Problema

Il tracciamento processi/job ha **tre livelli** (guida sopra): `dbops.audit_log`
(generico), `maintenance.job_run_log` (esecuzioni **pgAgent**, via `fn_run_and_log`),
`pipeline_task_registry` + `vendite.fatturazione_lotti_task_runs` (task *dentro* la
pipeline). Il batch fatturazione `run_fatturazione_batch` è però un **management command
via systemd/cron** (pgAgent è riservato alla manutenzione DB): registra i task per-lotto
in `fatturazione_lotti_task_runs`, ma **l'esecuzione del job in sé** (il *run* del cron)
**non è registrata da nessuna parte** — solo stdout/stderr. Manca la riga "run-level":
quando è partito, com'è finito, quanti emittenti/falliti.

## 2. Decisione: UNA tabella, non due — `maintenance.job_run_log` generalizzata

`maintenance.job_run_log` è già la tabella "un record per esecuzione di job". Creare una
seconda tabella gemella per i job cron sarebbe un **duplicato** (regola del 2). Decisione
(Tid, 2026-06-17): **riusarla** rendendola **generale per qualunque processo schedulato**,
distinguendo *come* è stato lanciato con una colonna discriminante. La tabella resta
**generica** (qualsiasi job), **non** pensata sulla fatturazione: il dettaglio di dominio
della fatturazione vive già in `vendite.event_log` / `fatturazione_lotti_task_runs` /
`fatturazione_lotti_log` (correlati via `run_uuid`).

### Confine netto

| Livello | Dove | Cosa |
|---|---|---|
| **Run del job** (generico) | `maintenance.job_run_log` | una riga per esecuzione: nome, origine, start/end, esito, riepilogo generico |
| **Dettaglio di dominio** (fatturazione) | `vendite.event_log` + `fatturazione_lotti_task_runs` + `fatturazione_lotti_log` | task per-lotto, fasi, esiti per emittente |

Correlazione: `run_uuid` di `job_run_log` (già esistente, `uuidv7()` default) propagato
nel `meta` dei record di dominio del run.

## 3. Modello — modifiche a `maintenance.job_run_log` (DB)

Due colonne (DDL in [brief DB §2](brief-db-job-run-registrazione.md)):

| Colonna | Tipo | Default | Note |
|---|---|---|---|
| `origine` | `varchar(16)` NOT NULL | `'PGAGENT'` | CHECK ∈ (`PGAGENT`,`CRON`,`COMMAND`). Default = backfill dei record pgAgent esistenti, zero regressione |
| `meta` | `jsonb` NOT NULL | `'{}'` | riepilogo **generico** del run (es. conteggi per esito). MAI dettaglio di dominio fatturazione |

Tutto il resto della tabella è già generico (`jobname`, `started_at`/`ended_at`, `ok`,
`rows_affected`, `message`, `error_code`/`error_detail`, `agent_host`, `run_uuid`).

## 4. Vincolo architetturale: registrazione DENTRO il canale di sistema

`run_fatturazione_batch` gira nel gateway `system_process_context` (RLS Path A): per la
durata del run la connessione `default` è ripuntata al ruolo `zeroerp_batch_fatturazione`.
Due conseguenze che **vincolano il design**:

1. **La registrazione del run deve avvenire DENTRO il `system_process_context`**, sulla
   stessa connessione del batch. Se la facessimo *fuori* (come ruolo web), il gateway
   chiuderebbe quella connessione allo `swap` delle credenziali → un eventuale **advisory
   lock di sessione verrebbe rilasciato** (i lock cadono alla chiusura connessione),
   rompendo l'anti-overlap. Tenendo lock+start+body+end sull'**unica** connessione del
   ruolo batch, il lock vive per tutto il run e cade solo a fine processo (anche su crash).
2. → **il ruolo `zeroerp_batch_fatturazione` deve poter scrivere il proprio run-log.**
   Per **non** allargare il perimetro DML del ruolo a una tabella `maintenance`, le due
   funzioni `fn_job_run_start`/`fn_job_run_end` sono **SECURITY DEFINER** (owner = owner
   DDL, `search_path` fisso): il ruolo batch ha bisogno solo di **`GRANT EXECUTE`** sulle
   funzioni, **nessun DML diretto** su `maintenance.job_run_log`. **Regola generale**:
   ogni ruolo `zeroerp_batch_<job>` futuro avrà solo bisogno dello stesso `EXECUTE` → il
   [brief DB](brief-db-job-run-registrazione.md) lo mette nel pattern di provisioning.
   (Gli advisory-lock di sessione funzionano comunque: appartengono al backend, non al
   ruolo, quindi SECURITY DEFINER non li altera.)

Struttura risultante nel command:

```python
with system_process_context(alias=SYSTEM_FATTURAZIONE_DB_ALIAS, actor=AUDIT_ACTOR_...):
    with registered_job("run_fatturazione_batch:immediata", origine="CRON",
                        lock_key="run_fatturazione_batch:immediata") as job:
        if not job.acquired:
            self.stdout.write("skip: altro run in corso")
            return
        ...corpo batch...
        job.set_meta({"emittenti": n, "falliti": k, "per_motivo": {...}})
```

## 5. Anti-overlap (advisory lock per identità logica)

La corsia immediata gira ogni ~2 min → un run lento può sovrapporsi al tick successivo.
A valle è già **sicuro** (`FOR UPDATE SKIP LOCKED` + guard `fatturato` → niente doppia
fattura); l'anti-overlap è **igiene** (no run paralleli sprecati, log puliti), gratis
riusando l'advisory-lock già in `fn_run_and_log`.

- **Chiave = identità logica del job**, non solo `jobname`: `run_fatturazione_batch:immediata`
  ≠ `:differita` → immediata e differita **non si bloccano a vicenda** (lavori diversi).
- Lock occupato → il run **non aspetta**: esce subito con riga `job_run_log` esito
  "skip" (come fa già `fn_run_and_log`).

## 6. Piano Backend — ✅ FATTO (2026-06-18)

Implementato come da piano sotto: building block
[`apps/core/services/job_run.py`](../../../../backend/apps/core/services/job_run.py)
(`registered_job` + `JobRunHandle`, chiama `script.fn_job_run_start/end`, json.dumps+`::jsonb`
per `meta`) + wiring in
[`run_fatturazione_batch`](../../../../backend/apps/vendite/management/commands/run_fatturazione_batch.py)
(registrazione **dentro** `system_process_context`, dry-run escluso, `_run_batch` ritorna il
riepilogo → `job.set_meta`). Test: `apps/core/tests/services/test_job_run.py` (acquired/skip/
errore) + command (registra + skip). Suite core+vendite verde (1065).


1. **Building block generico** `apps/core/services/job_run.py` — context manager
   `registered_job(job_name, *, origine='CRON', stepname=None, lock_key=None,
   agent_host=None)`:
   - all'ingresso chiama `script.fn_job_run_start(...)` → `{id, run_uuid, acquired}`;
     se `acquired=False` (lock occupato) la riga "skip" è già loggata a DB e il CM espone
     `job.acquired=False` (il caller salta il corpo);
   - espone `job.run_uuid` (per correlare i log di dominio) e `job.set_meta(dict)`;
   - all'uscita chiama `script.fn_job_run_end(id, ok, message, rows, error_code,
     error_detail, meta)`: `ok=False` + `error_*` se è uscito per eccezione, poi rilancia.
   Riusabile da **qualsiasi** futuro command/cron (no accoppiamento fatturazione).
2. **Integrazione in `run_fatturazione_batch`**: avvolgere il corpo (dentro
   `system_process_context`, §4). `job_name`/`lock_key` = `run_fatturazione_batch:<modalita>`.
   `meta` = riepilogo generico (emittenti processati/falliti, conteggi per `motivo_stop`).
   In `--dry-run`: registrare comunque il run con `origine='COMMAND'`? No — il dry-run non
   è un'esecuzione operativa: **niente registrazione** (solo discovery/stdout).
3. **Test** (mock cursor/funzioni): start→end happy path scrive CRON+meta; lock occupato →
   `acquired=False`, corpo saltato; eccezione → `fn_job_run_end(ok=False, error_*)` + rilancio.

## 7. Rollout / ordine

DB (2 colonne + 2 funzioni start/end **in `script`** + pgTAP; `fn_run_and_log` **invariata**;
nessun GRANT nuovo — il ruolo batch ha già `EXECUTE` su `script`) → BE (`registered_job` +
wiring command + test) →
DOC (aggiornare la [guida processi e job](/guide/analisi-tracciamento-processi-e-job):
`job_run_log` da "esecuzioni pgAgent" → "esecuzioni job schedulati: pgAgent + cron/command",
colonna `origine`, le 2 nuove funzioni).

Backfill: i record esistenti restano `origine='PGAGENT'` → semantica identica a oggi.

## 8. Criteri di accettazione (end-to-end)

- Un `run_fatturazione_batch` reale lascia **una riga** in `maintenance.job_run_log` con
  `origine='CRON'`, `started_at`/`ended_at`, `ok`, `meta` col riepilogo, `run_uuid`
  correlabile ai record di dominio in `vendite`.
- Due run sovrapposti della stessa corsia: il secondo esce "skip" (lock), riga loggata.
- Run immediata e differita in parallelo: **entrambi** procedono (lock-key diversi).
- I job pgAgent esistenti restano invariati (`origine='PGAGENT'`, `fn_run_and_log`).
- Nessun dettaglio di dominio fatturazione finisce in `job_run_log` (resta in `vendite`).
