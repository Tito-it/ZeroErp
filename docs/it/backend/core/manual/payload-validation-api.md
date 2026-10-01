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

- `qp_bool`, `qp_bool_optional`, `qp_int`, `qp_int_strict`, `qp_int_optional`,
  `qp_iso_date_optional`, `qp_str`, `qp_str_upper`

Liste paginate:

- `parse_list_params(qp, *, default_order="descrizione", default_limit=25, max_limit=200)`
- `paginated_envelope(results, total_count, page, page_size)`

## Output
- valore coerente oppure `ValueError(f"{key}_invalid")` su input non valido
  (le varianti `qp_int`, `qp_bool`, `qp_str` non sollevano: ripiegano sul default).

## Regole
- Le view non devono parsare tipi a mano: usare validator core.
- Traduzione del `ValueError`:
  - dentro `handle_post_json` (`apps/core/api/endpoint_helpers.py`) → `400 {"error": "invalid_payload"}`;
    il nome del campo si perde;
  - altrove, quando arriva all'envelope standard → `E_VALIDATION_INPUT` (400) con il
    messaggio (`<key>_invalid`).

> ⚠️ Difetto noto (E-6): l'envelope `invalid_payload` ha `error` stringa e non oggetto.
> Vedi [analisi difetti](../../../dev/work-in-progress/analisi-be-difetti-emersi-verifica-doc-api-core.md).

## Dipendenze DB
- Nessuna

## Note di migrazione
- Vendite usa i validator core su `run_lotto_pipeline`.
