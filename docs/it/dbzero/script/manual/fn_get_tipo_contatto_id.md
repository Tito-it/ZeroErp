📘 Documentazione Concettuale – Funzione `script.fn_get_tipo_contatto_id()`  

> 👀 **Vedi anche**
>
Approfondimenti tabelle:   
>
[config.tipi_contatti](/dbzero/config/tabelle/tipi_contatti)   
>
Approfondimenti funzioni:   
>
[script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)   
>  [dbops.fn_get_or_create_session_tx_id](/dbzero/dbops/funzioni/fn_get_or_create_session_tx_id)   

---
### 🎯 Scopo Principale
Recuperare l’ID del tipo di contatto corrispondente a un **codice interno** (`cod_int_tipo_contatto`), garantendo al contempo il logging e la tracciabilità tramite un `tx_id` di sessione.

---

### Parametri di Input

| Nome                      | Tipo      | Descrizione                                                |
| ------------------------- | --------- | ---------------------------------------------------------- |
| `p_cod_int_tipo_contatto` | `VARCHAR` | Codice interno univoco del tipo di contatto (es. `EMAIL`). |

---

### Flusso Logico

1. **Generazione `tx_id`**
   Invoca `dbops.fn_get_or_create_session_tx_id()` per ottenere o creare un identificativo di transazione di sessione, usato per il log centralizzato.

2. **Lookup ID**
   Esegue:

   ```sql
   SELECT id
     INTO v_id
     FROM config.tipi_contatti
    WHERE cod_int_tipo_contatto = p_cod_int_tipo_contatto;
   ```

3. **Gestione dell’errore**
   Se `v_id` è `NULL`, chiama:

   ```plpgsql
   PERFORM script.fn_log_and_raise_error(
     'database',
     'script.fn_get_tipo_contatto_id',
     'E_DEFAULT_CONTATTO_MISSING',
     jsonb_build_object('cod_int_tipo_contatto', p_cod_int_tipo_contatto),
     v_tx
   );
   ```

   Questo logga l’errore e solleva un’eccezione centralizzata, interrompendo l’esecuzione.

4. **Restituzione**
   Se l’ID viene trovato, lo restituisce.

---

### Vantaggi Operativi

* **Centralizzazione**: evita duplicazione di query e gestione degli errori in più punti.
* **Tracciabilità**: ogni chiamata è correlata a un `tx_id`, facilitando debug e audit.
* **Robustezza**: l’uso di `fn_log_and_raise_error` permette di uniformare il logging e lanciare eccezioni coerenti.

---

> **“Utilizzare una funzione dedicata con logging centralizzato garantisce coerenza nel recupero dei dati di metadato e semplifica la manutenzione del codice.”**
