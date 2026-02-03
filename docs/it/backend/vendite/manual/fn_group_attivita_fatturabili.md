# fn_group_attivita_fatturabili (Django)

## Scopo
Costruire in Django la chiave di aggregazione delle attivita fatturabili.

## Contesto
La logica di `vendite.fn_group_attivita_fatturabili()` e` stata portata in:
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
- Stato attuale: migrazione completata lato Python.
- La funzione SQL puo` restare come compatibilita` storica/transitoria.
