# API write checklist (Core Django)

## Scopo
Fornire una checklist operativa pronta per nuovi endpoint write (`POST/PUT/PATCH/DELETE` con side effect).

## Checklist ready-to-use
1. **View**: usare `handle_post_json(request, handler=..., require_idempotency_key=True)`.
2. **Header**: ogni POST che scrive porta `Idempotency-Key` per costruzione (`_ApiViewBase.initial`, dal 2026-10-20); una POST che legge dichiara `post_accesso = "view"`.
3. **Service**: tenere logica business nel service, non nella view.
4. **Errori**: usare `ErrorManager` + codici dominio (`ServiceError`).
5. **Test API**:
   - caso OK con `Idempotency-Key`
   - caso KO senza `Idempotency-Key` (`E_IDEMPOTENCY_KEY_REQUIRED`)
6. **Test retryable**: se applicabile, verificare header `Retry-After`.
7. **Doc endpoint**: aggiungere in Input l’header richiesto `Idempotency-Key`.
8. **Contratto risposta**: verificare envelope `{data, meta}` in successo e `{error, meta}` in errore, con `meta.request_id`.
9. **Idempotenza forte (opzionale ma consigliata)**:
   - abilitare `DJANGO_API_STRONG_IDEMPOTENCY_ENABLED=1`
   - usare tabella `dbops.idempotency_keys` per `in_progress/completed/failed`
   - replay automatico della stessa risposta su duplicate key: 200 con header `X-Idempotency-Replayed: 1`
   - chiave gia` in corso: `E_IDEMPOTENCY_IN_PROGRESS` (409, retryable → `Retry-After`)
   - lo strong mode scatta solo con `require_idempotency_key=True` e header presente.

## Note
- Per endpoint read-only (`GET` senza side effect), non richiedere `Idempotency-Key`.
- Se serve eccezione temporanea, motivarla in doc e aprire task di riallineamento.
- Per endpoint lista/search, seguire `docs/it/dev/Policy-ricerca-e-paginazione(API-DB).md` e gli helper di `docs/it/dev/api.md` §«Paginazione» (`pagina_da_query`, `parse_list_params`, `envelope_da_offset`, `fetch_paged_with_total`; `validate_pagination` è ritirato dal 2026-10-21).
- Se endpoint search, impostare `is_search_endpoint = True` per attivare throttling DRF.
- In idempotenza forte, `request_id` e `tx_id` sono entrambi UUID (consigliato mantenere formato UUID anche lato tracing).
