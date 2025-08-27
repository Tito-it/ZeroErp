# Schema `dbops`

## 📚 Tabelle
- [audit_log](tabelle/audit_log.md) — * Monitorare e storicizzare ogni chiamata a funzioni, job e API interne. * Fornire dettagli su utente, parametri e performance di esecuzione. * Collegare gli eventi di audit agli errori e ad altri log tramite `tx_id` gestito dal trigger.
- [automation_fk_exclusions](tabelle/automation_fk_exclusions.md) — `dbops.automation_fk_exclusions` elenca le **coppie Padre/Figlio** (schema/tabella) da **escludere** dalla regola automatica **ATTIVO** (soft-delete):
- [automation_overrides_cols](tabelle/automation_overrides_cols.md) — Centralizzare le **eccezioni di naming delle colonne** usate dagli automatismi (audit, soft‑delete, storico, ecc.). Quando il tuo schema usa nomi diversi dagli standard (es. `attivo` → `is_enabled`, `data_update` → `modified_at`), qui definisci l’override **per tabella**.
- [automation_rules_tbl](tabelle/automation_rules_tbl.md) — Configurare **regole di automazione** per generare/applicare trigger e vincoli in modo dichiarativo. Ogni riga descrive **cosa** applicare (*rule_type*), **dove** (*target_schema/target_table*), **quando** (*exec_mode*), **come chiamarlo** (*name_template*), **come verificare l'esistenza** (*existence_strategy*), e **con quali parametri** (*params*).
- [automation_scope](tabelle/automation_scope.md) — Definire **l’elenco degli schemi** su cui gli orchestratori di automazione devono operare. Funziona come una **allow‑list**: se presente e popolata, limita l’esecuzione alle sole voci elencate.
- [error_log](tabelle/error_log.md) — * Raccogliere in un unico punto gli errori generati da funzioni, trigger o applicazioni, permettendo analisi e allineamento con il catalogo di messaggi di errore. * Consentire il **collegamento transazionale** tramite `tx_id`, per ricostruire l’intero flusso di operazioni (ad esempio un job batch) incrociando tabelle come `dbops.audit_log`.
- [fk_index_policy](tabelle/fk_index_policy.md) — La tabella **`dbops.fk_index_policy`** definisce una **policy centralizzata** per la gestione degli index sulle foreign key, consentendo di abilitare o disabilitare la creazione/uso di indici per specifici vincoli referenziali.
- [transaction_ids](tabelle/transaction_ids.md) — La tabella **`dbops.transaction_ids`** funge da **registro centrale** di tutti gli identificativi di transazione (UUID) utilizzati in Zero ERP: ogni volta che viene avviata un’operazione di modifica dati (inserimento, aggiornamento o cancellazione) che coinvolge più tabelle, si genera un nuovo **`tx_id`** in questa tabella e lo si propaga a tutte le righe interessate, garantendo la **tracciabilità** e il **raggruppamento** coerente delle modifiche.

