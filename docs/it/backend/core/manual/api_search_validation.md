# API search validation (Core Django)

## Scopo
Evitare query di ricerca troppo generiche che degradano performance e selettivita`.

## Contesto
Helper condiviso in `apps/core/api/search_validators.py`.

## Input
- `term: str | None`
- `min_length` (default 3)
- `field_name` (default `term`)

## Output
- Nessuna eccezione se valido.
- `ServiceError` (`E_PIPELINE_VALIDATION`) se il termine e` troppo corto.

## Regole
- `None` e` ammesso (nessun filtro testuale).
- `term.strip()` deve avere lunghezza minima configurata.
- La regola minima consigliata e` `>= 3` per allineamento policy API/DB.

## Dipendenze DB
- Nessuna diretta.

## Note di migrazione
- Usare il validator core invece di controlli locali nelle view.
- Esempio applicativo: `apps/core/api/examples/domain_search_example.py`.
