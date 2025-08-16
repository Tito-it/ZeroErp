## 📘 Documentazione Concettuale – Trigger `trg_stradario_upd_dlt_storico_stradario`

> 👀 **Vedi anche**
>
> Approfondimenti tabelle:   
>
> * [config.stradario](/dbzero/config/tabelle/stradario)   
> * [storico.stradario](/dbzero/storico/tabelle/stradario)  
> 
> Approfondimenti funzioni: 
>  
> * [config.trgfn_stradario_upd_dlt_storico_stradario](/dbzero/config/funzioni/trgfn_stradario_upd_dlt_storico_stradario)   


Il trigger **`trg_stradario_upd_dlt_storico_stradario`** collega la logica di storicizzazione definita in `config.trgfn_stradario_upd_dlt_storico_stradario()` agli eventi di modifica e cancellazione dei record nella tabella `config.stradario`.

---

### 🎯 Scopo Principale

* **Attivare automaticamente** la funzione di versioning/storicizzazione su ogni **DELETE** o **UPDATE** di `config.stradario`.
* **Garantire che la logica di storicizzazione** sia eseguita in ogni operazione rilevante, senza interventi manuali.

---

### 🔍 Contesto e Definizione

* **Oggetto del trigger**: tabella `config.stradario`.
* **Eventi**: `BEFORE UPDATE OR DELETE`.
* **Ambito**: `FOR EACH ROW` (per ogni riga modificata/cancellata).


---

### ⚙️ Funzionamento Dettagliato

1. **Prima dell'operazione** (`BEFORE`): il trigger intercetta ogni `UPDATE` o `DELETE`.
2. **Chiamata della funzione**: invoca `config.trgfn_stradario_upd_dlt_storico_stradario()`, che:

   * Gestisce la chiusura di snapshot aperti o la creazione di nuovi record storici in `storico.stradario`.
   * Inserisce uno snapshot del nuovo stato (`valid_from`) dopo un `UPDATE` con flag `storicizza`.
   * Pulisce il flag `storicizza` (impostandolo a `false`).
   * Restituisce `NEW` o `OLD` a seconda del caso.
3. **Esecuzione dell'UPDATE/DELETE**: una volta restituito il record, l’operazione originale prosegue con il record modificato o eliminato.

---

### 🔒 Valore di Ritorno e Impatti

* **Non modifica** il flusso delle transazioni oltre l’aggiunta degli snapshot storici.
* **Mantiene** integrità e consistenza dei dati di `config.stradario`.

---

### 💡 Vantaggi Operativi

* **Attivazione trasparente**: nessuna chiamata manuale alla funzione di storicizzazione.
* **Coesione**: la logica di versioning rimane centralizzata nella funzione, il trigger ne definisce solo il contesto di esecuzione.
* **Estendibilità**: per applicare la stessa logica ad altre tabelle, basta creare trigger analoghi.

---

> 🧠 **“Il trigger rappresenta il punto di connessione tra gli eventi di database e la logica di storicizzazione, automatizzando il versioning dei dati.”**
