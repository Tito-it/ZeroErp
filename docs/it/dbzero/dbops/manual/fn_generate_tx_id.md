## 📘 Documentazione Concettuale – Funzione `dbops.fn_generate_tx_id`

> 👀 **Vedi anche**
>
> Approfondimento Tabelle:   
>
> * [dbops.transaction_ids](/dbzero/dbops/tabelle/transaction_ids)      
>
> Approfondimento funzioni :    
>
> * [dbops.fn_get_or_create_session_tx_id](/dbzero/dbops/funzioni/fn_get_or_create_session_tx_id)    


La funzione **`dbops.fn_generate_tx_id(p_generating_function TEXT, p_session_info JSONB DEFAULT '{}'::jsonb)`** centralizza la **generazione** e la **memorizzazione** di un nuovo identificativo di transazione (UUID) in `dbops.transaction_ids`, associando il contesto di chiamata e le informazioni di sessione.

---

### 🎯 Scopo Principale

* **Unico punto di generazione**
  Evitare duplicazioni di logica ed errori creando sempre il `tx_id` tramite una function dedicata.
* **Contestualizzazione**
  Conservare il nome della funzione applicativa (`generating_function`) e dati di sessione JSON (
  `session_info`), per migliorare la tracciabilità.
* **Sicurezza**
  Impostando `SECURITY DEFINER`, la function può essere invocata da ruoli meno privilegiati mantenendo i permessi di inserimento.

---

### 🔍 Parametri di Input

| Nome                    | Tipo    | Default       | Descrizione                                                                   |
| ----------------------- | ------- | ------------- | ----------------------------------------------------------------------------- |
| `p_generating_function` | `TEXT`  | —             | Nome (o identificativo) della funzione/procedura che richiede il `tx_id`.     |
| `p_session_info`        | `JSONB` | `'{}'::jsonb` | Oggetto JSON con dati di contesto (es. utente, IP, informazioni di sessione). |

---

### ⚙️ Flusso di Esecuzione

1. **Generazione UUID**

   ```plpgsql
   v_tx := uuidv7();
   ```
2. **Inserimento record**
   Inserisce in `dbops.transaction_ids` un nuovo rigo con:

   * `id` = `v_tx`
   * `generating_function` = `p_generating_function`
   * `session_info` = `p_session_info`
3. **Restituzione**
   Ritorna il valore `v_tx`, da utilizzare come chiave di correlazione nelle altre tabelle.

---


---

### 🚀 Esempio di Utilizzo

```sql
-- Genera un nuovo tx_id e ne visualizza il valore:
SELECT dbops.fn_generate_tx_id(
  'app.create_invoice',
  jsonb_build_object('user','mario','ip','10.0.0.5')
) AS tx_id;
```

---

### 💡 Vantaggi Operativi

* **Centralizzazione**: un’unica entry point per la creazione dei `tx_id`, evitando duplicazioni nella logica applicativa.
* **Tracciabilità avanzata**: conserva contesto funzionale e dati di sessione per ogni transazione.
* **Sicurezza**: grazie a `SECURITY DEFINER`, i ruoli applicativi possono invocare la function senza privilegi diretti su `transaction_ids`.
* **Estendibilità**: ulteriori parametri di contesto possono essere aggiunti a `session_info` senza modificare la logica di generazione.

---

> 🧠 **“La funzione `fn_generate_tx_id` semplifica e uniforma la creazione dei transaction IDs, assicurando tracciabilità, sicurezza e facilità di integrazione nell’architettura Zero ERP.”**
