# API Fatturazione — cockpit processi (Django)

## Scopo

Documentare gli endpoint di **comando** del cockpit di fatturazione (Fase C): i
verbi «Fattura» e «Rendi definitive» del mese di competenza, la numerazione del
singolo lotto, la ristampa massiva e la lettura degli esiti. Sono le azioni che
rendono azionabile la Dashboard Competenza, riusando **le stesse primitive del
batch** (I-1: un solo processo, due modi di avvio).

## Contesto

I verbi del mese sono **non bloccanti** (I-3): non eseguono il lavoro nella
richiesta HTTP, ma **accodano un job** nella coda lavori generica
`dbops.coda_lavori` (variante DB-native del pattern task-queue, senza broker) e
rispondono subito con l'handle del job. Il worker `draina_coda_lavori` (systemd
timer) lo esegue poi sotto l'identità dell'operatore (RLS attiva). Il FE segue
l'avanzamento via **polling** dello stato del job.

La numerazione del **singolo** lotto e la **ristampa** sono invece sincrone
(cardinalità 1 / accodamento veloce). Gate fiscale **I-7**: «Fattura» (pre-fiscale,
ferma a EMESSA) e «Rendi definitive» (numerazione) hanno **endpoint e permesso
distinti**; la stampa non numera mai.

Tre layer: `views.py` (`ApiFatturazione*`) → `services/pipeline_service.py` +
`fatturazione_driver_service.py` + handler coda → repository (`VenditeRepository`,
`VenditePipelineRepository`, `CodaLavoriRepository`).

## Input

Header sicurezza su tutti: `Authorization: Bearer <access_token>`. Tutti i POST
richiedono `Idempotency-Key: <uuid>` (header). Area funzionale: `vendite`.

### 1. Giro «Fattura competenza» (C-3, non bloccante)

- `POST /api/v1/vendite/fatturazione/run/` · permesso `genera_fatture_lotti`
- Body: `{ "competenza_mese": "YYYY-MM-DD" [, "fino_a_stato": "<codice>"]
  [, "gruppi": ["<gruppo_key>", …]] }`
- Corsia **differita**: si ferma a **EMESSA** (D-1), perimetro cumulativo
  `competenza ≤ M`. Scope emittente **catturato** all'accodamento.

#### 1-bis. Emissione mirata (`gruppi`, 2026-07-27)

Lo stesso endpoint, con `gruppi` valorizzato, fattura **solo** i gruppi
fatturabili indicati — un documento sorgente (PRV-0012, CTR-0007…) oppure gli
oneri di una commessa. Un solo verbo, due perimetri: il processo è identico
(invariante I-1), cambia solo cosa entra.

- Le chiavi arrivano da `GET /vendite/dashboard-competenza/gruppi/` e **non si
  costruiscono a mano**: le produce `vendite.fn_build_gruppo_fatturabile_key`.
- Corsia **`mirata`**: a differenza della differita **non filtra per corsia**
  (`p_fatturazione_immediata = NULL`). Non è una svista — la lista dei gruppi
  non conosce la corsia, quindi mostra anche i gruppi di commesse a
  fatturazione immediata: filtrare li renderebbe selezionabili a video e
  produttivi di **zero lotti, in silenzio**. La selezione esplicita
  dell'operatore è un perimetro più preciso dell'instradamento automatico.
  Fermata a EMESSA invariata (gate fiscale I-7).
- **Il criterio è uno stato del lotto, non un parametro**: il driver scrive le
  righe di `vendite.fatturazione_lotti_gruppi` nella **stessa transazione** in
  cui crea il lotto. Da lì in poi vive nel `LottoContext`, quindi un *rerun* o
  un *avanza step* dal `LottoDrawer` riproduce lo stesso perimetro invece di
  allargarlo.
- **Idempotenza**: la chiave di *business* della coda include un digest
  dell'insieme dei gruppi — senza, due emissioni mirate sullo stesso mese e
  scope con gruppi diversi cadrebbero sullo stesso job vivo e la seconda
  verrebbe assorbita in silenzio. Senza `gruppi` il digest è vuoto: la chiave
  del giro di massa resta identica a prima.
