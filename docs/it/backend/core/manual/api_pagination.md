# API pagination (Core Django)

## Scopo
Fornire configurazioni DRF standard per paginazione coerente su endpoint list/search.

## Contesto
Due strumenti, con ruoli diversi:

- `validate_pagination(page, page_size, *, error_code, function_name)` in
  `apps/core/services/list_helpers.py` — il building block usato dai service
  delle liste page-based. Rifiuta con errore (codice passato dal chiamante)
  `page < 1` e `page_size` fuori da 1..200 — **non** li riporta nei limiti — e
  restituisce l'offset `(page - 1) * page_size`.
- Le classi DRF `StandardPageNumberPagination` / `StandardCursorPagination` in
  `apps/core/api/pagination.py`: oggi nessuna view di produzione le usa, compaiono
  solo nell'esempio `apps/core/api/examples/domain_search_example.py`.

Alcuni endpoint trattano ancora `page_size` in locale (per esempio lo riducono
a 200 in silenzio invece di rifiutarlo): la pagina del singolo endpoint dice quale.

## Input
- `page`, `page_size` (query string) validati da `validate_pagination`.
- Classi DRF: `page` / `page_size` con `StandardPageNumberPagination`; cursore
  con `StandardCursorPagination`.

## Output
- `validate_pagination`: `page >= 1`, `page_size` 1..200, altrimenti errore.
- Paginazione page-number DRF: page size default 50, max 200.
- Paginazione cursor DRF: page size **fisso** 50 (nessun `page_size_query_param`:
  il client non puo' cambiarlo), ordering `-data_update`.

## Regole
- Usare page-number per dataset piccoli/medi e filtri semplici.
- Usare cursor per dataset grandi/ordinamenti stabili.
- Limite massimo pagina allineato alla policy: 200.
- Le view dominio non devono ridefinire limiti incoerenti senza motivazione.

## Dipendenze DB
- Nessuna diretta.

## Note di migrazione
- Allineare endpoint lista/search alla policy `docs/it/dev/Policy-ricerca-e-paginazione(API-DB).md`.
