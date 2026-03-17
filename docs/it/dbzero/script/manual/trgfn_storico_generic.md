## 📘 Documentazione Concettuale – Trigger Function `script.trgfn_storico_generic()`

> 👀 **Vedi anche**
>
Approfondimento funzioni:    
>
[script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)   
>
Guide:   
>
[Linee Guida SQL](/linee-guida-sql) per convenzioni di changeSet e commenti SQL  

La trigger function **`script.trgfn_storico_generic()`** centralizza la logica di storicizzazione in qualunque tabella del layer `storico`, gestendo:

* Chiusura automatica degli snapshot aperti (`valid_to IS NULL`).
* Creazione di uno snapshot iniziale con `valid_from` fisso (`1950-01-01`) se non esistevano record storici.
* Inserimento di snapshot finale con `valid_from = CURRENT_DATE` e `valid_to = NULL` per l’operazione corrente.
* Gestione di errori tramite `script.fn_log_and_raise_error`, mantenendo commenti interni e usando `TG_ARGV[0]` per il nome della colonna FK della tabella storica.
* Importante tutte le tabelle devono avere una colonna `storicizza` che è utilizzatta all'interno della funzion.

---

### 🎯 Scopo Principale

(latest review 02-02-26)
* **Unificazion- logica**: evitare duplicazioni del codice di storicizzazione in diverse funzioni trigger.
* **Flessibilità**: applicabile a qualsiasi tabella storica semplicemente specificando il parametro `TG_ARGV[0]` con il nome della colonna di riferimento.
* **Robustezza**: gestione completa degli errori con logging, senza interrompere il flusso DML principale.

---

### Parametri e Contesto

* **Parametri (`TG_ARGV`)**:

  1. `TG_ARGV[0]`: nome della colonna FK nella tabella storica che punta alla PK della tabella originale (es. `'indirizzo_dettaglio_id'`).
* **Trigger associato**: tipicamente usato con una DDL di tipo

  ```sql
  CREATE TRIGGER trg_storico
    AFTER UPDATE OR DELETE ON <schema>.<tabella_origine>
    FOR EACH ROW
    EXECUTE FUNCTION script.trgfn_storico_generic('<colonna_fk>');
  ```
* **Dipendenze**:

  * Schema `storico` deve contenere la tabella con stesso nome della sorgente.
  * Colonne `storicizza`, `valid_from`, `valid_to`, `data_insert`, `user_insert`, `snapshot`, `tipo_operazione` con struttura standard.
  * Funzione `script.fn_log_and_raise_error` per log degli errori.

---

### Flusso di Esecuzione Dettagliato

1. **Recupero ID record**

   * Se `TG_OP = 'DELETE'`, usa `OLD.id`, altrimenti `NEW.id`.
   * In caso di errore, logga con `E_SNAPSHOT_ID_NOT_FOUND`.

2. **Determinazione tipo e snapshot**

   * **UPDATE** → `op_type = 2`, `snapshot_data = to_jsonb(NEW)`.
   * **DELETE** → `op_type = 3`, `snapshot_data = to_jsonb(OLD)`.

3. **Chiusura snapshot aperti**

   * Esegue `UPDATE storico.<tabella>` su `valid_to = CURRENT_DATE` per i record con FK = ID e `valid_to IS NULL`.
   * Imposta `v_snapshot_open` a `TRUE` se modificati record; altrimenti `FALSE`.
   * Errori loggati con `E_SNAPSHOT_CLOSE_ERROR`.

4. **Inserimento storico iniziale**

   * Se `v_snapshot_open = FALSE`, inserisce snapshot initiale con `valid_from = '1950-01-01'` e `valid_to = CURRENT_DATE`, `tipo_operazione = 1`.
   * Errori gestiti con `E_SNAPSHOT_INIT_INSERT_ERROR`.

5. **Inserimento snapshot finale**

   * Inserisce sempre un record con `valid_from = CURRENT_DATE`, `valid_to = NULL`, `tipo_operazione = op_type`.
   * Errori gestiti con `E_SNAPSHOT_FINAL_INSERT_ERROR`.

6. **Restituzione record**

   * Ritorna `OLD` per `DELETE`, `NEW` per `UPDATE`.

---

### Vantaggi Operativi

* **Standardizzazione**: una sola funzione per tutte le tabelle storiche, semplifica manutenzione e aggiornamenti.
* **Configurabilità**: basta specificare la colonna di riferimento nel trigger, senza ulteriori modifiche al PL/pgSQL.
* **Resilienza**: errori intermedi non bloccano la DML, vengono loggati e notificati in modo consistente.
* **Audit Trail completo**: garantisce sempre la chiusura e la creazione di snapshot, mantenendo la storia integrale dei dati.

---

> **“Con `trgfn_storico_generic`, Zero ERP ha una soluzione unica e versatile per versionare ogni entità storica, riducendo complessità e aumentando l’affidabilità.”**