## ⚙️ Funzioni
- [apply_fk_index_policy](funzioni/apply_fk_index_policy.md) — Applicare in modo automatico le regole di indicizzazione definite nella tabella `dbops.fk_index_policy`:   
- [fn_admin_merge_comune](funzioni/fn_admin_merge_comune.md)
- [fn_admin_merge_stradario](funzioni/fn_admin_merge_stradario.md)
- [fn_audit_begin](funzioni/fn_audit_begin.md) — La funzione **`fn_audit_begin`** avvia una nuova sessione di auditing registrando un evento iniziale nella tabella `dbops.audit_log`. È utilizzata come punto di partenza per tracciare processi o automazioni che richiedono visibilità sull’intero ciclo di esecuzione.
- [fn_audit_end](funzioni/fn_audit_end.md) — La funzione **`fn_audit_end`** chiude una sessione di auditing avviata da `fn_audit_begin`, registrando lo stato finale nel record corrispondente in `dbops.audit_log`.
- [fn_audit_log_once](funzioni/fn_audit_log_once.md) — La funzione **`fn_audit_log_once`** registra un singolo evento di audit senza richiedere una sessione completa (`fn_audit_begin`/`fn_audit_end`). È utile per eventi puntuali o messaggi informativi.
- [fn_col_exists](funzioni/fn_col_exists.md)
- [fn_create_gestore](funzioni/fn_create_gestore.md)
- [fn_ensure_storico_table](funzioni/fn_ensure_storico_table.md)
- [fn_find_file_usage](funzioni/fn_find_file_usage.md) — * **Analisi d’impatto**     Identificare rapidamente tutte le relazioni di FK verso una tabella, utile per valutare dipendenze e conseguenze di modifiche, cancellazioni o refactoring di schema.
- [fn_find_function_usage](funzioni/fn_find_function_usage.md) — * **Discovery delle dipendenze**: individuare tutte le occorrenze di una funzione all’interno del codice PL/pgSQL, dei trigger e degli event trigger. * **Supporto al refactoring**: identificare facilmente i punti di utilizzo prima di rinominare o modificare una funzione.
- [fn_foreign_keys_info](funzioni/fn_foreign_keys_info.md) — `dbops.fn_foreign_keys_info(tabella)` restituisce una vista unificata di **tutte le relazioni tramite chiavi esterne** ( foreign key) che coinvolgono la tabella specificata, distinguendo tra:
- [fn_generate_tx_id](funzioni/fn_generate_tx_id.md) — * **Unico punto di generazione**   Evitare duplicazioni di logica ed errori creando sempre il `tx_id` tramite una function dedicata. * **Contestualizzazione**   Conservare il nome della funzione applicativa (`generating_function`) e dati di sessione JSON (   `session_info`), per migliorare la tracciabilità. * **Sicurezza**   Impostando `SECURITY DEFINER`, la function può essere invocata da ruoli meno privilegiati mantenendo i permessi di inserimento.
- [fn_get_child_fk_col](funzioni/fn_get_child_fk_col.md)
- [fn_get_or_create_session_tx_id](funzioni/fn_get_or_create_session_tx_id.md) — * **Unicità per sessione**: restituisce un `tx_id` costante per la durata della connessione, evitando chiamate ripetute a generatori esterni. * **Fallback sicuro**: in caso di errori di connessione o in contesti di migrazione/test, restituisce un UUID “nil” per non bloccare i processi. * **Contesto centralizzato**: memorizza il `tx_id` in una GUC di sessione (`dbops.tx_id`) per accessi successivi.
- [fn_get_override_col](funzioni/fn_get_override_col.md)
- [fn_list_indices](funzioni/fn_list_indices.md)
- [fn_migrate_add_indirizzo_normalizzato](funzioni/fn_migrate_add_indirizzo_normalizzato.md)
- [fn_name_from_template](funzioni/fn_name_from_template.md)
- [fn_normalize_indirizzo](funzioni/fn_normalize_indirizzo.md)
- [fn_populate_fk_index_policy](funzioni/fn_populate_fk_index_policy.md) — * **Coerenza iniziale**   Garantire che ogni FK rilevata nella view senza indice abbia la propria entry di policy, evitando omissioni. * **Popolamento “a freddo”**   Tutti i nuovi record vengono creati con `consentito = false`, lasciando in carico all’operatore la decisione di abilitare o meno l’indice. * **Automazione**   Riduce il lavoro manuale di inserimento di policy per nuove FKs.
- [fn_resolve_scope](funzioni/fn_resolve_scope.md)
- [fn_run_automations](funzioni/fn_run_automations.md)
- [fn_run_automations_attivo](funzioni/fn_run_automations_attivo.md)
- [fn_run_automations_audit_update](funzioni/fn_run_automations_audit_update.md)
- [fn_run_automations_storico](funzioni/fn_run_automations_storico.md)
- [fn_run_automations_storico_provision](funzioni/fn_run_automations_storico_provision.md)
- [fn_run_automations_tx_id](funzioni/fn_run_automations_tx_id.md)
- [fn_schema_in_scope](funzioni/fn_schema_in_scope.md)
- [fn_schema_match](funzioni/fn_schema_match.md)
- [fn_search_column_usage](funzioni/fn_search_column_usage.md) — * Individuare rapidamente tutte le occorrenze di un campo in definizioni SQL presenti nel database. * Facilitare attività di refactoring, pulizia del codice, e verifica di dipendenze tra oggetti del database.
- [fn_seed_fk_index_policy](funzioni/fn_seed_fk_index_policy.md) — * **Sincronizzazione iniziale**   Aggiunge in `fk_index_policy` tutte le FK con indice esistente rilevate in `vw_fk_con_indice_missing_policy`. * **Automazione**   Evita inserimenti manuali per policy già coperte da indice. * **Flag di origine**   Imposta `generated_by_script = true` per distinguere le righe create automaticamente.
- [fn_table_in_scope](funzioni/fn_table_in_scope.md)
- [fn_trigger_exists_block_by_args](funzioni/fn_trigger_exists_block_by_args.md)
- [fn_trigger_exists_by_function](funzioni/fn_trigger_exists_by_function.md)
- [fn_trigger_exists_by_name](funzioni/fn_trigger_exists_by_name.md)
- [fn_trigger_exists_cascade_by_args](funzioni/fn_trigger_exists_cascade_by_args.md)
- [fn_trigger_exists_require_by_args](funzioni/fn_trigger_exists_require_by_args.md)
- [proc_apply_storicizza_defaults](funzioni/proc_apply_storicizza_defaults.md) — La procedura `dbops.apply_storicizza_defaults()` ha il compito di **impostare il valore di default `true` per la colonna `storicizza`** in tutte le tabelle elencate nella tabella di configurazione `config.storico_set_storicizza`. È utilizzata per **garantire che le nuove righe inserite siano automaticamente storicizzate**, ove previsto.
- [proc_sync_storico_set_storicizza](funzioni/proc_sync_storico_set_storicizza.md) — `dbops.proc_sync_storico_set_storicizza` è una procedura di sincronizzazione che individua, all’interno del database, tutte le tabelle che possiedono la colonna `storicizza` con **valore di default `true`** e le registra nella tabella di configurazione `config.storico_set_storicizza`.
- [trgfn_child_requires_active_parent](funzioni/trgfn_child_requires_active_parent.md)
- [trgfn_prevent_deactivate_if_children](funzioni/trgfn_prevent_deactivate_if_children.md)
- [trgfn_soft_delete_cascade](funzioni/trgfn_soft_delete_cascade.md)
- [trgfn_tx_id_managed](funzioni/trgfn_tx_id_managed.md) — La trigger function **`dbops.trgfn_tx_id_managed()`** viene eseguita **`BEFORE INSERT OR UPDATE`** su ogni tabella che contiene la colonna `tx_id` e centralizza la **logica di validazione**, **generazione** e **assegnazione** dell’**UUID di transazione** per la riga in corso di inserimento/aggiornamento.

