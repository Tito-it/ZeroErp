## 📚 Documentazione Concettuale – Tabella `dbops.transaction_ids`  

> 👀 **Vedi anche**  
>
Approfondimento Tabelle:   
>
[config.parameter_overrides](/dbzero/config/tabelle/parameter_overrides)      
>
Approfondimento funzioni :    
>
[script.fn_get_parameter_full](/dbzero/script/funzioni/fn_get_parameter_full)    
> [script.trgfn_prevent_modification_generic](/dbzero/script/funzioni/trgfn_prevent_modification_generic)    

### 🎯 Scopo Principale

(latest review 10-01-26)
La tabella **`dbops.transaction_ids`** funge da **registro centrale** di tutti gli identificativi di transazione (UUID) utilizzati in Zero ERP: ogni volta che viene avviata un’operazione di modifica dati (inserimento, aggiornamento o cancellazione) che coinvolge più tabelle, si genera un nuovo **`tx_id`** in questa tabella e lo si propaga a tutte le righe interessate, garantendo la **tracciabilità** e il **raggruppamento** coerente delle modifiche.

---

### Vincoli

* **PRIMARY KEY**: `transaction_ids_pkey` sulla colonna `id` (UUID).

---
### 🚨 Protezione Dati di Audit

* **Trigger**: `trg_prevent_mod_parameters_audit` (BEFORE UPDATE OR DELETE) su `config.parameters_audit`.
  Esegue la funzione `script.trgfn_prevent_modification_generic()`, che impedisce qualsiasi modifica o cancellazione dei record di audit, assicurando l’inalterabilità della cronologia.


---

### Meccanismo di Utilizzo

1. **Generazione del `tx_id`**

   ```sql
   INSERT INTO dbops.transaction_ids DEFAULT VALUES
   RETURNING id;
   ```
2. **Propagazione**
   Il valore restituito (`tx_id`) viene passato alle colonne omonime (`tx_id`) nelle altre tabelle coinvolte, assicurando che tutte le operazioni riferiscano la stessa transazione.
3. **Auditing**

   * `user_insert` e `data_insert` registrano chi e quando ha creato il `tx_id`.
   * `user_update` e `data_update` vengono aggiornati ad ogni modifica grazie al trigger di audit.
   * `generating_function` può contenere il nome della funzione o procedura DB che ha generato il `tx_id`.
   * `session_info` può immagazzinare JSONB con ulteriori informazioni di contesto (es. utente applicativo, IP, dettagli di sessione).

---

### Vantaggi Operativi

* **Coerenza transazionale**: un singolo `tx_id` per raggruppare operazioni correlate su più tabelle.
* **Inalterabilità**: la cronologia rimane immutata grazie al trigger di prevenzione.
* **Tracciabilità**: facilità di debug e audit, risalendo a tutte le modifiche di una stessa transazione.
* **Flessibilità**: il campo `session_info` consente di allegare dati custom alla transazione.

---

> **“Centralizzare gli UUID di transazione in `dbops.transaction_ids` semplifica la gestione e l’analisi delle operazioni distribuite, garantendo un’unica chiave di correlazione per l’intera applicazione.”**