# API run_attivita_pipeline (Django)

## Scopo

Esporre via HTTP l'avvio della pipeline attivita fatturabili.

## Contesto

Endpoint applicativo che invoca il servizio Python `pr_run_attivita_pipeline` in
`apps/vendite/services/attivita_pipeline_service.py`, il quale delega ad
`AttivitaPipelineRunner.run_pipeline`.

View in `apps/vendite/api/views.py`:

- `ApiRunAttivitaPipeline`
- `ApiRunAttivitaPipelineV1`

## Input

- Metodo: `POST`
- Path canonico: `/api/v1/vendite/attivita_fatturabili/pipeline/run/`
- Header richiesto: `Idempotency-Key`
- Header sicurezza: `Authorization: Bearer <access_token>`
- Body JSON (tutti i campi opzionali):
  - `lotto_id` (int) — `0`/`null` = crea/risolvi lotto
  - `competenza_mese` (date `YYYY-MM-DD`) — mese di competenza
  - `utility_id` (int) — filtro utility
  - `billing_account_id` (int) — filtro billing account
  - `sorgente_tipo_id` (int) — esegue solo il branch della sorgente specificata
  - `emittente_soggetto_ruolo_id` (int) — emittente fiscale (ruolo `anagrafiche.soggetti_ruoli`)
  - `lock_batch_id` (uuid) — correlatore lotto
  - `meta` (object) — metadati liberi del run
  - `dry_run` (bool) — esegue senza effetti reali (handler non chiamati, nessun task run aperto)

## Output

- `200`: `{ "data": { "lotto_id": <id>, "status": "ok" }, "meta": { ... } }`
- `400`: payload non valido, nessuna sorgente abilitata, o errore applicativo pipeline
- `409`: operazione gia` in corso con la stessa `Idempotency-Key`

## Regole

- Valida JSON e formato date (`YYYY-MM-DD`).
- Converte `0` in `null` sugli ID opzionali.
- Se `lotto_id` e` omesso o `0`, il lotto viene creato/risolto via `vendite.fn_get_or_create_lotto_attivita`.
- Se il lotto esiste ed e` `IN_ESECUZIONE`, il rilancio e` bloccato con `E_ATTIVITA_PIPELINE`.
- `sorgente_tipo_id` abilita l'esecuzione di un singolo branch; se assente, tutti i branch abilitati vengono eseguiti.
- **Semantica branch**: ogni sorgente abilitata corrisponde a un branch indipendente. Un errore `BRANCH` non blocca gli altri branch. Un errore `GLOBAL` ferma tutti i branch rimanenti e marca il lotto `ERRORE`.
- **`dry_run=true`**: la pipeline risolve step e task ma non chiama gli handler e non apre task run. Utile per validazione configurazione.
- **Risoluzione emittente fiscale**: delegata a `vendite.fn_get_or_create_lotto_attivita` con helper condiviso `vendite.fn_resolve_lotto_utility_emittente` (stessa priorita` del dominio lotto).
- Endpoint write protetto con obbligo `Idempotency-Key`.
- Endpoint v1 richiede JWT.

## Dipendenze DB

- `vendite.fn_get_or_create_lotto_attivita` — creazione/risoluzione lotto attivita
- `vendite.fn_set_attivita_lotto_stato` — aggiornamento stato lotto (`IN_ESECUZIONE`/`COMPLETATO`/`ERRORE`)
- `vendite.attivita_fatturabili_sorgenti_branch_policy` — sorgenti abilitate e policy branch
- `vendite.fn_list_attivita_pipeline_steps` — step pipeline da eseguire per branch
- `vendite.fn_start_attivita_lotto_task_run` / `fn_complete_attivita_lotto_task_run` / `fn_fail_attivita_lotto_task_run` — tracing task run

## Note architetturali

- Dominio `ATTIVITA_FATTURABILI` distinto da `LOTTO`; nessun mapping hardcoded sorgente→branch (resolver DB).
- Stato tecnico pipeline su `attivita_fatturabili_lotti.stato_lotto`; stato business su `stato_operativo`.
- Vedi [pr_run_attivita_pipeline](pr_run_attivita_pipeline.md) per dettagli sull'orchestrazione interna.
