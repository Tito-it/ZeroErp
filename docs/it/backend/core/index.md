# Area 'core' (Backend)

## API
- [api-domain-conventions](manual/api-domain-conventions.md) — Definire uno standard unico per costruire future API di dominio.
- [api_diagnostics_error_envelope](manual/api_diagnostics_error_envelope.md) — Fornire un endpoint tecnico per validare contratto error envelope e policy retry.
- [api_endpoint_helpers](manual/api_endpoint_helpers.md) — Centralizzare il flusso standard dei POST JSON (parse, validazione base, envelope, idempotenza).
- [api_lookup_codici](manual/api_lookup_codici.md) — Espone una ricerca generica su tabelle di configurazione con struttura id / codice / descrizione. Permette autocompletamento e ricerca ILIKE da UI senza dover creare endpoint dedicati per ogni tabella config.
- [api_pagination](manual/api_pagination.md) — Fornire configurazioni DRF standard per paginazione coerente su endpoint list/search.
- [api_response_envelope](manual/api_response_envelope.md) — Definire il formato uniforme delle risposte successo/errore per tutte le API.
- [api_retry_policies](manual/api_retry_policies.md) — Uniformare gestione idempotency key e semantica retry lato API.
- [api_routing_core](manual/api_routing_core.md) — Documentare il routing core tra path legacy e path versionato v1.
- [api_search_validation](manual/api_search_validation.md) — Evitare query di ricerca troppo generiche che degradano performance e selettivita`.
- [api_throttling](manual/api_throttling.md) — Limitare burst di chiamate sugli endpoint search per proteggere backend e DB.
- [api_write_checklist](manual/api_write_checklist.md) — Fornire una checklist operativa pronta per nuovi endpoint write (POST/PUT/PATCH/DELETE con side effect).
- [error-handling-api](manual/error-handling-api.md) — Definire un contratto errore uniforme per tutte le API backend Django.
- [payload-validation-api](manual/payload-validation-api.md) — Centralizzare validazioni/coercizioni dei payload JSON API per ridurre logica duplicata nelle view dominio.
- [request-context-api](manual/request-context-api.md) — Assegnare metadati di correlazione request (request_id) e idempotenza (idempotency_key) in modo uniforme per tutte le API.
- [request-parsing-api](manual/request-parsing-api.md) — Centralizzare parsing JSON/body e parsing date ISO per le API Django.

## Utility
- [value-normalizer](manual/value-normalizer.md) — Centralizzare utility riusabili di normalizzazione valori input.

## Altri contenuti
- [gen-bk-docs](manual/gen-bk-docs.md) — Automatizzare la generazione degli indici index.md (e opzionalmente index.ci.md) per docs/it/backend/<area>/, includendo una descrizione breve estratta dalla sezione **Scopo**.
