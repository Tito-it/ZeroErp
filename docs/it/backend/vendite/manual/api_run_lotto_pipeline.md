# API run_lotto_pipeline (Django)

## Scopo
Esporre via HTTP l'avvio della pipeline lotto vendite.

## Contesto
Endpoint applicativo che invoca il servizio Python `pr_run_lotto_pipeline`, equivalente alla procedura SQL omonima.

## Input
- Metodo: `POST`
- Path: `/api/vendite/pipeline/run/`
- Body JSON: `lotto_id`, `competenza_mese`, `tipo_doc_fiscale_id`, `utility_id`, `billing_account_id`, `lock_batch_id`, `meta`, `dry_run`, `tipo_lotto`

## Output
- `200`: `{ "lotto_id": <id>, "status": "ok" }`
- `400`: payload non valido o errore applicativo pipeline

## Regole
- Valida JSON e formato date (`YYYY-MM-DD`).
- Converte `dry_run` in boolean.
- Usa parser/request helper condivisi area core.
- Traduce eccezioni con envelope errore core.

## Dipendenze DB
- Dipendenze indirette via `services/pipeline_runner.py` e `db/pipeline_repository.py`.

## Note di migrazione
- Primo endpoint operativo per pilotare la migrazione SQL -> Django della pipeline vendite.
