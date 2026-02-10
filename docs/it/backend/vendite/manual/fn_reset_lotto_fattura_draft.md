# Reset lotto fattura draft (Django)

## Scopo
Eseguire il reset tecnico di una singola fattura in un lotto MASSIVO DRAFT.

## Contesto
Wrapper applicativo di `vendite.fn_reset_lotto_fattura_draft`, mantiene la logica critica in DB.

## Input
- `lotto_id`: id lotto (obbligatorio, > 0)
- `fattura_id`: id fattura (obbligatorio, > 0)

## Output
- Dict con: `updated_attivita`, `deleted_fatture`, `deleted_righe`

## Regole
- Validazione `lotto_id` e `fattura_id`.
- Nessuna logica duplicata lato Python.

## Dipendenze DB
- `vendite.fn_reset_lotto_fattura_draft`

## Note di migrazione
- Wrapper Django introdotto per esporre l'azione in API senza duplicare la logica SQL.
