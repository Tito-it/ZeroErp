# API Gestione code — coda lavori + coda stampa (Django)

## Scopo

Documentare gli endpoint della **UI di gestione code** (brief
`brief-be-fe-gestione-code-lavori-stampa`): conteggi per il badge top bar,
liste della coda lavori generica (`dbops.coda_lavori`) e della coda stampa
(`vendite.fatture_stampa_coda`), dettaglio job e azioni di governo
(annulla/requeue). Estendono il layer **tracciamento core** esistente
(`tracciamento/job-runs/` ecc.) — stessa area, stesso namespace.

## Contesto

Le code sono il motore async del cockpit fatturazione (Fase C): i verbi UI
accodano job (`FATTURAZIONE_GIRO`/`FATTURAZIONE_NUMERA`), la DEFINITIVA accoda
stampe, i worker `draina_coda_lavori`/`draina_coda_stampa` (systemd timer)
drenano. Questi endpoint danno all'operatore la superficie di **monitoraggio e
governo**: quanti processi ha in coda, se il worker è vivo, e la possibilità di
annullare/sbloccare i **propri** job.

Asimmetria di scope (regge il design):

| | Coda lavori | Coda stampa |
| --- | --- | --- |
| Proprietario | per-UTENTE via `scope->>'scope_key'` (whitelist emittenti) | per-EMITTENTE via JOIN a `vendite.fatture` |
| Azioni | annulla / requeue (solo propri, o `code_manage`) | nessuna (il drainer ritenta da solo) |

Tre layer: `views_tracciamento.py` (`ApiCode*`, `ApiCodaLavori*`,
`ApiCodaStampaList`) → `apps/core/services/coda_lavori/gestione_service.py` →
`CodaLavoriRepository` (core) + `VenditePipelineRepository.elenca_coda_stampa`
(vendite, satellite di fatture) + `MaintenanceRepository.job_liveness`.

## Input

Header sicurezza su tutti: `Authorization: Bearer <access_token>`. Area
funzionale: **`strumenti`** (area DEDICATA, seed §6 del brief — decisione
2026-07-21: non si apre `core` agli operatori solo per le code, esporrebbe il
tracciamento infra). `LETTURA` = conteggi/liste/dettaglio; `TUTTO` = anche le
azioni POST. Le view tracciamento legacy (audit-log, job-runs…) restano su
area `core`. I POST richiedono `Idempotency-Key` (header).

### 1. Conteggi badge (BE-4, sola lettura)

- `GET /api/v1/core/tracciamento/code/conteggi/`
- Conteggi vivi (PENDING/IN_CORSO) delle due code, **scoped** al chiamante, +
  liveness worker (`ultimo run entro 10 minuti` = attivo). Pollato dal FE a 60s.

### 2. Lista coda lavori (BE-5, sola lettura)

- `GET /api/v1/core/tracciamento/coda-lavori/`
- Query: `ambito` (`miei` default | `tutti` — richiede `code_manage`/SUPER_ADMIN),
  `stato`, `tipo` (job_type), `solo_vivi`, `data_da`/`data_a` (YYYY-MM-DD,
  inclusiva), `limit` (max 200)/`offset`.
- Ogni riga porta `is_mio` (calcolato dal BE: la `scope_key` del job coincide
  con quella del chiamante) e `proprietario` (`scope->>'username'`).

### 3. Lista coda stampa (BE-6, sola lettura)

- `GET /api/v1/core/tracciamento/coda-stampa/`
- Query: come sopra + `lotto_id`; niente `is_mio` (la coda è per-emittente).
- Righe: fattura (numero/anno/serie), emittente, lotto, stato, tentativi,
  ultimo_errore, documento_id.

### 4. Dettaglio job (BE-8, sola lettura)

- `GET /api/v1/core/tracciamento/coda-lavori/<job_id>/`
- Payload, origine, priorità, timeline (accodato/claimed/started/ended),
  tentativi/max, ultimo_errore, result, job_run_id, proprietario, is_mio.

### 5. Azioni (BE-7, comando)

- `POST /api/v1/core/tracciamento/coda-lavori/<job_id>/annulla/` · body `{}`
  — solo job **PENDING** → `ANNULLATO`.
