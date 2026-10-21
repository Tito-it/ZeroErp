# Payload validation API (Core Django)

## Scopo
Centralizzare validazioni/coercizioni dei payload JSON API per ridurre logica duplicata nelle view dominio.

## Contesto
Validator condivisi in:
- `apps/core/api/payload_validators.py`

Per la validazione dei payload **nei service** (CRUD admin e simili) il building
block e' `PayloadValidator` / `map_integrity_error` in
`apps/core/services/payload_helpers.py`; questo modulo copre le view.

## Funzioni

Campi del body JSON (`payload: dict`, chiave `key`):

- `optional_int(payload, key, *, zero_as_none=False)` — `int` o `None`
- `optional_bool(payload, key, default=False)` — `bool`; se assente ritorna `default`
- `optional_iso_date(payload, key)` — `date` o `None`
- `optional_uuid(payload, key)` — `str` UUID normalizzato o `None` (`0`, `"0"`, `""` → `None`)

Query string (`raw: str | None`):

- `qp_bool_optional`, `qp_int_strict`, `qp_int_optional`,
  `qp_iso_date_optional`, `qp_str`, `qp_str_upper` (`qp_bool` e `qp_int`, che
  ripiegavano sul default in silenzio, sono ritirati)

Liste paginate:

- `pagina_da_query(qp, *, default_limit=DEFAULT_LIMIT, max_limit=MAX_LIMIT)` —
  `(limit, offset)` di ogni lista: `page`/`page_size` presenti → `ValueError`
  (`page_non_ammesso_usare_limit_offset` / `page_size_non_ammesso_usare_limit_offset`),
  valori non interi → `limit_invalid`/`offset_invalid`, limiti da `limiti_pagina`
  (dal 2026-10-21 il solo dialetto delle liste)
- `parse_list_params(qp, *, default_order="descrizione", default_limit=DEFAULT_LIMIT, max_limit=MAX_LIMIT)`
- `envelope_da_offset(results, total_count, *, limit, offset)` — l'envelope
  paginato da una finestra `limit`/`offset`
- `pagina_di(offset, limit)` — la pagina (da 1) che la finestra mostra
- `paginated_envelope(results, total_count, page, page_size)`

## Output
- valore coerente oppure `ValueError(f"{key}_invalid")` su input non valido
  (`qp_str` e `qp_str_upper` non sollevano: normalizzano a `None`).

## Regole
- Le view non devono parsare tipi a mano: usare validator core.
- Traduzione del `ValueError`: ovunque, anche dentro `handle_post_json`, arriva
  all'envelope standard come `E_VALIDATION_INPUT` (400) col suo messaggio
  (`<key>_invalid`). Fino al 2026-10-07 dentro `handle_post_json` usciva
  `{"error": "invalid_payload"}` e il nome del campo si perdeva (E-6, chiuso).

## Dipendenze DB
- Nessuna

## Note di migrazione
- Vendite usa i validator core su `run_lotto_pipeline`.
