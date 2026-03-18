## 📘 Documentazione Concettuale – Tabella `storico.indirizzi`

> 👀 **Vedi anche**  
>
Approfondimento Tabelle:   
>
[anagrafiche.indirizzi](/dbzero/anagrafiche/tabelle/indirizzi)  
>
Approfondimento funzioni e trigger:   
> [script.trgfn_upd_dlt_storico_generic](/dbzero/script/funzioni/trgfn_upd_dlt_storico_generic)  
> [dbops.trgfn_tx_id_managed](/dbzero/dbops/funzioni/trgfn_tx_id_managed)   

---

La tabella **`storico.indirizzi`** conserva lo **storico delle variazioni** della tabella `anagrafiche.indirizzi`.  
Ogni record è uno **snapshot** (copia completa in formato JSONB) dello stato dell'indirizzo al momento di una determinata operazione (inserimento, aggiornamento, eliminazione).

Il suo utilizzo è cruciale per:
- tracciare le modifiche agli indirizzi nel tempo,
- supportare analisi retrospettive,
- garantire la tracciabilità ai fini di audit e ricostruzione storica.

---
### 🎯 Scopo Principale
* **Versionamento degli indirizzi**  
  Ogni operazione su `anagrafiche.indirizzi` (INSERT, UPDATE, DELETE) genera un record nello storico che ne conserva lo stato precedente o iniziale.

* **Audit e trasparenza**  
  Mantiene informazioni su chi ha effettuato la modifica (`user_insert`) e quando (`data_insert`).

* **Snapshot in formato JSONB**  
  L’intero record viene memorizzato nel campo `snapshot` per una ricostruzione fedele dello stato originale.

---

### Collegamenti con Altre Tabelle

* **`anagrafiche.indirizzi`**  
  - Il campo `indirizzo_id` riferisce direttamente alla chiave primaria di `anagrafiche.indirizzi`.  
  - Vincolo referenziale:  
    - **ON UPDATE CASCADE** (propaga eventuali modifiche alla PK di `anagrafiche.indirizzi`)  
    - **ON DELETE NO ACTION** (non permette la cancellazione se esistono record storici collegati).  

---

### Campi Rilevanti

* **`valid_from`** – Data e ora di inizio validità (inclusiva).  
* **`valid_to`** – Data e ora di fine validità (esclusiva), può essere `NULL` se il record è attualmente valido.  
* **`snapshot`** – Contiene lo stato completo dell’indirizzo (in formato JSONB).  
* **`tipo_operazione`** – Indica la tipologia di evento:  
  - `1 = inserimento`  
  - `2 = aggiornamento`  
  - `3 = eliminazione`  
* **`change_type`** – Classifica il tipo di cambiamento:  
  - `A = Active`  
  - `S = Suppressed`  
  - `F = Fused`  
  - `D = Divided`  
* **`tx_id`** – Identificativo di transazione, generato dal trigger `dbops.trgfn_tx_id_managed`.

---

### Vantaggi Operativi

* **Ricostruzione temporale**  
  Permette di risalire allo stato di un indirizzo in una qualsiasi data passata, utile per audit, fatturazioni retroattive o analisi storiche.

* **Riduzione della ridondanza**  
  Lo snapshot JSONB contiene tutte le informazioni necessarie, senza dover duplicare intere tabelle storiche parallele.

* **Supporto a data analytics**  
  La combinazione di `valid_from` e `valid_to` permette di creare viste temporali e ricostruzioni a intervalli specifici.

* **Integrazione con processi di sincronizzazione**  
  Il campo `change_type` consente di distinguere il tipo di modifica, utile per sistemi di replica o data warehouse.

---

> **“`storico.indirizzi` è la scatola nera degli indirizzi: cattura ogni cambiamento per garantire memoria storica, auditabilità e coerenza temporale nel tempo.”**
