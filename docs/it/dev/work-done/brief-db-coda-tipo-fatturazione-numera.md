# Brief DB — nuovo tipo job coda `FATTURAZIONE_NUMERA` (prerequisito C-4 perimetro)

> ## ✅ FATTO 2026-07-21 — archiviato in work-done
>
> Il team DB ha seedato il tipo job. Verificato live sul DB dev:
> `('FATTURAZIONE_NUMERA', 'fatturazione_numera_default', 'OPERATORE', 3, True)`.
> Il BE C-4 (handler `fatturazione_numera_handler` + endpoint
> `POST /vendite/fatturazione/numera/`) è stato realizzato su questo seed.

---

> **Tipo**: brief DB al team (seed 80_data) · **Target**: `dev/db-tid` · **Data**:
> 2026-07-21 · **Owner richiesta**: BE (cockpit fatturazione, Fase C, step C-4) ·
> **Priorità**: prerequisito per il BE C-4 «Rendi definitive competenza» (perimetro).
>
> Regola: le azioni DB (seed/migration) non partono dall'agent — questo è il brief scritto
> ([[feedback_db_actions_passaggio_team]], [[feedback_be_fe_attende_prerequisiti_db]]). Il
> BE C-4 (handler + endpoint) **attende** questo seed prima di partire.

## 1. Cosa serve

Un **nuovo tipo di job** nella coda lavori generica per la **numerazione di perimetro**:
lo step DEFINITIVA (numera + accoda stampa) sui **più lotti EMESSA** di un mese di
competenza, eseguito in background (I-3: 2+ lotti → non bloccante), corsia dedicata e
**separata dalla fatturazione** (gate fiscale I-7 — «Fattura» ferma a EMESSA, «Rendi
definitive» numera). È il gemello di `FATTURAZIONE_GIRO` (C-3) per il verbo numerazione.

**Nessun nuovo oggetto DDL**: la coda `dbops.coda_lavori` + `fn_accoda_lavoro` + i CHECK
`run_as↔scope` esistono già (20260720-07..10). Serve **solo una riga di seed** nel registry
tipi `dbops.coda_lavori_tipi` — stesso pattern del seed `FATTURAZIONE_GIRO`
(`loadUpdateData` upsert su `codice`, `runOnChange: true`).

## 2. La riga di seed (proposta)

Aggiungere a `db/changelog/migrations_v2/80_data/sql/dbops/coda_lavori_tipi.csv`:

```csv
codice,handler_code,descrizione,run_as_default,max_tentativi_default,attivo
FATTURAZIONE_NUMERA,fatturazione_numera_default,"Numerazione di perimetro (C-4): step DEFINITIVA (numera + accoda stampa) sui lotti EMESSA di un mese di competenza.",OPERATORE,3,true
```

| Colonna | Valore | Perché |
| --- | --- | --- |
| `codice` (= `job_type`) | `FATTURAZIONE_NUMERA` | chiave naturale stabile, FK da `coda_lavori.job_type`; simmetrica a `FATTURAZIONE_GIRO` |
| `handler_code` | `fatturazione_numera_default` | chiave di dispatch → il BE la registra nel `handler_registry` Python (C-4) |
| `run_as_default` | **`OPERATORE`** | numerazione gated `numera_fatture_lotti` + scope operatore via RLS (come il single-lotto e come `FATTURAZIONE_GIRO`); MAI SISTEMA |
| `max_tentativi_default` | `3` | numera è **idempotente** per-fattura (`fn_numera_fattura_opz_emessa`, C-2d) e resume-safe per-lotto → retry sicuro, ma è atto fiscale: soglia più bassa del giro (5). Tarabile |
| `attivo` | `true` | dispatch worker-based (non fail-fast in-transazione): l'enqueuer (endpoint C-4) atterra **insieme** all'handler → nessuna finestra di dispatch orfano (stessa logica del seed `FATTURAZIONE_GIRO`) |

> **Sequenza sicura**: il seed può essere applicato **prima** del BE senza rischio — finché
> il BE C-4 non espone l'endpoint, **nessuno accoda** job di quel tipo (nessun dispatch
> orfano possibile). Il BE registra `fatturazione_numera_default` in `VenditeConfig.ready()`
> e apre `POST /vendite/fatturazione/numera/` (perimetro) quando questo seed è live.

## 3. Cosa NON serve (per evitare over-ask)

* **Nessun GRANT nuovo**: il job è `run_as=OPERATORE` → gira sul ruolo **app**
  (`zeroerp_app`, RLS attiva con l'identità dell'operatore) che ha già i grant su
  `dbops.coda_lavori` e sulle tabelle di fatturazione. Il ruolo batch **non è coinvolto**
  (nessun job SISTEMA).
* **Nessuna fn/trigger/DDL**: solo la riga di registry.
* **Nessuna coda dedicata**: riusa `dbops.coda_lavori` (il worker `draina_coda_lavori` già
  deployato la drena e dispatcha per `handler_code`).

## 4. Verifica (DoD)

Dopo l'apply del seed:

```sql
SELECT codice, handler_code, run_as_default, attivo
  FROM dbops.coda_lavori_tipi WHERE codice = 'FATTURAZIONE_NUMERA';
-- atteso: 1 riga, handler_code=fatturazione_numera_default, run_as_default=OPERATORE, attivo=t
```

Poi il BE C-4 può accodare il job; il worker `draina_coda_lavori` lo dispatcha
all'handler registrato. (Smoke end-to-end del verbo = lato BE C-4, su dati reali.)
