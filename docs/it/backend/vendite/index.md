# Area 'vendite' (Backend)

## API
- [api_attivita_pipeline_status](manual/api_attivita_pipeline_status.md) — Esporre via HTTP lo stato corrente della pipeline attivita fatturabili di un lotto, con riepilogo aggregato per branch.
- [api_attivita_task_runs](manual/api_attivita_task_runs.md) — Esporre via HTTP i task run runtime del lotto attivita fatturabili per monitoraggio operativo e diagnostica pipeline.
- [api_lotti_list](manual/api_lotti_list.md) — Esporre via HTTP l'elenco paginato dei lotti di fatturazione con filtri opzionali e decodifica delle FK.
- [api_lotto_fatture_list](manual/api_lotto_fatture_list.md) — Esporre via HTTP l'elenco paginato delle fatture appartenenti a un lotto, con decodifiche FK, filtri opzionali e ordinamento configurabile.
- [api_lotto_segnalazioni_summary](manual/api_lotto_segnalazioni_summary.md) — Esporre via HTTP il riepilogo segnalazioni attive di un lotto, con indicazione di blocco avanzamento step.
- [api_lotto_task_runs](manual/api_lotto_task_runs.md) — Esporre via HTTP i task run runtime di un lotto per monitoraggio operativo e diagnostica pipeline.
- [api_reset_lotto_draft](manual/api_reset_lotto_draft.md) — Esporre via HTTP il reset tecnico di un lotto MASSIVO in DRAFT.
- [api_reset_lotto_fattura_draft](manual/api_reset_lotto_fattura_draft.md) — Esporre via HTTP il reset tecnico di una singola fattura in un lotto MASSIVO in DRAFT.
- [api_run_attivita_pipeline](manual/api_run_attivita_pipeline.md) — Esporre via HTTP l'avvio della pipeline attivita fatturabili.
- [api_run_lotto_pipeline](manual/api_run_lotto_pipeline.md) — Esporre via HTTP l'avvio della pipeline lotto vendite.

## Funzioni
- [fn_execute_pipeline_step](funzioni/fn_execute_pipeline_step.md) — Eseguire un singolo step di pipeline, applicando i task definiti nello step corrente.
- [pr_run_lotto_pipeline](funzioni/pr_run_lotto_pipeline.md) — Orchestrare l'esecuzione della pipeline di fatturazione per un lotto, gestendo:

## Altri contenuti
- [fn_generate_fatture_righe](manual/fn_generate_fatture_righe.md) — Generare in Django le righe fattura a partire da attivita_fatturabili lockate sul lotto.
- [fn_group_attivita_fatturabili](manual/fn_group_attivita_fatturabili.md) — Costruire in Django la chiave di aggregazione delle attivita fatturabili.
- [fn_prepare_sdi_payload_lotto](manual/fn_prepare_sdi_payload_lotto.md) — Reperire dal database il dataset SDI di un lotto, aprendo/riusando i tentativi di invio e restituendo le righe da usare per la generazione file.
- [fn_reset_lotto_draft](manual/fn_reset_lotto_draft.md) — Eseguire il reset tecnico di un lotto MASSIVO in DRAFT invocando la funzione DB.
- [fn_reset_lotto_fattura_draft](manual/fn_reset_lotto_fattura_draft.md) — Eseguire il reset tecnico di una singola fattura in un lotto MASSIVO DRAFT.
- [pr_run_attivita_pipeline](manual/pr_run_attivita_pipeline.md) — Orchestrare l'esecuzione della pipeline attivita fatturabili per un lotto, gestendo:
- [test_attivita_pipeline](manual/test_attivita_pipeline.md) — Descrivere la struttura, i pattern e la copertura dei test per il dominio ATTIVITA_FATTURABILI della pipeline vendite (BE-3).
