# API search validation (Core Django)

## Scopo
Evitare query di ricerca troppo generiche che degradano performance e selettivita`.

## Contesto
Helper condiviso in `apps/core/api/search_validators.py`.

## Input
`require_min_search_length(term, *, min_length=3, field_name="term")`:
- `term: str | None`
- `min_length` (default 3)
- `field_name` (default `term`)

`validate_order_params(order_by, order_dir)`:
- `order_by: str | None` — deve stare in `ALLOWED_ORDER_COLUMNS`
  (`ragione_sociale_completa`, `soggetto_codice`, `id_fiscale_univoco`). È il **mirror
  dichiarato** della whitelist di `p_order_by` in `script.fn_search_soggetti_universale`: serve
  a dare il 400 `E_SEARCH_VALIDATION` invece del rifiuto del DB. Lo presidia
  `core/tests/db/test_search_ordinamento_db` (e2e). `utility_list` non è ordinabile dal
  2026-10-10: è un aggregato calcolato per le sole righe della pagina
- `order_dir: str | None` — `ASC` o `DESC` (case-insensitive, default `ASC`)

## Output
- Nessuna eccezione se valido.
- `require_min_search_length`: `ServiceError` (`E_SEARCH_VALIDATION`, 400) se il termine e` troppo corto.
- `validate_order_params`: coppia normalizzata `(order_by, ORDER_DIR)`, oppure `(None, None)` se
  `order_by` e` assente; `ServiceError` (`E_SEARCH_VALIDATION`, 400) se colonna o direzione
  non sono ammesse.

## Regole
- `None` e` ammesso (nessun filtro testuale).
- `term.strip()` deve avere lunghezza minima configurata.
- La regola minima consigliata e` `>= 3` per allineamento policy API/DB.

## Dipendenze DB
- Nessuna diretta.

## Note di migrazione
- Usare il validator core invece di controlli locali nelle view.
- Esempio applicativo: `SearchUniversaleView` in `apps/core/api/search_view.py` (`is_search_endpoint`, `SearchBurstRateThrottle`, `require_min_search_length`). L'esempio `domain_search_example.py` è stato rimosso il 2026-10-21.
