## 📘 Documentazione Concettuale – Function `config.trgfn_iva_ins_upd_check_conti_iva`

> 👀 **Vedi anche**
>
> Approfondimenti tabelle:    
>
> * [config.iva](/dbzero/config/tabelle/iva)    
> * [config.conti_contabili](/dbzero/config/tabelle/conti_contabili)    

La trigger function `trgfn_iva_ins_upd_check_conti_iva` assicura che i conti contabili associati ai codici IVA rispettino le regole aziendali: il conto di acquisto (`conto_iva_acquisti_id`) deve essere di tipo acquisto, mentre il conto di vendita (`conto_iva_vendita_id`) deve essere di tipo vendita.

---

### 🎯 Scopo Principale

* **Validazione contestuale**: eseguire controlli sui campi contabili prima di inserire o aggiornare un record in `config.iva`.
* **Coerenza dei dati**: evitare associazioni errate tra codici IVA e conti di tipo sbagliato.

---

### 🔍 Parametri e Contesto

* **Nessun parametro esterno**: opera sui record `NEW` del trigger.
* **Trigger associato**:

  ```
  CREATE OR REPLACE TRIGGER trg_iva_ins_upd_check_conti_iva
    BEFORE INSERT OR UPDATE ON config.iva
    FOR EACH ROW
    EXECUTE FUNCTION config.trgfn_iva_ins_upd_check_conti_iva();

  ```
* **Campi letti**:

  * `NEW.conto_iva_acquisti_id`
  * `NEW.conto_iva_vendita_id`

---

### ⚙️ Logica di Controllo

1. **Caricamento del tipo conto**

   ```
   SELECT tipo_conto INTO v_tipo_acq
     FROM config.conti_contabili
    WHERE id = NEW.conto_iva_acquisti_id;

   SELECT tipo_conto INTO v_tipo_ven
     FROM config.conti_contabili
    WHERE id = NEW.conto_iva_vendita_id;

   ```
2. **Verifica del conto di acquisto**

   ```
   IF NEW.conto_iva_acquisti_id IS NOT NULL AND v_tipo_acq <> 'A' THEN
     RAISE EXCEPTION 'Il conto acquisti (%), non è di tipo A', NEW.conto_iva_acquisti_id;
   END IF;

   ```
3. **Verifica del conto di vendita**

   ```
   IF NEW.conto_iva_vendita_id IS NOT NULL AND v_tipo_ven <> 'V' THEN
     RAISE EXCEPTION 'Il conto vendita (%), non è di tipo V', NEW.conto_iva_vendita_id;
   END IF;

   ```
4. **Terminazione**

   ```
   RETURN NEW;

   ```

Se uno dei controlli fallisce, la funzione interrompe l’operazione con un errore descrittivo.

---

### 🔒 Valore di Ritorno

* \`\`
  Restituisce `NEW` immutato se tutti i controlli superano, altrimenti solleva un’eccezione.

---

### 💡 Vantaggi Operativi

* **Prevenzione di errori**: blocca subito associazioni contabili non valide.
* **Feedback immediato**: messaggi di errore chiari aiutano lo sviluppatore o l’operatore.
* **Centralizzazione**: tutte le validazioni contabili per `config.iva` risiedono in un unico punto.

---

> 🧠 **“Con una trigger function dedicata alla validazione dei conti IVA si garantisce che ogni codice IVA sia sempre accoppiato al conto corretto, riducendo i rischi di anomalie contabili.”**