## 🔍 Views
- [vw_catalogo_oggetti](views/vw_catalogo_oggetti.md) — * Offrire una vista unificata degli oggetti PostgreSQL definiti nei due schemi principali di amministrazione. * Agevolare operazioni di discovery e auditing, bypassando query dirette sulle catalog tables.
- [vw_duplicate_indexes](views/vw_duplicate_indexes.md) — * **Individuare indici ridondanti**   Scoprire indici che hanno lo stesso set di colonne e possono quindi essere unificati o rimossi. * **Ottimizzazione dello storage e delle performance**   Ridurre overhead di manutenzione e migliorare le prestazioni di scrittura eliminando duplicazioni. * **Governance della struttura**   Supportare analisi periodiche per mantenere lo schema pulito e coerente.
- [vw_fk_con_indice_missing_policy](views/vw_fk_con_indice_missing_policy.md) — * **Identificare gli indici esistenti**   Trova le FK già indicizzate che non dispongono di una policy dedicata. * **Suggerimento DDL**   Genera automaticamente la stringa `CREATE INDEX ...` per uniformare naming e struttura. * **Supporto auditing e governance**   Permette di scoprire eventuali indici non tracciati, inserendoli poi in `fk_index_policy`.
- [vw_fk_senza_indice](views/vw_fk_senza_indice.md) — * Individuare automaticamente vincoli di integrità referenziale (FK) privi di indice, potenziali colli di bottiglia nelle operazioni di JOIN e DELETE. * Fornire suggerimenti di creazione indice coerenti, facilitando l’ottimizzazione delle performance. * Applicare eventuali policy di esclusione gestite in `dbops.fk_index_policy`.
- [vw_function_list](views/vw_function_list.md) — * Agevolare il **discovery** delle funzioni personalizzate per manutenzione e documentazione. * Rendere immediatamente disponibili:
- [vw_trigger_functions](views/vw_trigger_functions.md) — * Fornire una panoramica centralizzata dei trigger utente presenti in ogni tabella del database. * Rendere immediatamente accessibili:
