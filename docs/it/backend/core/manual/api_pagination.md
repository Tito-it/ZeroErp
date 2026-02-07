# API pagination (Core Django)

## Scopo
Fornire configurazioni DRF standard per paginazione coerente su endpoint list/search.

## Contesto
Helper definiti in `apps/core/api/pagination.py`.

## Input
- Parametri pagina DRF (`page`, `page_size`) con `StandardPageNumberPagination`.
- Cursor DRF con `StandardCursorPagination`.

## Output
- Paginazione page-number: page size default 50, max 200.
- Paginazione cursor: page size default 50, max 200, ordering `-data_update`.

## Regole
- Usare page-number per dataset piccoli/medi e filtri semplici.
- Usare cursor per dataset grandi/ordinamenti stabili.
- Limite massimo pagina allineato alla policy: 200.
- Le view dominio non devono ridefinire limiti incoerenti senza motivazione.

## Dipendenze DB
- Nessuna diretta.

## Note di migrazione
- Allineare endpoint lista/search alla policy `docs/it/dev/Policy-ricerca-e-paginazione(API-DB).md`.
