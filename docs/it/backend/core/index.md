# Area 'core' (Backend)

## API
- [api-domain-conventions](manual/api-domain-conventions.md) — Definire uno standard unico per costruire future API di dominio.
- [api_write_checklist](manual/api_write_checklist.md) — Fornire una checklist operativa pronta per nuovi endpoint write (POST/PUT/PATCH/DELETE con side effect).
- [error-handling-api](manual/error-handling-api.md) — Definire un contratto errore uniforme per tutte le API backend Django.
- [payload-validation-api](manual/payload-validation-api.md) — Centralizzare validazioni/coercizioni dei payload JSON API per ridurre logica duplicata nelle view dominio.
- [request-context-api](manual/request-context-api.md) — Assegnare metadati di correlazione request (request_id) e idempotenza (idempotency_key) in modo uniforme per tutte le API.
- [request-parsing-api](manual/request-parsing-api.md) — Centralizzare parsing JSON/body e parsing date ISO per le API Django.

## Utility
- [value-normalizer](manual/value-normalizer.md) — Centralizzare utility riusabili di normalizzazione valori input.

## Altri contenuti
- [gen-bk-docs](manual/gen-bk-docs.md) — Automatizzare la generazione degli indici index.md (e opzionalmente index.ci.md) per docs/it/backend/<area>/, includendo una descrizione breve estratta dalla sezione **Scopo**.
