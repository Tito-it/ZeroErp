# Request parsing API (Core Django)

## Scopo
Centralizzare parsing JSON/body e parsing date ISO per le API Django.

## Contesto
Helper condivisi disponibili in:
- `apps/core/api/request_parsers.py`

## Input
- `HttpRequest`
- valori stringa data (`YYYY-MM-DD`)

## Output
- `parse_json_body(...)` -> `dict`
- `parse_iso_date(...)` -> `date | None`

## Regole
- JSON non valido -> `ValueError("invalid_json")`
- Payload JSON non oggetto -> `ValueError("invalid_payload")`
- Data non valida -> `ValueError` standard Python

## Dipendenze DB
- Nessuna

## Note di migrazione
- I domini devono evitare parser duplicati locali nelle view.
