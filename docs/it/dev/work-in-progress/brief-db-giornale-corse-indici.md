# Brief DB — Il giornale delle corse senza indici di lettura

## ⏭️ Chi riparte — aggiornato al 2026-11-22

**Riparte: team DB** (`dev/db-tid`). La richiesta è chiusa (§3); la **forma** degli indici la decide il
team DB, il brief porta solo le chiavi di accesso del backend.

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | ✅ sessione BE | Il caso, le chiavi di lettura del backend | §1-§2 | — |
| 2 | **team DB** ⏭️ | Gli indici, la verifica dei piani, la doc | §3-§4 | 1 |
| 3 | team BE/FE | Niente: nessuna ricaduta (§5) | — | — |

> **Chi scrive:** sessione BE (`dev/backend-tid`), 2026-11-22. **A chi:** team DB.
> **Origine:** revisione della doc API di `maintenance` ([api_tracciamento.md](../../backend/core/manual/api_tracciamento.md)),
> che affermava «gli indici DB esistenti coprono i pattern di accesso». Per `dbops.audit_log` è vero, per
> `maintenance.job_run_log` no. Tid, 2026-11-22: brief separato.
> **Brief vicini verificati:** nessun brief aperto in `work-in-progress/` tocca `job_run_log`.

## 1. Il caso

`maintenance.job_run_log` ha **un solo indice**, la chiave primaria `job_run_log_pkey (id)` (doc DB
[job_run_log](/dbzero/maintenance/tabelle/job_run_log), 2026-11-22).

Sul modello:

* è un **giornale append-only senza ritenzione**: una riga per corsa o per passo, di ogni lavoro
  automatico, e nella doc DB nessuno la cancella. Cresce per costruzione;
* chi lo legge lo legge **per chiave** (corsia, processo) e **per recenza** (l'ultima corsa, le corse da
  una data): nessuna lettura del backend vuole la tabella intera.

Senza indici, ogni lettura per chiave è una scansione dell'intero giornale, e il costo cresce con la storia,
non con la domanda. Alcune di queste letture girano **a ogni sveglia** (`e_dovuto`, l'`ExecCondition` dei
timer) e **a ogni lettura dello stato dei worker** (badge code in topbar).

⚠️ C'è anche la FK `fk_job_run_log_processi (processo_codice)` senza indice di supporto, in un progetto che
ha la sua policy degli indici FK (`dbops.apply_fk_index_policy`). Se è un'esclusione voluta va bene, ma
dalla doc non si capisce: lo verifica il team DB.

## 2. Le chiavi di lettura del backend

Tutte da `apps/core/db/maintenance_repository.py` e `apps/core/db/processi_repository.py`. Sono le
**forme** delle query, non dei carichi.

| # | Chi | Filtro | Ordine |
| --- | --- | --- | --- |
| L1 | `list_job_runs` (`GET core/tracciamento/job-runs/`) | facoltativi: `jobname =`, intervallo su `started_at` | `started_at DESC, id DESC`, `LIMIT/OFFSET` |
| L2 | `cte_corse` → `job_liveness(jobnames=…)` (badge code, digest presidi) | `jobname = ANY(…)` | `DISTINCT ON (jobname) … ORDER BY jobname, started_at DESC, id DESC`, due volte: tutte le righe, e le sole `ended_at IS NOT NULL AND NOT saltata` |
| L3 | `cte_corse` → `job_liveness(processo_codice=…)` | `processo_codice =` | come L2 (per jobname, dentro il processo) |
| L4 | `cte_corse` + `GROUP BY jobname` → `list_job_summary` (`job-summary`, pannello esiti fatturazione) | nessuno, oppure `jobname LIKE '<prefisso>%'` e un'espressione sul mese di `started_at` / `meta ->> chiave` | come L2 |
| L5 | `corsa_riuscita_dal` / `corsa_chiusa_dal` (`e_dovuto`, a ogni sveglia) | `jobname = AND started_at >= AND ok` / `ok IS NOT NULL` | — (`EXISTS`) |
| L6 | `list_run_processo` (`GET amm-software/processi/{codice}/run/`) | `processo_codice =` | `started_at DESC, id DESC`, `LIMIT/OFFSET` |
| L7 | `list_processi` (`GET amm-software/processi/`): dal 2026-11-22 `cte_corse(chiave="processo_codice")` più un `count(*) … GROUP BY processo_codice`, non più una `LATERAL` per processo | `processo_codice IS NOT NULL`, **nessun** filtro di processo: il giornale intero, una riga per processo | `DISTINCT ON (processo_codice) … ORDER BY processo_codice, started_at DESC, id DESC`, due volte come L2 |

In sintesi, due chiavi: **`(jobname, started_at DESC, id DESC)`** (L1 con jobname, L2, L4, L5) e
**`(processo_codice, started_at DESC, id DESC)`** (L3, L6, L7), più la recenza pura per L1 senza filtri.
Lato DB leggono lo stesso giornale anche `maintenance.vw_job_run_da_guardare`,
`maintenance.vw_job_run_da_superuser` e `dbops.vw_processi_programmazione`: il team DB li conosce meglio
di questo brief e li mette nel conto.

⚠️ L4 con prefisso usa `jobname LIKE 'x%'`: un btree serve un `LIKE` per prefisso solo in collation `C` o
con `text_pattern_ops`. Lo segnalo, non lo decido.

## 3. La richiesta

1. Dare a `maintenance.job_run_log` gli indici che servono le chiavi del §2, nella forma che il team DB
   ritiene giusta (quali colonne, se parziali su `NOT saltata`, se `INCLUDE`).
2. Verificare con `EXPLAIN` su L2, L3 e L5 che il piano usi gli indici.
3. Chiarire la FK `fk_job_run_log_processi` rispetto alla policy degli indici FK (§1): coperta dal nuovo
   indice su `processo_codice`, oppure esclusa con un motivo scritto.

## 4. Doc

* `docs/it/dbzero/maintenance/tabelle/job_run_log.md` si rigenera; il manuale
  `maintenance/manual/job_run_log.md` dice quali letture servono gli indici.
* [api_tracciamento.md](../../backend/core/manual/api_tracciamento.md) § Note oggi dice «`job_run_log` ha
  **solo** la chiave primaria»: a indici applicati quella riga va corretta. La corregge la sessione BE al
  ritorno (`/arrivi-db`), così il team DB non tocca `backend/` né la doc BE.

## 5. Ricadute BE/FE

Nessuna: nessuna query cambia, nessun contratto cambia.
