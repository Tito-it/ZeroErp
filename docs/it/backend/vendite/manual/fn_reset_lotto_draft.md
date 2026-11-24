# Annullo del lotto in DRAFT (Django)

## Scopo
Annullare un lotto in DRAFT invocando la funzione DB, da `pipeline_service.fn_annulla_lotto_da_draft`.

## Contesto
Fa da wrapper applicativo a `vendite.fn_annulla_lotto_da_draft`, mantenendo la logica critica in DB. La catena:
`pipeline_service.fn_annulla_lotto_da_draft` → `LottoResetService.annulla_lotto_da_draft` →
`VenditePipelineRepository.annulla_lotto_da_draft`. Il nome del file resta quello storico.
La chiama solo l'endpoint `reset-draft` ([api_reset_lotto_draft](api_reset_lotto_draft.md)): non è più un task di pipeline.

## Input
- `lotto_id`: id lotto (obbligatorio, > 0)

## Output
- Dict con: `updated_lotti`, `updated_attivita`, `deleted_fatture`, `deleted_righe`

## Regole
- Validazione `lotto_id` obbligatoria.
- Nessuna logica duplicata lato Python: tutta la coerenza e` delegata al DB.

## Dipendenze DB
- `vendite.fn_annulla_lotto_da_draft`

## Note di migrazione
- Wrapper Django introdotto per esporre l'azione in API senza duplicare la logica SQL.
- 2026-11-24 — ritirato il task di pipeline `reset_lotto_draft` (D-I) che la usava come rollback di EMESSA:
  resta il solo chiamante HTTP. La funzione DB si chiama `fn_annulla_lotto_da_draft` da D-L.
