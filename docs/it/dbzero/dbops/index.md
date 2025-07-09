# Schema `dbops`

## 📚 Tabelle
- [audit_log](tabelle/audit_log.md) — * Monitorare e storicizzare ogni chiamata a funzioni, job e API interne. * Fornire dettagli su utente, parametri e performance di esecuzione. * Collegare gli eventi di audit agli errori e ad altri log tramite `tx_id` gestito dal trigger.
- [error_log](tabelle/error_log.md) — * Raccogliere in un unico punto gli errori generati da funzioni, trigger o applicazioni, permettendo analisi e allineamento con il catalogo di messaggi di errore. * Consentire il **collegamento transazionale** tramite `tx_id`, per ricostruire l’intero flusso di operazioni (ad esempio un job batch) incrociando tabelle come `dbops.audit_log`.
- [fk_index_policy](tabelle/fk_index_policy.md)
- [transaction_ids](tabelle/transaction_ids.md) — La tabella **`dbops.transaction_ids`** funge da **registro centrale** di tutti gli identificativi di transazione (UUID) utilizzati in Zero ERP: ogni volta che viene avviata un’operazione di modifica dati (inserimento, aggiornamento o cancellazione) che coinvolge più tabelle, si genera un nuovo **`tx_id`** in questa tabella e lo si propaga a tutte le righe interessate, garantendo la **tracciabilità** e il **raggruppamento** coerente delle modifiche.

## ⚙️ Funzioni
- [apply_fk_index_policy](funzioni/apply_fk_index_policy.md)
- [fn_admin_merge_comune](funzioni/fn_admin_merge_comune.md)
- [fn_admin_merge_stradario](funzioni/fn_admin_merge_stradario.md)
- [fn_create_gestore](funzioni/fn_create_gestore.md)
- [fn_find_file_usage](funzioni/fn_find_file_usage.md) — * **Analisi d’impatto**     Identificare rapidamente tutte le relazioni di FK verso una tabella, utile per valutare dipendenze e conseguenze di modifiche, cancellazioni o refactoring di schema.
- [fn_find_function_usage](funzioni/fn_find_function_usage.md) — * **Discovery delle dipendenze**: individuare tutte le occorrenze di una funzione all’interno del codice PL/pgSQL, dei trigger e degli event trigger. * **Supporto al refactoring**: identificare facilmente i punti di utilizzo prima di rinominare o modificare una funzione.
- [fn_foreign_keys_info](funzioni/fn_foreign_keys_info.md)
- [fn_generate_tx_id](funzioni/fn_generate_tx_id.md) — * **Unico punto di generazione**   Evitare duplicazioni di logica ed errori creando sempre il `tx_id` tramite una function dedicata. * **Contestualizzazione**   Conservare il nome della funzione applicativa (`generating_function`) e dati di sessione JSON (   `session_info`), per migliorare la tracciabilità. * **Sicurezza**   Impostando `SECURITY DEFINER`, la function può essere invocata da ruoli meno privilegiati mantenendo i permessi di inserimento.
- [fn_get_or_create_session_tx_id](funzioni/fn_get_or_create_session_tx_id.md) — * **Unicità per sessione**: restituisce un `tx_id` costante per la durata della connessione, evitando chiamate ripetute a generatori esterni. * **Fallback sicuro**: in caso di errori di connessione o in contesti di migrazione/test, restituisce un UUID “nil” per non bloccare i processi. * **Contesto centralizzato**: memorizza il `tx_id` in una GUC di sessione (`dbops.tx_id`) per accessi successivi.
- [fn_list_indices](funzioni/fn_list_indices.md)
- [fn_migrate_add_indirizzo_normalizzato](funzioni/fn_migrate_add_indirizzo_normalizzato.md)
- [fn_normalize_indirizzo](funzioni/fn_normalize_indirizzo.md)
- [fn_populate_fk_index_policy](funzioni/fn_populate_fk_index_policy.md) — * **Coerenza iniziale**   Garantire che ogni FK rilevata nella view senza indice abbia la propria entry di policy, evitando omissioni. * **Popolamento “a freddo”**   Tutti i nuovi record vengono creati con `consentito = false`, lasciando in carico all’operatore la decisione di abilitare o meno l’indice. * **Automazione**   Riduce il lavoro manuale di inserimento di policy per nuove FKs.
- [fn_search_column_usage](funzioni/fn_search_column_usage.md)
- [fn_seed_fk_index_policy](funzioni/fn_seed_fk_index_policy.md) — * **Sincronizzazione iniziale**   Aggiunge in `fk_index_policy` tutte le FK con indice esistente rilevate in `vw_fk_con_indice_missing_policy`. * **Automazione**   Evita inserimenti manuali per policy già coperte da indice. * **Flag di origine**   Imposta `generated_by_script = true` per distinguere le righe create automaticamente.
- [trgfn_tx_id_managed](funzioni/trgfn_tx_id_managed.md)
