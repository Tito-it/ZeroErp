# API domain conventions (Core Django)

## Scopo
Definire uno standard unico per costruire future API di dominio.

## Contesto
Per ridurre duplicazioni tra app dominio usare helper core:
- `apps/core/api/endpoint_helpers.py`
- `apps/core/api/request_parsers.py`
- `apps/core/api/error_responses.py`
- Template di partenza: `apps/core/api/examples/domain_post_example.py`

## Input
- `HttpRequest` con body JSON
- handler dominio che riceve `payload: dict`

## Output
- `JsonResponse` con contratto uniforme successo/errore

## Regole
- Endpoint POST JSON: usare `handle_post_json(request, handler=...)`.
- Nel handler dominio: validare campi specifici e invocare service.
- Errori applicativi: sempre via `ErrorManager`/`ServiceError`.
- Niente parser JSON/date duplicati nelle singole app dominio.

## Dipendenze DB
- Nessuna diretta (layer API)

## Note di migrazione
- Vendite usa gia` questo pattern su `run_lotto_pipeline`.
- Le nuove API (acquisti/anagrafiche/...) devono partire da questo standard.
