## 📘 Documentazione Concettuale – Trigger Function `anagrafiche.trgfn_contatti_ins_upd_set_default_contatto()`

> 👀 **Vedi anche**
>
> Approfondimento tabelle:    
> - [anagrafiche.contatti](/dbzero/anagrafiche/tabelle/contatti)    
>
> Approfondimento funzioni :    
> - [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)     

La trigger function **`anagrafiche.trgfn_contatti_ins_upd_set_default_contatto()`** garantisce che, per ogni soggetto/ruolo/utility, esista al massimo un contatto contrassegnato come predefinito (`is_default = true`).

---

### 🎯 Scopo Principale

* **Unicità del contatto predefinito**: assicura che quando un nuovo contatto viene marcato come default, tutti gli altri contatti dello stesso soggetto/ruolo/utility siano automaticamente resettati a `is_default = false`.

---

### 🔍 Contesto e Associazione

* **Tabella:** `anagrafiche.contatti`
* **Evento:** `BEFORE INSERT OR UPDATE`
* **Ambito:** `FOR EACH ROW`
* **Trigger DDL:**

  ```sql
  CREATE TRIGGER trg_contatti_ins_upd_set_default_contatto
    BEFORE INSERT OR UPDATE ON anagrafiche.contatti
    FOR EACH ROW
    EXECUTE FUNCTION anagrafiche.trgfn_contatti_ins_upd_set_default_contatto();
  ```

---

### ⚙️ Comportamento

1. **Se `NEW.is_default = TRUE`**

   * Non modifica il flag del record in lavorazione.
   * Esegue un `UPDATE` su `anagrafiche.contatti` per impostare `is_default = FALSE` su tutti gli altri contatti dello stesso `soggetto_id` che risultino ancora default.

2. **Se `NEW.is_default = FALSE`**

   * Verifica se esiste già un contatto default per lo stesso `soggetto_id`:

     ```sql
     SELECT COUNT(*) INTO cnt
       FROM anagrafiche.contatti
      WHERE soggetto_id = NEW.soggetto_id
        AND is_default;
     ```
   * Se **nessun** default è presente (`cnt = 0`), assegna automaticamente `NEW.is_default := TRUE`, garantendo almeno un contatto predefinito.

3. **Restituzione**

   * `RETURN NEW` per proseguire con l’inserimento o l’aggiornamento.

---

### 📋 Esempio di Flusso Interno

```plpgsql
-- Pseudocodice semplificato
IF NEW.is_default THEN
  UPDATE anagrafiche.contatti
     SET is_default = FALSE
   WHERE soggetto_id = NEW.soggetto_id
     AND soggetto_ruolo_id = NEW.soggetto_ruolo_id
     AND utility_id = NEW.utility_id
     AND id <> NEW.id;
END IF;

RETURN NEW;
```

---

### 💡 Vantaggi Operativi

* **User experience**: garantisce che in UI o API il contatto predefinito sia sempre univoco.
* **Consistenza dei dati**: elimina la necessità di logiche complesse in applicazione per la gestione del default.
* **Manutenibilità**: centralizza la logica di default direttamente nel database.

---

> 🧠 **“Con una trigger function dedicata, il vincolo di un solo contatto default per combinazione soggetto/ruolo/utility è garantito automaticamente a livello database.”**