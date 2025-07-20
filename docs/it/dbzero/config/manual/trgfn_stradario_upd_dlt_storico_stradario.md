## 📘 Documentazione Concettuale – Trigger Function `config.trgfn_stradario_upd_dlt_storico_stradario()`

> 👀 **Vedi anche**
>
> Approfondimento Tabelle:  
>  - [storico.stradario](/dbzero/storico/tabelle\stradario)   
>  - [config.stradario](/dbzero/config/tabelle/stradario)     
>  - [config.stradario_generale](/dbzero/config/tabelle/stradario_generale)   
>
> Approfondimenti funzioni:   
> - [config.trg_stradario_upd_dlt_storico_stradario](/dbzero/config/manual/trg_stradario_upd_dlt_storico_stradario)


La trigger function **`config.trgfn_stradario_upd_dlt_storico_stradario()`** gestisce la storicizzazione delle modifiche e cancellazioni nella tabella **`config.stradario`**, creando snapshot JSONB completi dello stato della via.

---

### 🎯 Scopo Principale

* **Audit Trail**: Conservare la cronologia completa di ogni update o delete applicato a `config.stradario`.
* **Versioning coerente**: Ricostruire lo stato di una via in qualsiasi momento grazie ai campi `valid_from` e `valid_to`.
* **Centralizzazione logica**: Evitare duplicazioni di codice di storicizzazione e garantire un comportamento uniforme.

---

### ⚙️ Obiettivi e Ruolo

1. **Determinazione contesto**: utilizzare `NEW.storicizza` o `OLD.storicizza` per decidere se attivare la storicizzazione.
2. **Chiusura snapshot aperto**: aggiornare `valid_to` per il record storico attualmente aperto.
3. **Creazione snapshot iniziale**: se non era presente nessuno snapshot per la riga, inserire un record con i valori `OLD` e `tipo_operazione = 1`.
4. **Inserimento snapshot aggiornato o finale**: aggiungere un nuovo record storico con `tipo_operazione = 2` (UPDATE) o `3` (DELETE), includendo il JSONB di `NEW` o `OLD`.
5. **Gestione errori**: in caso di eccezioni, loggare via `script.fn_log_and_raise_error` senza bloccare l’operazione DML.

---


### 🔖 Esempio di Trigger DDL

```sql
DROP TRIGGER IF EXISTS trg_stradario_upd_dlt_storico_stradario
  ON config.stradario;

CREATE TRIGGER trg_stradario_upd_dlt_storico_stradario
  BEFORE UPDATE OR DELETE ON config.stradario
  FOR EACH ROW
  WHEN (NEW.storicizza = TRUE OR OLD.storicizza = TRUE)
  EXECUTE FUNCTION config.trgfn_stradario_upd_dlt_storico_stradario();
```

---

### 💡 Vantaggi Operativi

* **Storico dettagliato**: snapshot JSONB completi dello stato della via al momento dell’operazione.
* **Consistenza temporale**: campi `valid_from`/`valid_to` per query storiche affidabili.
* **Classificazione chiara**: `tipo_operazione` distingue INSERT iniziale, UPDATE e DELETE.
* **Resilienza**: gestione delle eccezioni con logging, senza interrompere la DML.

---

> 🧠 **“`trgfn_stradario_upd_dlt_storico_stradario` offre un audit trail robusto e centralizzato per il tracciamento delle vie, unendo flessibilità JSONB e semplicità d’uso.”**
