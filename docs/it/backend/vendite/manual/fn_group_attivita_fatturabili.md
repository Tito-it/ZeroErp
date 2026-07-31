# fn_group_attivita_fatturabili (Django)

## Scopo
Costruire in Django la chiave di aggregazione delle attivita fatturabili.

> ⚠️ **Il nome e` quello dell'entrypoint Python** (`pipeline_service.fn_group_attivita_fatturabili`),
> **non** di una funzione SQL. La funzione DB omonima **non esiste piu`**: rimossa
> il 2026-07-28 col changeset `20260728-21`.

## Contesto
La logica di `vendite.fn_group_attivita_fatturabili()` (funzione DB **rimossa**) e` stata portata in:
- `apps/vendite/services/fatture_righe_service.py` (`group_attivita_fatturabili`)
- `apps/vendite/services/pipeline_service.py` (`fn_group_attivita_fatturabili`)

## Input
- `attivita_id`

## Output
- `group_key` strutturata (dict) con campi articolo/destinazione/uom/iva/competenza/regole

## Regole
- Deterministica e stabile.
- `dest_billing_account_id` e` sempre BA reale da attivita.
- `uom_id` usa fallback da articolo se assente su attivita.
- Competenza valorizzata solo se diversa dalla singola data attivita.
- Error handling centralizzato via `ErrorManager`.

## Dipendenze DB
- Tabelle `vendite.attivita_fatturabili`, `catalogo.articoli`, `vendite.articolo_regole_fatturazione`.

## Matrice responsabilita` (Python vs DB)
- Python: composizione chiave di grouping, validazioni input, politica errori.
- DB: source of truth dei dati (attivita/articolo/regole) e vincoli di integrita`.

## Note di migrazione
- Stato attuale: migrazione completata lato Python (dal 2026-02-03, commit `ece04a5ff`).
- **La funzione SQL e` stata RIMOSSA** il 2026-07-28 (changeset `20260728-21`),
  insieme a `vendite.fn_generate_fatture_righe` che era il suo unico chiamante.

  ⚠️ Qui prima si leggeva: *«la funzione SQL puo` restare come compatibilita`
  storica/transitoria»*. Vale la stessa avvertenza del manuale gemello: quella
  formula ha reso indistinguibile un residuo da un'implementazione viva, e ci si
  e` sviluppato sopra per un giorno. Storia completa:
  `docs/it/dev/work-in-progress/brief-db-ritiro-generatore-righe-fattura-sql.md`.
