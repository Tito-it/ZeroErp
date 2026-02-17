# Area 'vendite' (Backend)

## API
- [api_reset_lotto_draft](manual/api_reset_lotto_draft.md) — Esporre via HTTP il reset tecnico di un lotto MASSIVO in DRAFT.
- [api_reset_lotto_fattura_draft](manual/api_reset_lotto_fattura_draft.md) — Endpoint applicativo che invoca il servizio Python fn_reset_lotto_fattura_draft.
- [api_run_lotto_pipeline](manual/api_run_lotto_pipeline.md) — Esporre via HTTP l'avvio della pipeline lotto vendite.

## Funzioni
- [fn_execute_pipeline_step](funzioni/fn_execute_pipeline_step.md) — Eseguire un singolo step di pipeline, applicando i task definiti nello step corrente.
- [pr_run_lotto_pipeline](funzioni/pr_run_lotto_pipeline.md) — Orchestrare l'esecuzione della pipeline di fatturazione per un lotto, gestendo: - avanzamento step configurati - aggiornamento stato lotto/job - logging di fase e gestione errori applicativi

## Altri contenuti
- [fn_generate_fatture_righe](manual/fn_generate_fatture_righe.md) — Generare in Django le righe fattura a partire da attivita_fatturabili lockate sul lotto.
- [fn_group_attivita_fatturabili](manual/fn_group_attivita_fatturabili.md) — Costruire in Django la chiave di aggregazione delle attivita fatturabili.
- [fn_prepare_sdi_payload_lotto](manual/fn_prepare_sdi_payload_lotto.md) — Reperire il dataset SDI del lotto dal DB con apertura/riuso tentativi.
- [fn_reset_lotto_draft](manual/fn_reset_lotto_draft.md) — Eseguire il reset tecnico di un lotto MASSIVO in DRAFT invocando la funzione DB.
- [fn_reset_lotto_fattura_draft](manual/fn_reset_lotto_fattura_draft.md) — Eseguire il reset tecnico di una singola fattura in un lotto MASSIVO DRAFT.
