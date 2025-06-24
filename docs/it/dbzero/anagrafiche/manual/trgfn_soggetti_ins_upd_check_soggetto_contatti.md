## 📘 Documentazione Concettuale – Trigger Function `anagrafiche.trgfn_soggetti_ins_upd_check_soggetto_contatti`

> 👀 **Vedi anche**
>
> Approfondimento tabelle:    
> - [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti)    
> - [anagrafiche.contatti](/dbzero/anagrafiche/tabelle/contatti)    
>
> Approfondimento funzioni :    
> - [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)     


La trigger function **`anagrafiche.trgfn_soggetti_ins_upd_check_soggetto_contatti()`** verifica, al termine dell’inserimento o aggiornamento di un record in `anagrafiche.soggetti`, che il soggetto associato abbia almeno un contatto valido. Se non trova contatti con `is_default = TRUE` o almeno un canale valorizzato (email, telefono, cellulare, PEC), registra l’evento e solleva un’eccezione centralizzata.

---

### 🎯 Scopo Principale

* **Validazione di integrità**
  Garantire che ogni soggetto disponga di almeno un contatto predefinito o dotato di un canale attivo.

* **Log e gestione errori centralizzata**
  Utilizzare `script.fn_log_and_raise_error` per tracciare l’anomalia e segnalare l’errore con un codice specifico (`E_SOGGETTO_NO_CONTATTI`).

* **Deferrable per transazioni**
  Essendo un **constraint trigger** `DEFERRABLE INITIALLY DEFERRED`, l’esecuzione avviene al momento del `COMMIT`, consentendo di completare tutte le operazioni di contatto correlate prima della verifica finale.

---

### 🔍 Parametri e Contesto del Trigger

* **Trigger associato**: `AFTER INSERT OR UPDATE` su `anagrafiche.soggetti`, definito come:

  ```sql
  CREATE CONSTRAINT TRIGGER trg_soggetti_ins_upd_check_soggetto_contatti
    AFTER INSERT OR UPDATE ON anagrafiche.soggetti
    DEFERRABLE INITIALLY DEFERRED
    FOR EACH ROW
    EXECUTE FUNCTION anagrafiche.trgfn_soggetti_ins_upd_check_soggetto_contatti();
  ```
* **Deferrable**: permette di posticipare la verifica fino alla fine della transazione per includere eventuali operazioni correlate su `anagrafiche.contatti`.

---

### ⚙️ Flusso Logico

1. **Conteggio contatti validi**

   ```plpgsql
   SELECT COUNT(*) INTO v_count
     FROM anagrafiche.contatti c
    WHERE c.soggetto_id = NEW.id
      AND c.default_context = 'soggetto'
      AND (
        c.is_default
        OR c.email      IS NOT NULL
        OR c.telefono   IS NOT NULL
        OR c.cellulare  IS NOT NULL
        OR c.pec        IS NOT NULL
      );
   ```
2. **Verifica risultato**

   ```plpgsql
   IF v_count = 0 THEN
     PERFORM script.fn_log_and_raise_error(
       'database',
       TG_NAME,
       'E_SOGGETTO_NO_CONTATTI',
       jsonb_build_object('soggetto_id', NEW.id)
     );
   END IF;
   ```

   * Chiama `fn_log_and_raise_error`, che registra su log la violazione e solleva l’eccezione appropriata.
3. **Restituzione**
   Restituisce `NEW` se la condizione è soddisfatta; altrimenti l’eccezione interrompe la commit.

---

### 🔒 Error Handling e Logging

* **Codice errore**: `E_SOGGETTO_NO_CONTATTI` (messaggio configurato in `config.messaggi_errore`).
* **Context payload**: JSON `{ "soggetto_id": <NEW.id> }` passato a `fn_log_and_raise_error` per dettagliare l’evento di errore.
* **Log ed eccezione**: `fn_log_and_raise_error` effettua il logging e lancia un’eccezione per bloccare la transazione.

---

### 💡 Vantaggi Operativi

* **Integrità garantita**
  Nessun soggetto privo di contatti validi può essere creato o aggiornato, prevenendo dati anomali.
* **Deferral di verifica**
  Utilizzo di trigger constraint deferrable per includere le modifiche ai contatti nella stessa transazione.
* **Centralizzazione del logging**
  Tutta la gestione di log ed eccezioni avviene tramite una funzione dedicata, facilitando l’audit.
* **Manutenzione e coerenza**
  Separazione fra logica di business (controllo contatti) e gestione degli errori (logging), in due moduli riutilizzabili.

---

> 🧠 **“Usare un constraint trigger deferrable per verificare i contatti di un soggetto assicura integrità e coerenza dei dati, sfruttando logging e gestione errori centralizzata.”**