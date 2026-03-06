# Area 'pratiche' (Backend)

## API
- [api_flussi_list](manual/api_flussi_list.md) — Esporre via HTTP la lista e la creazione dei flussi di una pratica.
- [api_flusso_canali](manual/api_flusso_canali.md) — Esporre via HTTP i canali abilitati per il template del flusso.
- [api_flusso_detail](manual/api_flusso_detail.md) — Esporre via HTTP il dettaglio di un flusso con verifica ownership pratica.
- [api_flusso_prerequisiti](manual/api_flusso_prerequisiti.md) — Esporre via HTTP i prerequisiti di un template flusso con flag soddisfatto per preview/UI.
- [api_flusso_riattiva](manual/api_flusso_riattiva.md) — Esporre via HTTP la riattivazione di un singolo flusso sospeso.
- [api_flusso_sospendi](manual/api_flusso_sospendi.md) — Esporre via HTTP la sospensione di un singolo flusso all'interno di una pratica.
- [api_flusso_stato](manual/api_flusso_stato.md) — Esporre via HTTP le transizioni di stato di un flusso: avvio (IN_CORSO), completamento (COMPLETATO con esito) e transizioni generiche (SOSPESO, ANNULLATO, ecc.).
- [api_genera_pratica](manual/api_genera_pratica.md) — Esporre via HTTP la generazione manuale di una nuova pratica da un flusso applicando una regola di generazione.
- [api_pratica_assegnazione](manual/api_pratica_assegnazione.md) — Esporre via HTTP l'assegnazione di una pratica a risorsa umana e/o unita' organizzativa.
- [api_pratica_detail](manual/api_pratica_detail.md) — Esporre via HTTP il dettaglio e l'aggiornamento di una singola pratica.
- [api_pratica_giornale](manual/api_pratica_giornale.md) — Esporre via HTTP il giornale di bordo (audit trail) di una pratica con paginazione.
- [api_pratica_calcoli_tempo](manual/api_pratica_calcoli_tempo.md) — Esporre via HTTP i calcoli tempo (prestazione da/a) di una pratica.
- [api_pratica_riattiva](manual/api_pratica_riattiva.md) — Esporre via HTTP la riattivazione di una pratica sospesa.
- [api_pratica_sospendi](manual/api_pratica_sospendi.md) — Esporre via HTTP la sospensione di una pratica con motivo e data riattivazione opzionale.
- [api_pratica_sospensioni](manual/api_pratica_sospensioni.md) — Esporre via HTTP la lista delle sospensioni (attive e chiuse) di una pratica.
- [api_pratica_stato](manual/api_pratica_stato.md) — Esporre via HTTP il cambio stato di una pratica tramite codice_interno.
- [api_pratiche_generate](manual/api_pratiche_generate.md) — Esporre via HTTP le pratiche generate da un flusso.
- [api_pratiche_list](manual/api_pratiche_list.md) — Esporre via HTTP l'elenco paginato delle pratiche con filtri e la creazione di nuove pratiche.
- [api_regole_generazione](manual/api_regole_generazione.md) — Esporre via HTTP le regole di generazione cross-pratica applicabili a un flusso.

## Altri contenuti
- [generazione_service](manual/generazione_service.md) — Servizio per generazione cross-pratica: regole applicabili, generazione manuale e lookup pratiche generate.
- [handler_registry](manual/handler_registry.md) — Registry degli handler flusso: mapping statico da handler_key (definita in DB nella tabella pratiche.handler_flussi) a classi Python che implementano la logica di automazione.
- [pratiche_service](manual/pratiche_service.md) — Facade applicativo per operazioni su pratiche, flussi, prerequisiti, giornale e handler dispatch. API interna cross-dominio: altre app Django (vendite, anagrafiche, acquisti) importano e usano queste funzioni per creare…