- Validazione: `gruppi` non-lista, elemento non stringa/vuoto, lista vuota
  (ambigua fra «niente» e «tutto») o oltre 200 elementi → **400**
  `E_VALIDATION_INPUT`.
- **L'esito è una LISTA di lotti**: `result.lotti = [{lotto_id,
  tipo_doc_fiscale_id, competenza_mese}, …]`. Un gruppo con righe di
  `tipo_doc_fiscale` diverso finisce in terne — e quindi lotti — diversi. Il FE
  offre N «vai al lotto», non uno.

### 2. Polling stato job (C-3)

- `GET /api/v1/vendite/fatturazione/run/<job_id>/`
- Ownership **scope-based**: l'operatore vede i job della propria `scope_key`
  (whitelist emittenti) — due operatori con la stessa whitelist condividono il
  giro deduplicato; un job di altro scope → **404** (indistinguibile da inesistente).

### 3. «Rendi definitive competenza» (C-4 perimetro, non bloccante)

- `POST /api/v1/vendite/fatturazione/numera/` · permesso `numera_fatture_lotti`
- Body: `{ "competenza_mese": "YYYY-MM-DD" }`
- Accoda un job `FATTURAZIONE_NUMERA`: esegue lo step DEFINITIVA (numera + accoda
  stampa) sui **lotti EMESSA** del mese. Polling via `run/<job_id>/`.

### 4. «Rendi definitive» singolo lotto (C-4, sincrono)

- `POST /api/v1/vendite/fatturazione/lotti/<lotto_id>/numera/` · permesso `numera_fatture_lotti`
- Body: `{}`. Guard scope (404 fuori scope) + guard **EMESSA** (409 se non EMESSA).

### 5. Ristampa massiva lotto (C-8, sincrono)

- `POST /api/v1/vendite/fatturazione/lotti/<lotto_id>/ristampa/` · nessun
  `post_permission` (stampa = lettura I-4; gate readonly lato FE)
- Body: `{}`. Guard scope (404) + guard **DEFINITIVA** (409): accoda in
  `vendite.fatture_stampa_coda` una riga per ogni fattura non esclusa; il worker
  `draina_coda_stampa` le renderizza. **Non numera** (gate DEFINITIVA → il
  backstop del worker non ha nulla da numerare).

### 6. Esiti giri + stato coda stampa (C-5, sola lettura)

- `GET /api/v1/vendite/fatturazione/esiti/`
- Riassunto per corsia da `maintenance.job_run_log` (jobname
  `run_fatturazione_batch*`/`draina_coda_stampa`/`draina_coda_lavori`) + conteggi
  coda stampa per stato **scoped all'operatore** (JOIN a `vendite.fatture`).

## Output

- Accodamento (run / numera perimetro):
```json
{ "data": { "job_id": 555, "stato": "PENDING" }, "meta": { "request_id": "..." } }
```
- Polling (`run/<job_id>/`):
```json
{ "data": {
    "id": 555, "job_type": "FATTURAZIONE_GIRO", "stato": "FATTO",
    "tentativi": 0, "max_tentativi": 5,
    "result": { "lane": 3, "senza_emittente": 0, "falliti": 0 },
    "ultimo_errore": null, "job_run_id": 12
} }
```
  Stati: `PENDING` → `IN_CORSO` → `FATTO` | `ERRORE` | `ANNULLATO`. Il `result`
  del giro riporta `lane` (terne emittibili), `falliti`; quello della
  numerazione perimetro `lotti`/`numerati`/`falliti`.
- Ristampa: `{ "data": { "lotto_id": 117, "accodate": 4 } }`
- Numerazione singolo lotto: esito dello step (`stato_doc_fiscale_id`,
  `step_eseguiti`, `motivo_stop`).
- Esiti: `{ "data": { "giri": [ { "jobname": "...", "last_ok": true, "last_run_at": "..." } ], "coda_stampa": { "PENDING": 2, "FATTO": 5 } } }`

## Regole

- **Idempotenza a due layer**: header HTTP `Idempotency-Key`
  (`dbops.idempotency_keys`, replay della risposta) ≠ **chiave di business** della
  coda `{job_type}:{competenza}:{scope_key}` (dedup dei job VIVI: due click sullo
  stesso mese/scope → stesso job). La `scope_key` = «ALL» (admin) o gli emittenti
  autorizzati ordinati.
- **Identità operatore catturata** all'accodamento (`auth_user_id`, `username`,
  `identita_id`, `emittente_ids`, `scope_key`): il worker la ripropone per intero
  (5 GUC via `set_jwt_gucs`) così la RLS risolve **come nel web**. Un job
  OPERATORE senza identità completa → fail-loud.
- **Gate fiscale I-7**: numerazione (atto fiscale) sempre dietro permesso
  `numera_fatture_lotti`, distinto da `genera_fatture_lotti`; la ristampa è gated
  a **DEFINITIVA** per non numerare mai via backstop.
- **Worker non schedulato** = job resta PENDING: il polling FE ha un cap
  (~3 min) e avvisa «in coda» invece di attendere all'infinito.

## Codici errore

| Codice | HTTP | Quando |
| --- | --- | --- |
| `E_VALIDATION_INPUT` | 400 | `competenza_mese` assente o identità operatore non risolta dal token |
| `E_JOB_NON_TROVATO` | 404 | polling di un job inesistente o di altro scope |
| `E_LOTTO_NON_TROVATO` | 404 | lotto fuori scope/inesistente (numera/ristampa singolo) |
| `E_LOTTO_NON_NUMERABILE` | 409 | «Rendi definitive» su lotto non EMESSA |
| `E_LOTTO_NON_RISTAMPABILE` | 409 | ristampa massiva su lotto non DEFINITIVA |
| `E_IDEMPOTENCY_KEY_REQUIRED` | 400 | POST senza header `Idempotency-Key` |

## Dipendenze DB

- **Coda lavori generica**: `dbops.coda_lavori` (+ `dbops.coda_lavori_tipi`
  registry, seed tipi `FATTURAZIONE_GIRO`/`FATTURAZIONE_NUMERA`) +
  `dbops.fn_accoda_lavoro(...)` (enqueue atomico + dedup job vivi). Claim/reaper/
  marca = BE in SQL diretto (`FOR UPDATE SKIP LOCKED`).
- **Coda stampa** (outbox PDF): `vendite.fatture_stampa_coda` +
  `vendite.fn_accoda_stampe_lotto(p_lotto_id)`. Drenata da `draina_coda_stampa`.
- **Pipeline**: `vendite.fatturazione_lotti`, `vendite.fatture`,
  `config.stati_doc_fiscale` (EMESSA/DEFINITIVA), `maintenance.job_run_log`.
- **Emissione mirata**: `vendite.fatturazione_lotti_gruppi` (perimetro del
  lotto), `vendite.fn_build_gruppo_fatturabile_key` (unica fonte della chiave) e
  il parametro `p_gruppi` di `fn_list_emittibili_lane`,
  `fn_list_commesse_emittibili`, `fn_emit_attivita_fatturabili_da_commessa`,
  `fn_select_attivita_fatturabili`. Assenza di righe/`NULL` = nessuna
  restrizione = comportamento del giro schedulato.
- **RLS operatore** su `fatturazione_lotti`/`fatture` (policy
  `rls_*_ef_whitelist`, GUC `app.current_user_id` + `app.ruolo_applicativo`).

## Note di migrazione

Le azioni sono endpoint di **comando accanto** alle viste `vw_dash_*` (I-6: il
read-side non si tocca). Deploy worker: systemd timer su `draina_coda_lavori`
(+ `draina_coda_stampa`) — vedi `docs/it/dev/backend/play-book-operativo-backend.md`
§16. Contratto coda + design: `docs/it/dev/work-in-progress/brief-design-coda-lavori-generica.md`;
guide funzionali `docs/it/guide/gestione-code-di-lavoro.md` +
`analisi-tracciamento-processi-e-job.md`.

**Emissione mirata (2026-07-27)**: additiva su `fatturazione/run/`. Senza
`gruppi` il comportamento — corsia, chiave di dedup, esito — è **bit-identico**
a prima. Substrato DB `20260727-10..19`; brief BE/FE
`dev/work-in-progress/brief-be-fe-emissione-fattura-mirata.md`.
