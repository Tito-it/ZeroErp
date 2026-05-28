# Brief DB — Vista lista offerte con `is_attiva` (simmetria preventivi)

> **Status**: ✅ **COMPLETATO** — 2026-05-27. Team DB ha consegnato la vista
> `vendite.vw_offerte_commerciali_list` con `is_attiva` (semantica: stato
> NOT IN ('SUPERATA','ANNULLATA')) + `has_next_revisione` (EXISTS figlio).
> Soggetto risolto via `istanze_utilities` (1 join, sempre valorizzato).
> Backend `offerte_repository.list_offerte` + `count_offerte` ora leggono
> dalla vista con param `solo_attiva` (default true); il toggle FE
> "Mostra storico revisioni" è in `OfferteSearchTable`.
> **Target team**: DB (`dev/db-tid`)
> **Origine**: allineamento UI lista offerte commerciali al pattern preventivi
> (filtro "mostra solo revisione attiva" / toggle "mostra storico").
> **No produzione**: breaking change ammessi (memoria `project_no_produzione_solo_sviluppo`).

---

## Richiesta

Speculare a `vendite.vw_preventivi_list`:

- Nuova vista `vendite.vw_offerte_commerciali_list` (o nome che preferite)
  che proietta le offerte ed espone la colonna calcolata **`is_attiva`** con
  la stessa semantica preventivi: "non esiste una revisione successiva nello
  stesso lineage che NON sia abortita". Le offerte sono catenate via
  `revisione_padre_id`; "abortita" si appoggia al concetto già canonico
  (stato ANNULLATA / `is_abortito_snapshot` o equivalente).
- Opzionale per coerenza UX: `has_next_revisione` (qualunque rev successiva,
  anche abortita) — campo già esposto in `vw_preventivi_list`.

Il BE filtra `WHERE is_attiva IS TRUE` quando `solo_attiva=true` (default),
mostra storico completo quando `false`.

## Motivazione

Oggi la lista offerte legge direttamente da `vendite.offerte_commerciali`
([offerte_repository.py:381](../../../backend/apps/vendite/db/offerte_repository.py))
senza calcolo `is_attiva` → mostra sempre tutte le revisioni, comportamento
opposto rispetto ai preventivi. Allineamento simmetrico richiesto.

## Fuori scope

Niente nuove colonne in tabella, niente trigger, niente migrations DDL:
tutta logica nella vista.

---

*Brief DB sintetico — il dettaglio implementativo (definizione vista,
predicato esatto, indici) è a discrezione del team DB.*
