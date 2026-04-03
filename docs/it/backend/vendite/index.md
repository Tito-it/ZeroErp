# Area 'vendite' (Backend)

## API
- [api_commessa_attivita](manual/api_commessa_attivita.md) — Esporre via HTTP la lista paginata delle attività (commesse_attivita) di una commessa, con filtri opzionali per stato emissione, stato approvazione e mese di competenza.
- [api_commessa_stato](manual/api_commessa_stato.md) — Esporre via HTTP lo stato e i contatori aggregati di una singola commessa, per dashboard e monitoraggio avanzamento.
- [api_commesse_push_log](manual/api_commesse_push_log.md) — Esporre via HTTP il dettaglio di un singolo push log commesse, per consultazione operativa e diagnostica delle esecuzioni push.
- [api_listini](manual/api_listini.md) — Esporre via HTTP la gestione completa dei listini vendite: anagrafica listino, versioni temporali, righe prezzo, associazioni di contesto e test del resolver prezzo.
- [api_lotti_list](manual/api_lotti_list.md) — Esporre via HTTP l'elenco paginato dei lotti di fatturazione con filtri opzionali e decodifica delle FK.
- [api_lotto_fatture_list](manual/api_lotto_fatture_list.md) — Esporre via HTTP l'elenco paginato delle fatture appartenenti a un lotto, con decodifiche FK, filtri opzionali e ordinamento configurabile.
- [api_lotto_segnalazioni_summary](manual/api_lotto_segnalazioni_summary.md) — Esporre via HTTP il riepilogo segnalazioni attive di un lotto, con indicazione di blocco avanzamento step.
- [api_lotto_task_runs](manual/api_lotto_task_runs.md) — Esporre via HTTP i task run runtime di un lotto per monitoraggio operativo e diagnostica pipeline.
- [api_reset_lotto_draft](manual/api_reset_lotto_draft.md) — Esporre via HTTP il reset tecnico di un lotto MASSIVO in DRAFT.
- [api_reset_lotto_fattura_draft](manual/api_reset_lotto_fattura_draft.md) — Esporre via HTTP il reset tecnico di una singola fattura in un lotto MASSIVO in DRAFT.
- [api_run_commesse_push](manual/api_run_commesse_push.md) — Esporre via HTTP l'avvio dell'orchestratore push commesse, che sincronizza documenti sorgente (preventivi, ordini, contratti, DDT, consumi) verso commesse e commesse_attivita.
- [api_run_lotto_pipeline](manual/api_run_lotto_pipeline.md) — Esporre via HTTP l'avvio della pipeline lotto vendite.

## Funzioni
- [fn_execute_pipeline_step](funzioni/fn_execute_pipeline_step.md) — Eseguire un singolo step di pipeline, applicando i task definiti nello step corrente.
- [run_lotto_pipeline](funzioni/run_lotto_pipeline.md)

## Altri contenuti
- [fn_generate_fatture_righe](manual/fn_generate_fatture_righe.md) — Generare in Django le righe fattura a partire da attivita_fatturabili lockate sul lotto.
- [fn_group_attivita_fatturabili](manual/fn_group_attivita_fatturabili.md) — Costruire in Django la chiave di aggregazione delle attivita fatturabili.
- [fn_prepare_sdi_payload_lotto](manual/fn_prepare_sdi_payload_lotto.md) — Reperire dal database il dataset SDI di un lotto, aprendo/riusando i tentativi di invio e restituendo le righe da usare per la generazione file.
- [fn_reset_lotto_draft](manual/fn_reset_lotto_draft.md) — Eseguire il reset tecnico di un lotto MASSIVO in DRAFT invocando la funzione DB.
- [fn_reset_lotto_fattura_draft](manual/fn_reset_lotto_fattura_draft.md) — Eseguire il reset tecnico di una singola fattura in un lotto MASSIVO DRAFT.
- [pr_run_lotto_pipeline](manual/pr_run_lotto_pipeline.md) — Orchestrare l'esecuzione della pipeline di fatturazione per un lotto, gestendo:
