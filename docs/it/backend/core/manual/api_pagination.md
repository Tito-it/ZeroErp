# API pagination (Core Django)

## Scopo

Leggere la finestra di ogni lista in un dialetto solo, `limit`/`offset`, e rispondere con l'envelope di lista `{count, results}` (`pagina_con_totale`, [api.md §Paginazione](../../../dev/api.md)).

## Contesto

⛔ **Un dialetto solo: `limit`/`offset`** (decisione di Tid del 2026-10-21).
Ogni endpoint lista del backend legge la finestra **solo** dalla query string,
con un building block solo. Fino a quel giorno ne convivevano due: le liste
offset-based (`limit`/`offset`) e una ventina di liste page-based
(`page`/`page_size`: dashboard vendite, lotti, tracciamento, note, lookup
codici, tabelle di configurazione, audit dei permessi, ricerca globale,
pagamenti), ognuna col suo helper e con regole di fuori-limite diverse. La
regola completa e la storia stanno in [api.md §Paginazione](../../../dev/api.md).

I building block, tutti in `apps/core/api/payload_validators.py` salvo dove
indicato:

- `pagina_da_query(qp, *, default_limit=DEFAULT_LIMIT, max_limit=MAX_LIMIT)` —
  la finestra di **ogni** lista: ritorna `(limit, offset)`. Rifiuta
  `page`/`page_size` (`richiedi_limit_offset`), legge i due interi con
  `qp_int_strict` e rifiuta quelli fuori limite (`limit` fuori da
  1..`max_limit`, `offset` negativo): non li riporta nei limiti.
- `parse_list_params(qp, *, default_order, default_limit, max_limit)` — il
  bundle delle liste configurabili (`search`, `limit`, `offset`, `order_by`,
  `order_dir`): la finestra la prende da `pagina_da_query`. Dal 2026-11-24 non
  ritorna più `page`.
- `limiti_pagina(limit, offset, *, tetto=MAX_LIMIT)` in `apps/core/db/_helpers.py`
  — il clamp: limite fra 1 e `tetto`, offset non negativo. È la difesa
  interna dei **repository**, non la risposta all'utente: la finestra che
  arriva dalla query string l'ha già validata `pagina_da_query`.
- `pagina_con_totale(results, totale)` in `apps/core/services/list_helpers.py`
  — l'envelope di **ogni** lista paginata: `{"count": totale, "results": …}`,
  con `count` il totale della query. I campi propri di una lista stanno
  accanto (`{**pagina_con_totale(…), "stati": …}`).
- ⛔ `envelope_da_offset`, `paginated_envelope` e `pagina_di` sono **ritirati**
  dal 2026-11-24 (D-1 di brief-be-fe-BB-audit): davano la forma lunga
  `{count, page, page_size, total_pages, results}`, che ripeteva come pagina la
  finestra chiesta con `limit`/`offset`.
- `parametri_finestra(*, default_limit=None, max_limit=None)` in
  `apps/core/api/openapi_params.py` — i due `OpenApiParameter` `limit`/`offset`
  dello schema OpenAPI, con default e massimo letti dalle costanti (o da quelli
  passati, che devono essere gli stessi dati a `pagina_da_query`).

Default e massimo stanno in `apps/core/api/constants.py`: `DEFAULT_LIMIT` (25),
`MAX_LIMIT` (200), `DEFAULT_LIMIT_EVENTI` (100, liste di eventi). Una lista che
ne vuole altri li passa a `pagina_da_query` (per esempio la ricerca globale:
default 25, max 100; le segnalazioni e i task run di un lotto: max 500,
`LOTTO_LISTE_PAGINA_MAX`); la pagina del singolo endpoint dice quali.

⛔ Le classi DRF `StandardPageNumberPagination` / `StandardCursorPagination`
(`apps/core/api/pagination.py`) e l'esempio che le usava
(`apps/core/api/examples/domain_search_example.py`) sono stati **rimossi il
2026-10-21** (ok Tid): nessuna view le usava, e una lista che le avesse
adottate sarebbe tornata a parlare `page`/`page_size`. `REST_FRAMEWORK` in
`settings.py` non dichiara una paginazione di default.

## Input

- `limit` (query string): righe per pagina, default `DEFAULT_LIMIT` (25), max
  `MAX_LIMIT` (200), salvo i valori dichiarati dalla lista.
- `offset` (query string): righe da saltare, default `0`.

## Output

- `pagina_da_query` → `(limit, offset)` validi, oppure `ValueError` → 400
  `E_VALIDATION_INPUT`.
- Risposta HTTP: envelope di lista `{"count", "results"}` (`pagina_con_totale`),
  più i campi propri della lista. Niente `page`/`page_size`/`total_pages`
  (dal 2026-11-24; fino a quel giorno la risposta li ricavava dall'offset). I
  cruscotti che riportano un offset oltre la fine all'ultima pagina lo
  dichiarano in `offset_effettivo`.

## Regole

- `page` o `page_size` presenti in query → 400 `E_VALIDATION_INPUT`
  (`page_non_ammesso_usare_limit_offset` /
  `page_size_non_ammesso_usare_limit_offset`), dal 2026-10-21 su ogni lista
  (dal 2026-10-20 sulle sole offset-based, che prima li ignoravano).
- `limit` o `offset` non interi (anche vuoti, `?limit=`) → 400
  `E_VALIDATION_INPUT` (`limit_invalid` / `offset_invalid`). Niente più ripiego
  muto sul default (`qp_int`, ritirato).
- Fuori limiti → 400 `E_VALIDATION_INPUT` (decisione di Tid del 2026-10-21):
  `limit` fuori da 1..`max_limit` → `limit_fuori_limiti_1_<max>` (per esempio
  `limit_fuori_limiti_1_200`), `offset` negativo → `offset_negativo`. Fino a
  quel giorno la finestra si riportava nei limiti in silenzio: chi chiedeva 500
  righe ne riceveva 200 credendole tutte.
- La view legge e valida la finestra; service e repository la ricevono già
  valida e **non** ripetono il controllo (i guard di `pipeline_service` e
  `commesse_service`, che rispondevano `E_PIPELINE_VALIDATION` /
  `E_COMMESSA_VALIDATION`, sono stati tolti lo stesso giorno). Nei repository
  resta il clamp `limiti_pagina` come difesa interna.
- ⛔ `validate_pagination` (`apps/core/services/list_helpers.py`, il building
  block delle liste page-based) è **ritirato** dal 2026-10-21.
- Nello schema OpenAPI la finestra si dichiara con `*parametri_finestra(...)`,
  mai a mano.

## Dipendenze DB

- Nessuna diretta.

## Note di migrazione

- Allineare endpoint lista/search alla policy `docs/it/dev/Policy-ricerca-e-paginazione(API-DB).md`.
- 2026-10-21: pagina riscritta sul dialetto unico. Prima descriveva
  `validate_pagination` (page-based, che **rifiutava** i valori fuori limite)
  accanto alle classi DRF.
- 2026-10-21 (stesso giorno): il fuori limite diventa un 400; rimosse le
  classi DRF e l'esempio `domain_search_example.py`.
- 2026-11-24: la risposta di ogni lista diventa `{count, results}`
  (`pagina_con_totale`, D-1 di brief-be-fe-BB-audit); ritirati
  `envelope_da_offset`, `paginated_envelope` e `pagina_di`.
