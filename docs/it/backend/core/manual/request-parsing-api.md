# Request parsing API (Core Django)

## Scopo
Centralizzare parsing JSON/body e parsing date ISO per le API Django.

## Contesto
Helper condivisi disponibili in:
- `apps/core/api/request_parsers.py`

## Input
- `HttpRequest` Django o `Request` DRF
- valori stringa data (`YYYY-MM-DD`)

## Output
- `parse_json_body(...)` -> `dict`
- `parse_iso_date(...)` -> `date | None`

## Regole
- Con una `Request` DRF si usa `request.data`; con un `HttpRequest` Django si decodifica il body in UTF-8.
  - ⚠️ Difetto noto ([F-10](../../../dev/work-in-progress/analisi-be-difetti-emersi-verifica-doc-api-core.md)): un body non UTF-8 solleva `UnicodeDecodeError` (sottoclasse di `ValueError`) senza il messaggio `invalid_json`.
- Body vuoto (`HttpRequest`) -> `{}`
- JSON non valido (o `ParseError` DRF) -> `ValueError("invalid_json")`
- Payload JSON non oggetto -> `ValueError("invalid_payload")`
- `parse_iso_date`: valore vuoto o `None` -> `None`; data non valida -> `ValueError` standard Python

## Dipendenze DB
- Nessuna

## Note di migrazione
- I domini devono evitare parser duplicati locali nelle view.
