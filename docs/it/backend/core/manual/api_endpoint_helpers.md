# API endpoint helpers (Core Django)

## Scopo
Centralizzare il flusso standard dei POST JSON (parse, validazione base, envelope, idempotenza).

## Contesto
La logica e` implementata in `apps/core/api/endpoint_helpers.py` e viene usata dalle view dominio per ridurre boilerplate.

## Input
- `request: HttpRequest | Request`
- `handler(payload: dict) -> dict`
- `require_idempotency_key: bool` (default `False`)

## Output
- `JsonResponse` di successo (`success_response`)
- `JsonResponse` errore, sempre nell'envelope (`exception_to_error_response`)

## Regole
- Parsing JSON centralizzato con `parse_json_body`: corpo illeggibile (anche non UTF-8) o che non e' un oggetto -> 400 `E_VALIDATION_INPUT` nell'envelope, `context.motivo` `invalid_json` / `invalid_payload` (BB `errore_corpo`, lo stesso di `corpo_oggetto`).
- Ogni eccezione dell'handler, `ValueError` compreso, passa da `exception_to_error_response`: un `ValueError` esce 400 `E_VALIDATION_INPUT` col suo messaggio. Fino al 2026-10-07 i due casi rispondevano `{"error": "invalid_json"}` / `{"error": "invalid_payload"}` fuori envelope (E-6, chiuso).
- Se `require_idempotency_key=True` e header mancante -> `E_IDEMPOTENCY_KEY_REQUIRED`.
- Se `DJANGO_API_STRONG_IDEMPOTENCY_ENABLED=1` **e** l'endpoint passa `require_idempotency_key=True` (con l'header presente):
  - claim key su `dbops.idempotency_keys`
  - replay su `completed` (`X-Idempotency-Replayed: 1`)
  - `409` su `in_progress` (`E_IDEMPOTENCY_IN_PROGRESS`)
  - `mark_completed`/`mark_failed` su esito handler.
- Logging operativo idempotenza:
  - `idempotency_first_execution`
  - `idempotency_replay`
  - `idempotency_in_progress`
  - `idempotency_completed`
  - `idempotency_failed_*`

## Altri helper del modulo

- `handle_detail_patch(request, update_fn, pk, *, require_idempotency_key=False)`: PATCH di dettaglio, delega a `handle_post_json` con `update_fn(pk, payload)`.
- `get_scope_user_id(request)`: `auth_user_id` per il filtro di scope emittente; `None` per il superuser Django (nessun filtro).
- `get_risorsa_umana_id(request)`: la risorsa umana dell'utente (identita' OPERATORE attiva → `risorse_umane` attiva), con cache per richiesta; `None` se non associato.

## Dipendenze DB
- `dbops.idempotency_keys` (solo con strong idempotency attiva)
- `dbops.fn_get_or_create_session_tx_id()` (risoluzione `tx_id`)

## Note di migrazione
- Le view dominio nuove devono usare questo helper invece di implementare `try/except` locali.
- La idempotenza "header only" resta valida anche con strong mode disattivata.
