# API run_lotto_pipeline (Django)

## Scopo
Esporre via HTTP l'avvio della pipeline lotto vendite.

## Contesto
Endpoint applicativo che invoca il servizio Python `pr_run_lotto_pipeline`, equivalente alla procedura SQL omonima.

## Input
- Metodo: `POST`
- Path canonico: `/api/v1/vendite/pipeline/run/`
- Path legacy (deprecato): `/api/vendite/pipeline/run/` (disabilitato di default)
- Header richiesto: `Idempotency-Key`
- Header sicurezza (solo path `/api/v1/...`): `Authorization: Bearer <access_token>`
- Body JSON: `lotto_id`, `competenza_mese`, `tipo_doc_fiscale_id`, `utility_id`, `billing_account_id`, `lock_batch_id`, `meta`, `dry_run`, `tipo_lotto`

## Output
- `200`: `{ "data": { "lotto_id": <id>, "status": "ok" }, "meta": { ... } }`
- `400`: payload non valido o errore applicativo pipeline

## Regole
- Valida JSON e formato date (`YYYY-MM-DD`).
- Converte `dry_run` in boolean.
- Per input compatibili UI/legacy, converte `0` in `null` sugli ID opzionali (`lotto_id`, `tipo_doc_fiscale_id`, `utility_id`, `billing_account_id`).
- `lock_batch_id` e` il correlatore del lotto: se lo passi e` **RIUSO** lotto; per creare un lotto nuovo devi **ometterlo** o passare `null` (il DB lo genera). Riutilizzare un `lock_batch_id` di un lotto `COMPLETATO` produce errore.
- Usa parser/request helper condivisi area core.
- Traduce eccezioni con envelope errore core.
- Implementa il pattern standard core `handle_post_json(...)`.
- Non usa `try/except Exception` locale: fallback errori non gestiti delegato al middleware API globale.
- Endpoint write protetto con obbligo `Idempotency-Key`.

## Dipendenze DB
- Dipendenze indirette via `services/pipeline_runner.py` e `db/pipeline_repository.py`.

## Note di migrazione
- Primo endpoint operativo per pilotare la migrazione SQL -> Django della pipeline vendite.
