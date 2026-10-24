# API run_lotto_pipeline_until_done (Django)

## Scopo

Esporre via HTTP il **driver** della pipeline lotto: a differenza di
[`pipeline/run/`](api_run_lotto_pipeline.md) (che esegue **un solo step** per
chiamata), questo endpoint **concatena gli step** finché la catena del lotto è
conclusa, restituendo un esito strutturato con il motivo di stop.

## Contesto

Endpoint applicativo che invoca il servizio Python
`run_lotto_pipeline_until_done` (`apps.vendite.services.pipeline_service`), che a
sua volta delega a `LottoPipelineRunner.run_lotto_until_done` (chiama `run_pipeline`
in loop). Stesso motore di `pipeline/run/`, nessuna logica di stato duplicata.

View: `ApiRunLottoPipelineUntilDone` (`apps.vendite.api.views`).

> È l'avvio **on-demand da interfaccia** della fatturazione. La schedulazione
> automatica (cron/timer immediata+differita) usa lo stesso motore via management
> command `run_fatturazione_batch` (non un'API).
>
> **Scope RLS (contesto di esecuzione).** Questo endpoint gira nel contesto
> **OPERATORE** del chiamante (GUC d'identità dal JWT): quando la RLS operatori sarà
> *enforced*, l'operatore potrà fatturare **solo gli emittenti nella sua whitelist**
> (un `emittente_soggetto_ruolo_id` fuori scope → nessun lotto/effetto). Il batch
> **headless** (cron `run_fatturazione_batch`), invece, gira in contesto **SISTEMA**
> (tutti gli emittenti). Vedi
> [brief-db-contesto-sistema-batch-fatturazione-rls.md](/dev/work-done/brief-db-contesto-sistema-batch-fatturazione-rls)
> (RLS opzione B). Oggi (RLS dormiente) entrambi i percorsi vedono tutto.

## Input

- Metodo: `POST`
- Path canonico: `/api/v1/vendite/pipeline/run-until-done/`
- Header richiesto: `Idempotency-Key`
- Header sicurezza: `Authorization: Bearer <access_token>`
- Permesso: `post_permission = "genera_fatture_lotti"` (area `vendite`)
- Body JSON (identico a `pipeline/run/`, tutti i campi opzionali):
  - `lotto_id` (int) — `0`/`null` = crea/risolvi lotto
  - `competenza_mese` (date `YYYY-MM-DD`)
  - `tipo_doc_fiscale_id` (int)
  - `utility_id` (int)
  - `billing_account_id` (int)
  - `emittente_soggetto_ruolo_id` (int) — emittente fiscale (ruolo `anagrafiche.soggetti_ruoli`)
  - `lock_batch_id` (uuid) — correlatore lotto
  - `meta` (object) — metadati liberi; la chiave `fatturazione_immediata` (bool)
    porta la **corsia** (filtro propagato al pull); vedi `run_fatturazione_batch`
  - `dry_run` (bool JSON stretto: una stringa o un numero → `400 E_VALIDATION_INPUT`)
  - `tipo_lotto` (string) — `MASSIVO` (default) o `GIORNALIERO`

⚠️ **`data_documento` NON è esposta qui, ed è deliberato** (2026-08-25). Il
servizio `run_lotto_pipeline_until_done` accetta il parametro — è così che i
verbi del cockpit scrivono la data dichiarata sui lotti che creano — ma
`_run_lotto_kwargs` non lo mappa dal body: questo endpoint resta la superficie
**stretta** del driver, e la data documento è una decisione d'atto che si prende
dai verbi (`fatturazione/run/`, `fatturazione/numera/`,
`lotti/<id>/numera/` — vedi [api_fatturazione.md](api_fatturazione.md)).
Un lotto creato da qui prende quindi la data dalla **politica del suo registro**,
che è il default giusto. Detto perché non venga letto come una dimenticanza.

## Output

- `200`: esito del driver

```json
{
  "data": {
    "lotto_id": 123,
    "stato_lotto": "COMPLETATO",
    "stato_doc_fiscale_id": 8,
    "step_eseguiti": 3,
    "motivo_stop": "COMPLETATO"
  },
  "meta": { ... }
}
```

Campi dell'esito:

- `lotto_id` — lotto creato/risolto (può essere `null` solo se il primo run su lotto
  nuovo fallisce, caso in cui l'errore è propagato come `4xx`, non come esito).
- `stato_lotto` — stato job del lotto a fine driver.
- `stato_doc_fiscale_id` — stato documentale dell'ultimo step eseguito (nullable).
- `step_eseguiti` — numero di step realmente eseguiti nel run.
- `motivo_stop` — perché il driver si è fermato:
  - `COMPLETATO` — catena conclusa: step di chiusura (`chiude_lotto`) raggiunto,
    oppure nessun avanzamento residuo;
  - `BLOCCATO_CRITICITA` — segnalazioni critical attive sul lotto
    (`E_PIPELINE_LOTTO_CRITICAL`): correggerle e ri-lanciare;
  - `ERRORE` — la catena si è fermata su un errore di dominio. Due famiglie:
    il fallimento di uno **step** (il lotto è marcato `ERRORE`) e il **rifiuto
    pre-volo**, quando il lotto non è dentro la propria catena
    (`E_PIPELINE_STATO_LOTTO`, dal 2026-09-08 — vedi
    [`pipeline/run/`](api_run_lotto_pipeline.md) §Regole);
  - `GUARD_MAX_ITER` — backstop anti-loop raggiunto (anomalo: indica step che non
    avanzano).
- `errore` — l'errore di dominio che ha fermato la catena. Porta gli **stessi
  nomi dell'envelope** — `code`, `message`, `detail`, `hint`, `fields`,
  `targets` — così che a video il gesto lo disegni un consumatore solo.
  ⚠️ **La chiave c'è sempre**, col valore a `null` quando la catena non si è
  fermata per errore: va guardato il **valore**, non la presenza della chiave.
  ⚠️ **È il canale su cui il fallimento arriva davvero all'operatore**: questi
  endpoint rispondono `200` anche quando la catena si ferma, quindi il frontend
  rende `errore.message` e non il messaggio dell'envelope (che qui non passa).
- `400`: payload non valido o errore applicativo pipeline (`E_PIPELINE_VALIDATION`,
  `E_PIPELINE`, …).

> ⛔ **Un `200` non è un successo: si guarda `motivo_stop`.** Il fallimento è un
> campo del payload e non uno status, perché la catena può aver eseguito qualche
> step prima di fermarsi e quel lavoro va raccontato. Difetto misurato in-app il
> 2026-08-21: toast verde su un lotto che il database aveva rifiutato. Lato
> frontend la lettura sta in `verdettoRunner` (`useLottoAzioni`), con i soli
> `COMPLETATO` e `FERMATO_A_STATO` come esiti buoni.

## Regole

- Stop a `chiude_lotto`: con la configurazione corrente (`chiude_lotto` su
  `DEFINITIVA`) la catena si ferma alla **numerazione**, prima di `INVIATA`/SDI
  (fuori scope). Il driver **non** chiude il lotto direttamente: lo fa
  `_process_close_lotto_by_flag` dentro `run_pipeline` (niente doppia chiusura).
- Non solleva sui motivi di stop noti (`BLOCCATO_CRITICITA`/`ERRORE` sono esiti, non
  eccezioni); l'unica eccezione propagata è il fallimento del **primo** run su lotto
  nuovo (nessun `lotto_id` da riportare).
- Stesse validazioni e risoluzione emittente di `pipeline/run/` (vedi quel manuale):
  validazione lookup `tipo_doc_fiscale_id`/`utility_id`, normalizzazione `0`→`null`,
  emittente come attributo del lotto.
- ⛔ **Il lotto dev'essere dentro la propria catena** (2026-09-08): un lotto
  esistente il cui stato fiscale non è uno degli step configurati fa **rifiutare
  il giro** (`E_PIPELINE_STATO_LOTTO`), invece di girare a vuoto. Il driver lo
  vede come `motivo_stop: ERRORE` con l'`errore` valorizzato — nessuno step
  eseguito, stato del lotto **invariato**. Regola estesa e motivazioni in
  [`pipeline/run/`](api_run_lotto_pipeline.md) §Regole.
- ⭐ **`stato_lotto` nell'esito non è più «lavabile» da un giro vuoto**
  (2026-09-08): la conclusione ricalcola sempre le segnalazioni prima di
  scrivere lo stato job, quindi un giro che non esegue step non può restituire
  `COMPLETATO` su un lotto le cui fatture sono ancora rotte. Chi leggeva
  `stato_lotto` da questo esito per dire «è andata bene» ora legge un dato che
  è stato **guadagnato**.
- Guard anti-loop `_MAX_STEP_ITERATIONS` (backstop).
- Endpoint write: `Idempotency-Key` obbligatoria, JWT richiesto.

## Dipendenze DB

- Le stesse di `pipeline/run/` (`fn_get_or_create_lotto`,
  `fn_resolve_lotto_utility_emittente`, catalogo step pipeline, ecc.).
- Lettura stato avanzamento: `vendite.fatturazione_lotti.stato_doc_fiscale_id` +
  flag `config.stati_doc_fiscale.chiude_lotto`.

## Vedi anche

- [api_run_lotto_pipeline.md](api_run_lotto_pipeline.md) — singolo step.
- Management command `run_fatturazione_batch` — driver batch a corsie
  (immediata/differita) che richiama lo stesso servizio per emittente.
