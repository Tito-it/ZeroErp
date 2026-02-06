# API write checklist (Core Django)

## Scopo
Fornire una checklist operativa pronta per nuovi endpoint write (`POST/PUT/PATCH/DELETE` con side effect).

## Checklist ready-to-use
1. **View**: usare `handle_post_json(request, handler=..., require_idempotency_key=True)`.
2. **Header**: verificare presenza `Idempotency-Key` (gestito dal core helper).
3. **Service**: tenere logica business nel service, non nella view.
4. **Errori**: usare `ErrorManager` + codici dominio (`ServiceError`).
5. **Test API**:
   - caso OK con `Idempotency-Key`
   - caso KO senza `Idempotency-Key` (`E_IDEMPOTENCY_KEY_REQUIRED`)
6. **Test retryable**: se applicabile, verificare header `Retry-After`.
7. **Doc endpoint**: aggiungere in Input l’header richiesto `Idempotency-Key`.
8. **Contratto risposta**: verificare envelope `{data,error}` + `meta.request_id`.

## Note
- Per endpoint read-only (`GET` senza side effect), non richiedere `Idempotency-Key`.
- Se serve eccezione temporanea, motivarla in doc e aprire task di riallineamento.
- Per endpoint lista/search, seguire `docs/it/dev/Policy-ricerca-e-paginazione(API-DB).md` e usare i helper DRF core.
- Se endpoint search, impostare `is_search_endpoint = True` per attivare throttling DRF.
