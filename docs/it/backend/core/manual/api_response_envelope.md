# API response envelope (Core Django)

## Scopo
Definire il formato uniforme delle risposte successo/errore per tutte le API.

## Contesto
Gli helper sono in:
- `apps/core/api/success_responses.py`
- `apps/core/api/error_responses.py`
- `apps/core/services/error_translator.py`

## Input
- Risultato dominio (`dict`) per risposte successo.
- Eccezione (`ServiceError`, `DatabaseError`, `Exception`) per risposte errore.

## Output
- Successo: `{ "data": {...}, "meta": {...} }`
- Errore da service/DB (`exception_to_error_response`):
  `{ "error": {code, message, ui_action, ...}, "meta": {...} }`, dove `error` porta
  anche `detail`, `technical_message`, `hint`, `tx_id`, `retryable`, `fields`,
  `targets` quando valorizzati (le chiavi `null` vengono omesse).
- Errore da eccezione DRF di autenticazione/permessi (`drf_exception_handler`):
  `error` ridotto a `{code, message, ui_action}`.
- JSON o payload non validi (`invalid_json_response` / `invalid_payload_response`):
  `{ "error": "invalid_json" }` / `{ "error": "invalid_payload" }` — `error` e' una
  **stringa**, non un oggetto.
- `meta` include `request_id` e, se presente, `idempotency_key`; manca se entrambi
  sono assenti.

> ⚠️ Difetto noto (E-6): l'envelope di JSON/payload non validi non rispetta la
> forma `error: {code, message}` — vedi [analisi difetti](../../../dev/work-in-progress/analisi-be-difetti-emersi-verifica-doc-api-core.md).

## Regole
- Contratto stabile: `message` resta business/safe per codici tecnici.
- In produzione (`DJANGO_API_EXPOSE_TECHNICAL_DETAILS=0`) il dettaglio tecnico e` sanificato.
- In debug (`DJANGO_API_EXPOSE_TECHNICAL_DETAILS=1`) `technical_message` espone il dettaglio tecnico.
- Errori `retryable` includono header `Retry-After`.
- `invalid_json` e `invalid_payload` rispondono con `400`.

## Dipendenze DB
- Indirette: mapping errori DB tramite translator (`E_DATABASE`, `E_DATABASE_RETRYABLE`).

## Note di migrazione
- Evitare envelope custom nelle singole app dominio.
- Ogni nuova API deve rispondere nel formato standard core.
