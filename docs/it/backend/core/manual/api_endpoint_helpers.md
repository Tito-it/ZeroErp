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
- `JsonResponse` errore (`invalid_json`, `invalid_payload`, `exception_to_error_response`)

## Regole
- Parsing JSON centralizzato con `parse_json_body`: body non JSON -> 400 `{"error": "invalid_json"}`.
- Ogni `ValueError` sollevato dall'handler -> 400 `{"error": "invalid_payload"}`, senza codice ne' messaggio (le altre eccezioni passano da `exception_to_error_response`).
  ⚠️ Difetto noto (E-6): i due errori sono una stringa, non l'oggetto `error` dell'envelope, e il `ValueError` perde il suo messaggio — vedi [analisi difetti](../../../dev/work-in-progress/analisi-be-difetti-emersi-verifica-doc-api-core.md).
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
