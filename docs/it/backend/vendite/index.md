# Area 'vendite' (Backend)

## API
- [api_commessa_attivita](manual/api_commessa_attivita.md) — Esporre via HTTP la lista paginata delle attività (commesse_attivita) di una commessa, con filtri opzionali per stato emissione, stato approvazione e mese di competenza.
- [api_commessa_stato](manual/api_commessa_stato.md) — Esporre via HTTP lo stato e i contatori aggregati di una singola commessa, per dashboard e monitoraggio avanzamento.
- [api_commesse_pricing](manual/api_commesse_pricing.md) — Esporre via HTTP le operazioni di gestione prezzo su attivita` di commessa: riallineamento da listino (N5), variazione eccezionale manuale (N7) e sblocco prezzo bloccato (N7-sblocco).
- [api_commesse_push_log](manual/api_commesse_push_log.md) — Esporre via HTTP il dettaglio di un singolo push log commesse, per consultazione operativa e diagnostica delle esecuzioni push.
- [api_contratti](manual/api_contratti.md) — CRUD operativo dei contratti commerciali cliente-listino, con sub-entita' **righe** (vendite.contratti_righe) e **utility 1:1** (vendite.contratti_utilities). E' il ponte tra il cliente (BA) e il listino, e veicola le t…
- [api_listini](manual/api_listini.md) — Esporre via HTTP la gestione completa dei listini vendite: anagrafica listino, versioni temporali, righe prezzo, associazioni di contesto e test del resolver prezzo.
- [api_lotti_list](manual/api_lotti_list.md) — Esporre via HTTP l'elenco paginato dei lotti di fatturazione con filtri opzionali e decodifica delle FK.
- [api_lotto_fatture_list](manual/api_lotto_fatture_list.md) — Esporre via HTTP l'elenco paginato delle fatture appartenenti a un lotto, con decodifiche FK, filtri opzionali e ordinamento configurabile.
- [api_lotto_segnalazioni_summary](manual/api_lotto_segnalazioni_summary.md) — Esporre via HTTP il riepilogo segnalazioni attive di un lotto, con indicazione di blocco avanzamento step.
- [api_lotto_task_runs](manual/api_lotto_task_runs.md) — Esporre via HTTP i task run runtime di un lotto per monitoraggio operativo e diagnostica pipeline.
- [api_preventivi](manual/api_preventivi.md) — Esporre via HTTP la gestione completa dei preventivi di vendita: CRUD testata, righe, indirizzi, cambio stato, revisioni, integrazione con commesse/fatturazione e pratiche.
- [api_promo_articoli](manual/api_promo_articoli.md) — CRUD admin per l'overlay promo temporale **STADIO 0** del resolver prezzi v5: una promo attiva per (articolo, uom) in un periodo batte qualunque prezzo da listino o matrice categoria. E' l'unico livello che ammette tipo…
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
- [pricing_service](manual/pricing_service.md) — Wrapper Python su due funzioni DB del pricing v5:
