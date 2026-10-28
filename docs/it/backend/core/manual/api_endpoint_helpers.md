# API endpoint helpers (Core Django)

## Scopo
Centralizzare il flusso standard dei POST JSON (parse, validazione base, envelope, idempotenza).

## Contesto
La logica e` implementata in `apps/core/api/endpoint_helpers.py` e viene usata dalle view dominio per ridurre boilerplate.

## Input
- `request: HttpRequest | Request`
- `handler(payload: dict) -> dict`
- `require_idempotency_key: bool` (default `False`)
- `unita_di_lavoro: UnitaDiLavoro` (default `ATOMICA`; `A_PASSI` per le operazioni che committano un passo alla volta) — conta solo in modalita' forte

## Output
- `JsonResponse` di successo (`success_response`)
- `JsonResponse` errore, sempre nell'envelope (`exception_to_error_response`)

## Regole
- Parsing JSON centralizzato con `parse_json_body`: corpo illeggibile (anche non UTF-8) o che non e' un oggetto -> 400 `E_VALIDATION_INPUT` nell'envelope, `context.motivo` `invalid_json` / `invalid_payload` (BB `errore_corpo`, lo stesso di `corpo_oggetto`).
- Ogni eccezione dell'handler, `ValueError` compreso, passa da `exception_to_error_response`: un `ValueError` esce 400 `E_VALIDATION_INPUT` col suo messaggio. Fino al 2026-10-07 i due casi rispondevano `{"error": "invalid_json"}` / `{"error": "invalid_payload"}` fuori envelope (E-6, chiuso).
- Se `require_idempotency_key=True` e header mancante -> `E_IDEMPOTENCY_KEY_REQUIRED`.
- Se `DJANGO_API_STRONG_IDEMPOTENCY_ENABLED=1` **e** l'endpoint passa `require_idempotency_key=True` (con l'header presente):
  - prenotazione con `IdempotencyStore.claim_or_replay`, che chiama `dbops.fn_idempotency_prenota(key, auth_user_id, endpoint, request_id, ripresa_ammessa)`, in autocommit (la prenotazione si vede subito dalle altre richieste). `endpoint` = metodo + percorso senza query string; `auth_user_id` = `get_actor_user_id` (NULL per l'anonimo); `ripresa_ammessa` = `unita_di_lavoro == ATOMICA`, **sempre** passato (NULL e' `E_SCRIPT_CHIAMATA_NON_VALIDA`)
  - REPLAY: risposta salvata (`X-Idempotency-Replayed: 1`)
  - IN_CORSO: `409` `E_IDEMPOTENCY_IN_PROGRESS`
  - key di un altro utente o endpoint: `400` `E_IDEMPOTENCY_KEY_RIUSATA`, sollevato dalla funzione
  - **ATOMICA**: handler e `mark_completed` in un `transaction.atomic()`; il diario (`ErrorManager.log_error_only`) aspetta la fine della transazione (`ErrorManager.diario_dopo_la_transazione`)
  - **A_PASSI**: handler e `mark_completed` senza `atomic` esterno
  - su eccezione: `mark_failed` **fuori** dall'`atomic`, dopo il rollback.
- Gli endpoint A_PASSI stanno nel registro di `apps/core/tests/test_unita_di_lavoro.py`.
- Logging operativo idempotenza:
  - `idempotency_first_execution`
  - `idempotency_replay`
  - `idempotency_in_progress`
  - `idempotency_completed`
  - `idempotency_failed_*`

## Altri helper del modulo

- `get_scope_user_id(request)`: `auth_user_id` per il filtro di scope emittente; `None` per il superuser Django (nessun filtro).
- `get_risorsa_umana_id(request)`: la risorsa umana dell'utente (identita' OPERATORE attiva → `risorse_umane` attiva), con cache per richiesta; `None` se non associato.

## Dipendenze DB
- `dbops.fn_idempotency_prenota` e `dbops.idempotency_keys` (solo con strong idempotency attiva)
- `dbops.fn_get_or_create_session_tx_id()` (risoluzione `tx_id`)
- `config.parameters.SYSTEM_IDEMPOTENZA_IN_CORSO_SECONDI`: la soglia di ripresa. La legge e la valida `dbops.fn_idempotency_soglia_secondi`, per la prenotazione e per il backend (`IdempotencyStore.soglia_ripresa_secondi`), che la confronta col timeout di gunicorn all'avvio e a ogni `kill -HUP` (`backend/gunicorn.conf.py` → `apps/core/services/soglia_idempotenza.py`)

## Vedi anche
- [Le operazioni che non si ripetono](/guide/operazioni-che-non-si-ripetono) — il meccanismo intero
- [API — regole comuni](/dev/api), sezione «Idempotency-Key»

## Note di migrazione
- Le view dominio nuove devono usare questo helper invece di implementare `try/except` locali.
- La idempotenza "header only" resta valida anche con strong mode disattivata.
