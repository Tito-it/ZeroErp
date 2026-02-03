# fn_generate_fatture_righe (Django)
  
## Scopo
Generare in Django le righe fattura a partire da `attivita_fatturabili` lockate sul lotto.

## Contesto
La logica di `vendite.fn_generate_fatture_righe()` e` stata portata in:
- `apps/vendite/services/fatture_righe_service.py` (`generate_fatture_righe`)
- `apps/vendite/services/pipeline_service.py` (`fn_generate_fatture_righe`)

## Input
- `lotto_id`
- `dry_run` (default `False`)

## Output
- numero righe elaborate
- aggiornamento `fattura_riga_id` e `fatturato` sulle attivita processate (se non dry-run)

## Regole
- Idempotenza per riga.
- Header fattura ottenuto via `fn_get_or_create_fattura_header`.
- Group key calcolata via servizio Python `group_attivita_fatturabili`.
- In `dry_run` conta gli elementi ma non esegue insert/update.
- Error handling centralizzato via `ErrorManager`.

## Dipendenze DB
- Tabelle `vendite.attivita_fatturabili`, `vendite.fatture_righe`, `vendite.fatture`.
- Funzione DB `vendite.fn_get_or_create_fattura_header(...)` per header.
- Vincoli di integrita`/consistenza restano in DB.

## Matrice responsabilita` (Python vs DB)
- Python: loop applicativo, costruzione metadati riga, gestione `dry_run`, policy errori.
- DB: locking/selezione dati, generazione header fattura, persistenza righe e regole di integrita`.

## Note di migrazione
- Stato attuale: migrazione logica completata lato Python.
- La funzione SQL puo` restare per compatibilita` storica/transitoria.
