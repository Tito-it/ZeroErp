# fn_prepare_sdi_payload_lotto (Django)

## Scopo
Reperire dal database il dataset SDI di un lotto, aprendo/riusando i tentativi di invio e restituendo le righe da usare per la generazione file.

## Contesto
Facade Python per la funzione SQL `vendite.fn_prepare_sdi_payload(...)`.

Implementazione:
- `apps/vendite/services/pipeline_service.py` (`fn_prepare_sdi_payload_lotto`)
- `apps/vendite/db/pipeline_repository.py` (`run_prepare_sdi_payload_lotto_task`)

La logica di idempotenza e apertura tentativi resta centralizzata lato DB.

## Input
- `lotto_id` (obbligatorio)
- `stato_sdi_codice_interno` (default `DA_INVIARE`)
- `force_new_tentativo` (default `False`)

## Output
Lista tipizzata `SdiPayloadRow` con:
- `fattura_sdi_id`, `fattura_id`, `tentativo_num`, `stato_sdi_id`
- `codice_documento`, `numero_fattura`, `data_fattura`
- `billing_account_id`, `emittente_soggetto_ruolo_id`, `valuta_id`
- `totale_a_pagare`

## Regole
- `force_new_tentativo=False`: riusa tentativo aperto (`data_invio IS NULL`) se presente.
- `force_new_tentativo=True`: forza nuovo tentativo incrementale.
- Nessuna duplicazione di logica applicativa: il backend non ricalcola filtri/validazioni SDI, delega al DB.

## Dipendenze DB
- `vendite.fn_prepare_sdi_payload(...)`
- `vendite.fatture_sdi`
- `vendite.fatture_sdi_eventi`

## Note di migrazione
- Questa facade e` usabile sia dal task pipeline (`prepare_sdi_payload_lotto`) sia da processi applicativi esterni alla pipeline.