- `POST /api/v1/core/tracciamento/coda-lavori/<job_id>/requeue/` · body
  `{"extra_tentativi": 1..10}` (default 3, fonte unica nel service) — solo job
  **ERRORE**, oppure **IN_CORSO davvero STANTIO** (`claimed_at` oltre la
  soglia del reaper, 30 min — stessa definizione di «bloccato»): riaccodare
  un job che un worker sta eseguendo farebbe partire una **seconda esecuzione
  concorrente** (review 2026-07-22). → `PENDING` con `max_tentativi += extra`
  (storia tentativi preservata).

## Output

- Conteggi:
```json
{ "data": {
    "coda_lavori": { "pending": 2, "in_corso": 1 },
    "coda_stampa": { "pending": 0, "in_corso": 0 },
    "worker": {
      "coda_lavori": { "last_run_at": "2026-07-21 22:47:07+02", "attivo": true, "last_ok": true },
      "coda_stampa": { "last_run_at": null, "attivo": false, "last_ok": null }
    }
} }
```
- Liste: `{ "data": { "count": N, "results": [ ... ] } }` (offset-based).
- Azioni: `{ "data": { "job_id": 5, "stato": "ANNULLATO" | "PENDING" } }`.

## Regole

- **Ownership scope-based (I-3)**: l'operatore vede/agisce sui job della
  propria `scope_key` (stessa fonte `scope_key_da_emittenti` dell'enqueue —
  nessuna seconda logica di scope, I-1). Fuori scope = **404** indistinguibile
  da inesistente (no leak). Whitelist emittenti `None` (admin globale) = vede
  tutto.
- **`code_manage`** (azione di processo, area `strumenti` — seed §6 del brief,
  id atteso 28): sblocca `?ambito=tutti` e le azioni su job altrui. SUPER_ADMIN
  bypassa. ⚠️ Fino all'apply dei seed (area + azione), tutto il layer è
  fail-closed: solo SUPER_ADMIN.
- **Niente race col worker**: annulla/requeue ri-verificano stato E scope
  nell'UPDATE (0 righe = 409 parlante) — un claim concorrente vince sempre.
- **Liveness fail-visible**: worker mai girato → `{attivo: false}` esplicito,
  mai una chiave mancante.

## Codici errore

| Codice | HTTP | Quando |
| --- | --- | --- |
| `E_PERMESSO_NEGATO` | 403 | `?ambito=tutti` senza `code_manage`/SUPER_ADMIN |
| `E_JOB_NON_TROVATO` | 404 | job inesistente o di altro scope (dettaglio/azioni) |
| `E_JOB_NON_ANNULLABILE` | 409 | annulla su job non più PENDING |
| `E_JOB_NON_RIACCODABILE` | 409 | requeue su job non riaccodabile (né ERRORE né IN_CORSO stantio) |
| `E_VALIDATION_INPUT` | 400 | `extra_tentativi` fuori range 1..10 |
| `E_IDEMPOTENCY_KEY_REQUIRED` | 400 | POST senza header `Idempotency-Key` |

## Dipendenze DB

- `dbops.coda_lavori` (+ `coda_lavori_tipi`): lettura/UPDATE diretti
  (annulla/requeue condizionati allo stato — design brief coda §3a).
- `vendite.fatture_stampa_coda` + JOIN `vendite.fatture` (scope emittente via
  `add_emittente_scope_condition`, convenzione SR) + `anagrafiche.emittenti_fiscali`.
- `maintenance.job_run_log` (liveness worker, jobname
  `draina_coda_lavori`/`draina_coda_stampa`).
- Seed `config.aree_funzionali` area `strumenti` + azione
  `config.azioni_processo` `code_manage` su quell'area (team DB, brief §6).

## Note di migrazione

Endpoint **accanto** al read-side esistente (I-4: `esiti/` e il polling
`run/<job_id>/` di vendite restano invariati). Consumer FE: badge top bar +
drawer rapido + vista «Strumenti → Code di lavoro». Raccordo col cantiere
dashboard-home: l'eventuale widget KPI «Processi in coda» dovrà riusare
`gestione_service.conteggi_code` come callable del registry contatori, non una
query nuova.
