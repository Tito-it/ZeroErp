# Reset lotto draft (Django)

## Scopo
Eseguire il reset tecnico di un lotto MASSIVO in DRAFT invocando la funzione DB.

## Contesto
Fa da wrapper applicativo a `vendite.fn_reset_lotto_draft`, mantenendo la logica critica in DB.
Usata da API dedicate e da processi backoffice.

## Input
- `lotto_id`: id lotto (obbligatorio, > 0)

## Output
- Dict con: `updated_lotti`, `updated_attivita`, `deleted_fatture`, `deleted_righe`

## Regole
- Validazione `lotto_id` obbligatoria.
- Nessuna logica duplicata lato Python: tutta la coerenza e` delegata al DB.

## Dipendenze DB
- `vendite.fn_reset_lotto_draft`

## Note di migrazione
- Wrapper Django introdotto per esporre l'azione in API senza duplicare la logica SQL.
