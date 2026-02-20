# API run_lotto_pipeline (Django)

## Scopo

Esporre via HTTP l'avvio della pipeline lotto vendite.

## Contesto

Endpoint applicativo che invoca il servizio Python `pr_run_lotto_pipeline`, equivalente alla procedura SQL omonima.

## Input

- Metodo: `POST`
- Path canonico: `/api/v1/vendite/pipeline/run/`
- Header richiesto: `Idempotency-Key`
- Header sicurezza: `Authorization: Bearer <access_token>`
- Body JSON (tutti i campi opzionali):
  - `lotto_id` (int) — `0`/`null` = crea/risolvi lotto
  - `competenza_mese` (date `YYYY-MM-DD`) — mese di competenza
  - `tipo_doc_fiscale_id` (int) — tipo documento fiscale
  - `utility_id` (int) — filtro utility
  - `billing_account_id` (int) — filtro billing account
  - `emittente_soggetto_ruolo_id` (int) — emittente fiscale (ruolo `anagrafiche.soggetti_ruoli`)
  - `lock_batch_id` (uuid) — correlatore lotto (vedi Regole)
  - `meta` (object) — metadati liberi del run
  - `dry_run` (bool) — esegue senza effetti reali
  - `tipo_lotto` (string) — `MASSIVO` (default) o `GIORNALIERO`

## Output

- `200`: `{ "data": { "lotto_id": <id>, "status": "ok" }, "meta": { ... } }`
- `400`: payload non valido o errore applicativo pipeline

## Regole

- Valida JSON e formato date (`YYYY-MM-DD`).
- Converte `dry_run` in boolean.
- Converte `0` in `null` sugli ID opzionali (`lotto_id`, `tipo_doc_fiscale_id`, `utility_id`, `billing_account_id`, `emittente_soggetto_ruolo_id`).
- `lock_batch_id` è il correlatore del lotto: se passato è **RIUSO** lotto; per creare un lotto nuovo **ometterlo** o passare `null` (il DB lo genera). Riutilizzare un `lock_batch_id` di un lotto `COMPLETATO` produce errore.
- **Risoluzione emittente fiscale** — delegata a `vendite.fn_get_or_create_lotto` nel DB con questa priorità:
  1. `emittente_soggetto_ruolo_id` esplicito nel payload → validato e usato direttamente.
  2. Dedotto dal mapping `billing_account_id` → emittente fiscale, se `billing_account_id` valorizzato.
  3. Unico emittente fiscale attivo nel sistema → usato come default.
  4. Se non determinabile → errore bloccante.
- **`emittente_soggetto_ruolo_id` è attributo del lotto**, non del billing account: viene persistito su `vendite.fatturazione_lotti.emittente_soggetto_ruolo_id` e usato da tutti i task pipeline (es. `select_attivita`) come fonte primaria. Il valore nei `params` JSON della config pipeline non sovrascrive quello del lotto.
- Implementa il pattern standard core `handle_post_json(...)`.
- Endpoint write protetto con obbligo `Idempotency-Key`.
- Endpoint v1 richiede JWT.

## Dipendenze DB

- `vendite.fn_get_or_create_lotto` (creazione/risoluzione lotto + emittente)
- `vendite.fatturazione_lotti.emittente_soggetto_ruolo_id` (attributo lotto persistito)
- Dipendenze indirette via `services/pipeline_runner.py` e `db/pipeline_repository.py`

## Note di migrazione

- Primo endpoint operativo per pilotare la migrazione SQL -> Django della pipeline vendite.
- L'emittente fiscale era in precedenza dedotto a runtime dai parametri; ora è attributo esplicito del lotto (persistito in DB alla creazione).
