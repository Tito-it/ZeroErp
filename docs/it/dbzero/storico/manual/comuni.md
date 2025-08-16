## 📘 Documentazione Concettuale – Tabella `storico.comuni`

> 👀 **Vedi anche**
>
> Approfondimento tabelle:      
>
> * [config.comuni](/dbzero/config/tabelle/comuni)     
>
> Approfondimento funzioni:    
>
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)    
> * [config.trgfn_comuni_upd_dlt_storico_comuni](/dbzero/config/funzioni/trgfn_comuni_upd_dlt_storico_comuni)    

La tabella **`storico.comuni`** mantiene la cronologia completa dei record di **`config.comuni`**, archiviando snapshot JSON dei dati ad ogni operazione di modifica o cancellazione (quando il flag `storicizza` è impostato a `TRUE`).

---
### 🎯 Scopo Principale

* **Audit Trail**: Conservare una traccia immutabile di ogni modifica e cancellazione applicata a `config.comuni`.
* **Versioning dei record**: Permettere la ricostruzione dello stato storico di ogni comune in un dato momento.
* **Query storiche**: Supportare interrogazioni basate su intervalli temporali grazie ai campi `valid_from` e `valid_to`.
* **Classificazione operazioni**: Utilizzare `tipo_operazione_id` e `change_type` per distinguere INSERT iniziale, UPDATE e DELETE.
---

### 📝 Descrizione del Meccanismo di Storico

1. **Trigger di storicizzazione**
   La trigger function `config.trgfn_comuni_upd_dlt_storico_comuni()` si attiva **BEFORE UPDATE OR DELETE** su `config.comuni` quando `storicizza = TRUE`.

2. **Ricostruzione INSERT iniziale**
   Anche se non esiste un record di `storico.comuni` per un dato `comune_id`, al primo **UPDATE** o **DELETE** viene creato automaticamente uno **snapshot iniziale** (tipo_operazione_id = 1) con i dati originali.

3. **Gestione valid_from/valid_to**

   * Ogni UPDATE chiude il record precedente impostando `valid_to = CURRENT_DATE`.
   * Successivamente crea un nuovo snapshot (tipo_operazione_id = 2) con `valid_from = CURRENT_DATE` e `valid_to = NULL`, fino al prossimo cambiamento.
   * DELETE chiude e aggiunge uno snapshot di cancellazione (tipo_operazione_id = 3) con `valid_to = CURRENT_DATE`.

4. **Uso del JSONB**

   * Il campo `snapshot` replica **tutti** i campi di `config.comuni` in formato JSONB, garantendo flessibilità di evoluzione dello schema.
   * **Vantaggio**: facile query e estrazione dell’intero stato storico del record.
   * **Costo**: overhead di spazio e possibili impatti sulle performance in lettura/scrittura.

5. **Change_type**
   Il campo `change_type` aiuta a classificare rapidamente la natura del record storico:

   * `A` = Active (predefinito per nuovi snapshot)
   * `S` = Suppressed
   * `F` = Fused
   * `D` = Divided

---

### 🔧 Vantaggi Operativi

* **Storico dettagliato**: grazie a `snapshot` JSONB, ogni modifica può essere ricostruita integralmente, indipendentemente dall’aggiunta di nuovi campi in `config.comuni`.

* **Tracciabilità degli eventi**: i campi `tipo_operazione_id` e `change_type` forniscono metadati chiari su **quando** e **come** è avvenuto il cambiamento.

* **Allineamento dello schema**: il meccanismo non richiede aggiornamenti manuali del modello storico a ogni modifica di `config.comuni`, perché il JSONB è autonomo.

* **Resilienza a errori**: il trigger di storicizzazione utilizza blocchi `EXCEPTION` per loggare errori senza bloccare l’operazione DML principale.

---

> 🧠 **“Con `storico.comuni`, Zero ERP unisce flessibilità e completezza: un audit trail granulare dei comuni, a costo di uno storage aggiuntivo, ma con performance e semplicità di gestione future-proof.”**

