# Area 'vendite' (Backend)

## API
- [api_approvazioni_prezzo](manual/api_approvazioni_prezzo.md) — Workflow **L3 approvazione out-of-policy** per override prezzo che violano i limiti L2 configurati: l'operatore richiede approvazione, l'approver (utente con approva_prezzo_override) decide approva/rifiuta dalla coda de…
- [api_commessa_attivita](manual/api_commessa_attivita.md) — Esporre via HTTP la lista paginata delle attività (commesse_attivita) di una commessa, con filtri opzionali per stato emissione, stato approvazione e mese di competenza.
- [api_commessa_stato](manual/api_commessa_stato.md) — Esporre via HTTP lo stato e i contatori aggregati di una singola commessa, per dashboard e monitoraggio avanzamento.
- [api_commesse_pricing](manual/api_commesse_pricing.md) — Esporre via HTTP le operazioni di gestione prezzo su attivita` di commessa: riallineamento da listino (N5), variazione eccezionale manuale (N7) e sblocco prezzo bloccato (N7-sblocco).
- [api_commesse_push_log](manual/api_commesse_push_log.md) — Esporre via HTTP il dettaglio di un singolo push log commesse, per consultazione operativa e diagnostica delle esecuzioni push.
- [api_contratti](manual/api_contratti.md) — CRUD operativo dei contratti commerciali cliente-listino, con sub-entita' **righe** (vendite.contratti_righe) e **utility 1:1** (vendite.contratti_utilities). E' il ponte tra il cliente (BA) e il listino di riferimento.
- [api_listini](manual/api_listini.md) — Esporre via HTTP la gestione completa dei listini vendite: anagrafica listino, versioni temporali, righe prezzo, associazioni di contesto e test del resolver prezzo.
- [api_lotti_list](manual/api_lotti_list.md) — Esporre via HTTP l'elenco paginato dei lotti di fatturazione con filtri opzionali e decodifica delle FK.
- [api_lotto_fatture_list](manual/api_lotto_fatture_list.md) — Esporre via HTTP l'elenco paginato delle fatture appartenenti a un lotto, con decodifiche FK, filtri opzionali e ordinamento configurabile.
- [api_lotto_segnalazioni_summary](manual/api_lotto_segnalazioni_summary.md) — Esporre via HTTP il riepilogo segnalazioni attive di un lotto, con indicazione di blocco avanzamento step.
- [api_lotto_task_runs](manual/api_lotto_task_runs.md) — Esporre via HTTP i task run runtime di un lotto per monitoraggio operativo e diagnostica pipeline.
- [api_offerte](manual/api_offerte.md) — CRUD operativo delle **offerte commerciali**, documento pre-contrattuale che propone al cliente le condizioni quadro per una specifica utility prima della formalizzazione in contratto. Espone sub-entita' **eccezioni** (…
- [api_ordini](manual/api_ordini.md) — CRUD operativo (scheletro) degli **ordini di vendita**, documento del ciclo attivo che raccoglie le righe articolo da evadere/fatturare. Espone testata, **righe** con **componenti BoM** (modello unificato), **conferma**…
- [api_preventivi](manual/api_preventivi.md) — Esporre via HTTP la gestione completa dei preventivi di vendita: CRUD testata, righe, indirizzi, cambio stato, revisioni, integrazione con commesse/fatturazione e pratiche.
- [api_preventivi_approvazione_flusso](manual/api_preventivi_approvazione_flusso.md) — Esporre via HTTP l'accoppiamento **M2** (brief BE §8.3): sul percorso pratica, il completamento del flusso APPROVAZIONE_CLIENTE **guida** l'accettazione del preventivo collegato, in un'unica transazione.
- [api_preventivi_collega_pratica](manual/api_preventivi_collega_pratica.md) — Aggancia un preventivo come **ROOT** a una pratica (pratiche_sorgenti). Usato a PREVENTIVAZIONE sul percorso pratica-first PREVENTIVI: è la **fonte di verità** del legame preventivo↔pratica da cui l'handler vendita.push…
- [api_pricing](manual/api_pricing.md) — Endpoint diagnostici e di lookup per il sistema pricing v5. Espongono il resolver a 3 stadi (PROMO → CONTRATTO → CATEGORIA) e i limiti L2 di variazione prezzo configurati per l'utente corrente.
- [api_promo_articoli](manual/api_promo_articoli.md) — CRUD admin per l'overlay promo temporale **STADIO 0** del resolver prezzi v5: una promo attiva per (articolo, uom) in un periodo batte qualunque prezzo da listino o matrice categoria. E' l'unico livello che ammette tipo…
- [api_reset_lotto_draft](manual/api_reset_lotto_draft.md) — Esporre via HTTP il reset tecnico di un lotto MASSIVO in DRAFT.
- [api_reset_lotto_fattura_draft](manual/api_reset_lotto_fattura_draft.md) — Esporre via HTTP il reset tecnico di una singola fattura in un lotto MASSIVO in DRAFT.
- [api_run_commesse_push](manual/api_run_commesse_push.md) — Esporre via HTTP l'avvio dell'orchestratore push commesse, che sincronizza documenti sorgente (preventivi, ordini, contratti, DDT, consumi) verso commesse e commesse_attivita.
- [api_run_lotto_pipeline](manual/api_run_lotto_pipeline.md) — Esporre via HTTP l'avvio della pipeline lotto vendite.
- [api_vendite_form_defaults](manual/api_vendite_form_defaults.md) — Endpoint **form-defaults** read-only consumati dai drawer FE all'apertura o al cambio di un campo chiave (BA per contratti/preventivi, sorgente per clone versione). Centralizzano lato BE la risoluzione di valori di defa…
- [api_vendite_lookups](manual/api_vendite_lookups.md) — Endpoint **lookup statici** per gli enum di dominio vendite (Fase 2 refactor frontend vendite): tipi variazione (contratto/promo), ambiti contratto, modalità pricing contratto. Eliminano i magic string cablati nei drawe…

## Funzioni
- [fn_execute_pipeline_step](funzioni/fn_execute_pipeline_step.md) — Eseguire un singolo step di pipeline, applicando i task definiti nello step corrente.
- [run_lotto_pipeline](funzioni/run_lotto_pipeline.md)

## Altri contenuti
- [fn_generate_fatture_righe](manual/fn_generate_fatture_righe.md) — Generare in Django le righe fattura a partire da attivita_fatturabili lockate sul lotto.
- [fn_group_attivita_fatturabili](manual/fn_group_attivita_fatturabili.md) — Costruire in Django la chiave di aggregazione delle attivita fatturabili.
- [fn_prepare_sdi_payload_lotto](manual/fn_prepare_sdi_payload_lotto.md) — Reperire dal database il dataset SDI di un lotto, aprendo/riusando i tentativi di invio e restituendo le righe da usare per la generazione file.
- [fn_reset_lotto_draft](manual/fn_reset_lotto_draft.md) — Eseguire il reset tecnico di un lotto MASSIVO in DRAFT invocando la funzione DB.
- [fn_reset_lotto_fattura_draft](manual/fn_reset_lotto_fattura_draft.md) — Eseguire il reset tecnico di una singola fattura in un lotto MASSIVO DRAFT.
- [modello-contratti](manual/modello-contratti.md) — Un contratto e' un accordo cliente-fornitore che fissa **come si prezza** un articolo per un cliente specifico, su una specifica utility, per un periodo di validita'. E' il ponte tra:
- [offerte_service](manual/offerte_service.md) — Facade applicativa CRUD per vendite.offerte_commerciali + eccezioni (mirror di contratti_righe) + utility 1:1 (estensione contratti_utilities), con gestione della state machine di processo (BOZZA / EMESSA / ACCETTATA /…
- [pr_run_lotto_pipeline](manual/pr_run_lotto_pipeline.md) — Orchestrare l'esecuzione della pipeline di fatturazione per un lotto, gestendo:
- [pricing_service](manual/pricing_service.md) — Wrapper Python su due funzioni DB del pricing v5:
- [push_preventivo_handler](manual/push_preventivo_handler.md) — Handler flusso vendita.push_preventivo — orchestratore **CONFERMA_VENDITA**, primo handler reale del motore pratiche. Al passaggio del flusso CONFERMA in IN_CORSO **smista per natura** le righe del preventivo ACCETTATO…
- [template_contratto_iniziale](manual/template_contratto_iniziale.md) — Template HTML iniziale per la generazione PDF di un contratto commerciale tramite context builder CONTRATTO.
- [template_offerta_iniziale](manual/template_offerta_iniziale.md) — Template HTML iniziale per la generazione PDF di un'**offerta commerciale** tramite il context builder OFFERTA_COMMERCIALE. Da copiare in documenti.template_documenti_versioni.html_template come prima versione PUBBLICAT…
