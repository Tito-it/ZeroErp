## 📘 Documentazione Concettuale – Trigger Function `anagrafiche.trgfn_soggetti_ins_upd_genera_cdsoggetto()`

> 👀 **Vedi anche**
>
> Approfondimenti tabelle:    
> - [config.sistema_codici](/dbzero/config/tabelle/sistema_codici)    
>
> Approfondimenti funzioni:   
> - [script.fn_generate_codice](/dbzero/script/funzioni/fn_generate_codice)    

### 🎯 Scopo Principale

La trigger function **`anagrafiche.trgfn_soggetti_ins_upd_genera_cdsoggetto()`** viene eseguita **`BEFORE INSERT OR UPDATE`** su **`anagrafiche.soggetti`** e si occupa di:

* Verificare se il campo `codice_soggetto` è nullo.
* Generare automaticamente un nuovo `codice_soggetto` utilizzando la logica centralizzata in `script.fn_generate_codice('soggetto')`.

---

### ⚙️ Obiettivi e Ruolo

1. **Unicità e coerenza**: garantire che ogni soggetto inserito o aggiornato abbia un codice univoco, evitando conflitti manuali.
2. **Centralizzazione della generazione**: delegare la logica di creazione alla funzione di utility `fn_generate_codice`, che usa la tabella di sistema `config.sistema_codici` per decide prefissi, sequenze e formati.
3. **Semplicità di manutenzione**: modifiche al formato dei codici o alle regole di sequenza avvengono in un unico punto (`fn_generate_codice`), senza toccare il trigger.

---

### 🔍 Flusso di Esecuzione Dettagliato

1. **Verifica dell’operazione**
   Il trigger opera sia su **`INSERT`** sia su **`UPDATE`**.

2. **Controllo** **`codice_soggetto`**

   ```plpgsql
   IF (TG_OP = 'INSERT' OR TG_OP = 'UPDATE')
      AND NEW.codice_soggetto IS NULL THEN
     -- Campo non valorizzato: generazione automatica
   ```

3. **Invocazione della funzione di generazione**

   ```plpgsql
   NEW.codice_soggetto := script.fn_generate_codice('soggetto');
   ```

   * `fn_generate_codice` legge da `config.sistema_codici` i parametri (prefisso, sequenza, formato) per il dominio `'soggetto'`.

4. **Restituzione del record**
   Il record aggiornato con `NEW.codice_soggetto` valorizzato viene restituito all’operazione DML.

---

### 🔖 Esempio di Trigger DDL

```sql
DROP TRIGGER IF EXISTS trg_soggetti_ins_upd_genera_cdsoggetto
  ON anagrafiche.soggetti;

CREATE TRIGGER trg_soggetti_ins_upd_genera_cdsoggetto
  BEFORE INSERT OR UPDATE
  ON anagrafiche.soggetti
  FOR EACH ROW
  EXECUTE FUNCTION anagrafiche.trgfn_soggetti_ins_upd_genera_cdsoggetto();
```

---

### 💡 Vantaggi Operativi

* **Automazione**: elimina la necessità di calcolare o fornire manualmente il codice del soggetto.
* **Consistenza**: assicura che tutti i codici seguano lo stesso pattern, facilitando ricerche e integrazioni.
* **Flessibilità**: cambiamenti al pattern di codice (prefissi, lunghezza, charset) si applicano modificando solo `config.sistema_codici` o la funzione `fn_generate_codice`.

---

> 🧠 **“Con ****`trgfn_soggetti_ins_upd_genera_cdsoggetto`****, Zero ERP assicura codici di soggetto uniformi e coerenti, lasciando al database il compito di generare e mantenere la logica di sequenza.”**
